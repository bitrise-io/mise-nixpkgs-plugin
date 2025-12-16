describe("nix.current_system", function()
    local nix
    local mock_runtime = require("spec.helpers.mock_runtime")

    before_each(function()
        package.loaded["nix"] = nil
        mock_runtime.restore_runtime()
    end)

    it("returns x86_64-linux for amd64 linux", function()
        mock_runtime.inject_runtime(mock_runtime.create_runtime({
            osType = "linux",
            archType = "amd64",
        }))
        nix = require("lib.nix")
        assert.equals("x86_64-linux", nix.current_system())
    end)

    it("returns aarch64-linux for arm64 linux", function()
        mock_runtime.inject_runtime(mock_runtime.create_runtime({
            osType = "linux",
            archType = "arm64",
        }))
        nix = require("lib.nix")
        assert.equals("aarch64-linux", nix.current_system())
    end)

    it("returns x86_64-darwin for amd64 darwin", function()
        mock_runtime.inject_runtime(mock_runtime.create_runtime({
            osType = "darwin",
            archType = "amd64",
        }))
        nix = require("lib.nix")
        assert.equals("x86_64-darwin", nix.current_system())
    end)

    it("returns aarch64-darwin for arm64 darwin", function()
        mock_runtime.inject_runtime(mock_runtime.create_runtime({
            osType = "darwin",
            archType = "arm64",
        }))
        nix = require("lib.nix")
        assert.equals("aarch64-darwin", nix.current_system())
    end)

    it("errors on windows with amd64", function()
        mock_runtime.inject_runtime(mock_runtime.create_runtime({
            osType = "windows",
            archType = "amd64",
        }))
        nix = require("lib.nix")
        assert.has_error(function()
            nix.current_system()
        end, "Windows is not supported by Nix")
    end)

    it("errors on windows with arm64", function()
        mock_runtime.inject_runtime(mock_runtime.create_runtime({
            osType = "windows",
            archType = "arm64",
        }))
        nix = require("lib.nix")
        assert.has_error(function()
            nix.current_system()
        end, "Windows is not supported by Nix")
    end)

    it("errors on unsupported architecture riscv64", function()
        mock_runtime.inject_runtime(mock_runtime.create_runtime({
            osType = "linux",
            archType = "riscv64",
        }))
        nix = require("lib.nix")
        assert.has_error(function()
            nix.current_system()
        end, "Unsupported architecture: riscv64")
    end)

    it("errors on unsupported architecture i386", function()
        mock_runtime.inject_runtime(mock_runtime.create_runtime({
            osType = "linux",
            archType = "i386",
        }))
        nix = require("lib.nix")
        assert.has_error(function()
            nix.current_system()
        end, "Unsupported architecture: i386")
    end)
end)
