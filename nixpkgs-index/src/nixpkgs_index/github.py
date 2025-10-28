"""GitHub API client for discovering nixpkgs commits."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from dataclasses import dataclass
import requests

logger = logging.getLogger(__name__)


@dataclass
class TimeWindow:
    """Represents a time window for querying commits."""

    start: datetime
    end: datetime


def calculate_target_times(
    start_time: datetime,
    step_interval: timedelta,
    max_steps: int,
    since: Optional[datetime] = None,
) -> List[datetime]:
    """
    Calculate target times at regular intervals going backwards from start_time.

    Args:
        start_time: The starting point (usually HEAD timestamp)
        step_interval: Time interval between steps (e.g., 14 days)
        max_steps: Maximum number of steps to calculate
        since: Optional earliest time limit

    Returns:
        List of target times in chronological order (oldest first)
    """
    target_times = []

    for step in range(1, max_steps + 1):
        target_time = start_time - (step_interval * step)

        if since and target_time < since:
            break

        target_times.append(target_time)

    target_times.reverse()
    return target_times


def create_query_window(
    target_time: datetime, window_size: timedelta = timedelta(hours=1)
) -> TimeWindow:
    """
    Create a time window around a target time for querying commits.

    Args:
        target_time: The target time to center the window around
        window_size: Half the total window size (default: 1 hour, so total window is 2 hours)

    Returns:
        TimeWindow with start and end times
    """
    return TimeWindow(start=target_time - window_size, end=target_time + window_size)


class GitHubAPIError(Exception):
    """Raised when GitHub API requests fail."""

    pass


class GitHubCommit:
    """Represents a commit from GitHub API."""

    def __init__(self, sha: str, timestamp: datetime):
        self.sha = sha
        self.timestamp = timestamp

    def __repr__(self):
        return (
            f"GitHubCommit(sha={self.sha[:12]}, timestamp={self.timestamp.isoformat()})"
        )


class GitHubClient:
    """Client for GitHub API to discover nixpkgs commits."""

    BASE_URL = "https://api.github.com"
    REPO_OWNER = "NixOS"
    REPO_NAME = "nixpkgs"

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"token {token}"})

    def get_branch_head(self, branch: str) -> GitHubCommit:
        """Get the HEAD commit of a branch."""
        url = (
            f"{self.BASE_URL}/repos/{self.REPO_OWNER}/{self.REPO_NAME}/commits/{branch}"
        )

        logger.debug(f"Fetching HEAD of branch: {branch}")
        response = self.session.get(url)

        if response.status_code != 200:
            raise GitHubAPIError(
                f"Failed to get branch HEAD: {response.status_code} {response.text}"
            )

        data = response.json()
        sha = data["sha"]
        timestamp_str = data["commit"]["committer"]["date"]
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        logger.info(f"Branch HEAD: {sha[:12]} at {timestamp.isoformat()}")
        return GitHubCommit(sha, timestamp)

    def discover_commits_at_intervals(
        self,
        branch: str,
        step_interval: timedelta,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        max_steps: Optional[int] = None,
    ) -> List[GitHubCommit]:
        """
        Discover commits at regular time intervals.

        Algorithm:
        1. Start with the most recent commit (or `until` if specified)
        2. Calculate target times at regular intervals using calculate_target_times()
        3. For each target time, query API for the closest commit
        4. Returns commits in chronological order (oldest first)
        """
        commits = []

        if until:
            start_time = until
            logger.info(f"Starting from specified until time: {until.isoformat()}")
        else:
            head = self.get_branch_head(branch)
            commits.append(head)
            start_time = head.timestamp
            logger.info(
                f"Starting from branch HEAD: {head.sha[:12]} at {start_time.isoformat()}"
            )

        if max_steps is None:
            max_steps = 1000

        target_times = calculate_target_times(
            start_time, step_interval, max_steps, since
        )

        logger.info(f"Calculated {len(target_times)} target times to query")

        for i, target_time in enumerate(target_times, 1):
            window = create_query_window(target_time)

            logger.debug(
                f"Step {i}/{len(target_times)}: target time {target_time.isoformat()} (window: {window.start.isoformat()} to {window.end.isoformat()})"
            )

            commit = self._get_oldest_commit_in_window(branch, window.start, window.end)

            if commit:
                commits.append(commit)
                logger.debug(
                    f"  Found: {commit.sha[:12]} at {commit.timestamp.isoformat()}"
                )
            else:
                logger.debug(f"  No commits found in window")

        commits.reverse()
        logger.info(f"Discovered {len(commits)} commits total")
        return commits

    def _get_oldest_commit_in_window(
        self, branch: str, since: datetime, until: datetime
    ) -> Optional[GitHubCommit]:
        """
        Get the oldest commit in a time window.

        Uses GitHub Commits API with since/until parameters.
        """
        url = f"{self.BASE_URL}/repos/{self.REPO_OWNER}/{self.REPO_NAME}/commits"

        params = {
            "sha": branch,
            "since": since.isoformat(),
            "until": until.isoformat(),
            "per_page": 100,
        }

        response = self.session.get(url, params=params)

        if response.status_code != 200:
            logger.warning(
                f"API request failed: {response.status_code} {response.text}"
            )
            return None

        commits_data = response.json()

        if not commits_data:
            return None

        oldest_commit = commits_data[-1]
        sha = oldest_commit["sha"]
        timestamp_str = oldest_commit["commit"]["committer"]["date"]
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

        return GitHubCommit(sha, timestamp)

    def check_rate_limit(self) -> Tuple[int, int]:
        """
        Check GitHub API rate limit.

        Returns (remaining, limit) tuple.
        """
        url = f"{self.BASE_URL}/rate_limit"
        response = self.session.get(url)

        if response.status_code != 200:
            logger.warning(f"Failed to check rate limit: {response.status_code}")
            return (0, 0)

        data = response.json()
        core = data["resources"]["core"]
        remaining = core["remaining"]
        limit = core["limit"]

        logger.debug(f"GitHub API rate limit: {remaining}/{limit} remaining")
        return (remaining, limit)
