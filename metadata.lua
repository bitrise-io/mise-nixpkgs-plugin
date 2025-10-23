-- metadata.lua
-- Backend plugin metadata and configuration
-- Documentation: https://mise.jdx.dev/backend-plugin-development.html

PLUGIN = { -- luacheck: ignore
    name = "nixpkgs",

    version = "0.1.0",

    description = "A mise backend plugin for installing pre-built tools from Nix and nixpkgs",

    author = "bitriseio",

    homepage = "https://github.com/bitriseio/mise-nixpkgs-plugin",

    license = "MIT",

    notes = {
        "Requires Nix to be installed on your system",
        "This plugin manages tools from the nixpkgs ecosystem",
    },
}
