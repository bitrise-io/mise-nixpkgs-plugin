"""Unit tests for GitHub client module."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from nixpkgs_index.github import GitHubClient, GitHubCommit, GitHubAPIError


class TestGitHubCommit:
    def test_create_github_commit(self):
        sha = "abc123def456"
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        commit = GitHubCommit(sha, timestamp)

        assert commit.sha == sha
        assert commit.timestamp == timestamp

    def test_github_commit_repr(self):
        sha = "abc123def456789abcdef"
        timestamp = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        commit = GitHubCommit(sha, timestamp)
        repr_str = repr(commit)

        assert "abc123def456" in repr_str
        assert "2025-01-15" in repr_str


class TestGitHubClient:
    def test_create_client_with_token(self):
        token = "ghp_test_token"
        client = GitHubClient(token=token)

        assert client.token == token
        assert client.session is not None
        assert "Authorization" in client.session.headers

    def test_client_sets_auth_header(self):
        token = "ghp_test_token"
        client = GitHubClient(token=token)

        assert client.session.headers.get("Authorization") == f"token {token}"

    def test_client_no_auth_header_without_token(self):
        client = GitHubClient(token=None)

        assert "Authorization" not in client.session.headers

    @patch("requests.Session.get")
    def test_get_branch_head_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sha": "abc123",
            "commit": {"committer": {"date": "2025-01-15T12:00:00Z"}},
        }
        mock_get.return_value = mock_response

        client = GitHubClient()
        commit = client.get_branch_head("nixpkgs-unstable")

        assert commit.sha == "abc123"
        assert commit.timestamp == datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    @patch("requests.Session.get")
    def test_get_branch_head_failure(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_get.return_value = mock_response

        client = GitHubClient()

        with pytest.raises(GitHubAPIError) as exc_info:
            client.get_branch_head("nonexistent-branch")

        assert "Failed to get branch HEAD" in str(exc_info.value)

    @patch("requests.Session.get")
    def test_check_rate_limit_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resources": {"core": {"remaining": 4999, "limit": 5000}}
        }
        mock_get.return_value = mock_response

        client = GitHubClient()
        remaining, limit = client.check_rate_limit()

        assert remaining == 4999
        assert limit == 5000

    @patch("requests.Session.get")
    def test_check_rate_limit_failure(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        client = GitHubClient()
        remaining, limit = client.check_rate_limit()

        assert remaining == 0
        assert limit == 0

    @patch("requests.Session.get")
    def test_get_oldest_commit_in_window_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "sha": "newest_commit",
                "commit": {"committer": {"date": "2025-01-15T13:00:00Z"}},
            },
            {
                "sha": "oldest_commit",
                "commit": {"committer": {"date": "2025-01-15T11:00:00Z"}},
            },
        ]
        mock_get.return_value = mock_response

        client = GitHubClient()
        since = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        until = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

        commit = client._get_oldest_commit_in_window("nixpkgs-unstable", since, until)

        assert commit is not None
        assert commit.sha == "oldest_commit"

    @patch("requests.Session.get")
    def test_get_oldest_commit_in_window_empty(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        client = GitHubClient()
        since = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        until = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

        commit = client._get_oldest_commit_in_window("nixpkgs-unstable", since, until)

        assert commit is None

    @patch("requests.Session.get")
    def test_get_oldest_commit_in_window_api_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_get.return_value = mock_response

        client = GitHubClient()
        since = datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        until = datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc)

        commit = client._get_oldest_commit_in_window("nixpkgs-unstable", since, until)

        assert commit is None

    @patch.object(GitHubClient, "get_branch_head")
    @patch.object(GitHubClient, "_get_oldest_commit_in_window")
    def test_discover_commits_at_intervals_basic(self, mock_get_oldest, mock_get_head):
        head_commit = GitHubCommit(
            "head_sha", datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        )
        mock_get_head.return_value = head_commit

        # Simulate finding commits at different times
        window_commits = [
            GitHubCommit(
                "commit1", datetime(2025, 1, 8, 12, 0, 0, tzinfo=timezone.utc)
            ),
            GitHubCommit(
                "commit2", datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            ),
        ]
        mock_get_oldest.side_effect = window_commits

        client = GitHubClient()
        commits = client.discover_commits_at_intervals(
            branch="nixpkgs-unstable", step_interval=timedelta(days=7), max_steps=2
        )

        assert len(commits) == 3  # head + 2 discovered
        assert commits[0].sha == "commit2"  # Chronological order
        assert commits[-1].sha == "head_sha"

    @patch.object(GitHubClient, "get_branch_head")
    @patch.object(GitHubClient, "_get_oldest_commit_in_window")
    def test_discover_commits_with_until_parameter(
        self, mock_get_oldest, mock_get_head
    ):
        until_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        window_commit = GitHubCommit(
            "commit1", datetime(2025, 1, 8, 12, 0, 0, tzinfo=timezone.utc)
        )
        mock_get_oldest.return_value = window_commit

        client = GitHubClient()
        commits = client.discover_commits_at_intervals(
            branch="nixpkgs-unstable",
            step_interval=timedelta(days=7),
            until=until_time,
            max_steps=1,
        )

        # Should not call get_branch_head when until is specified
        mock_get_head.assert_not_called()
        assert len(commits) == 1
        assert commits[0].sha == "commit1"

    @patch.object(GitHubClient, "get_branch_head")
    @patch.object(GitHubClient, "_get_oldest_commit_in_window")
    def test_discover_commits_default_max_steps(self, mock_get_oldest, mock_get_head):
        head_commit = GitHubCommit(
            "head_sha", datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        )
        mock_get_head.return_value = head_commit
        mock_get_oldest.return_value = None  # No commits found

        client = GitHubClient()
        commits = client.discover_commits_at_intervals(
            branch="nixpkgs-unstable",
            step_interval=timedelta(days=7),
            # Note: max_steps not specified
        )

        assert len(commits) == 1  # Only head
        # Verify _get_oldest_commit_in_window was called multiple times
        assert mock_get_oldest.call_count == 1000

    @patch.object(GitHubClient, "get_branch_head")
    @patch.object(GitHubClient, "_get_oldest_commit_in_window")
    def test_discover_commits_returns_chronological_order(
        self, mock_get_oldest, mock_get_head
    ):
        head_commit = GitHubCommit(
            "newest", datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        )
        mock_get_head.return_value = head_commit

        window_commits = [
            GitHubCommit("middle", datetime(2025, 1, 8, 12, 0, 0, tzinfo=timezone.utc)),
            GitHubCommit("oldest", datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)),
        ]
        mock_get_oldest.side_effect = window_commits

        client = GitHubClient()
        commits = client.discover_commits_at_intervals(
            branch="nixpkgs-unstable", step_interval=timedelta(days=7), max_steps=2
        )

        assert commits[0].sha == "oldest"
        assert commits[1].sha == "middle"
        assert commits[2].sha == "newest"


class TestGitHubAPIError:
    def test_raise_github_api_error(self):
        with pytest.raises(GitHubAPIError) as exc_info:
            raise GitHubAPIError("Test error message")

        assert "Test error message" in str(exc_info.value)

    def test_github_api_error_is_exception(self):
        error = GitHubAPIError("Test")
        assert isinstance(error, Exception)
