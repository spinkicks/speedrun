# Clean-machine BUILD prerequisites (desktop installer)

To build the Speedrun desktop installer on a clean Windows machine:
1. Toolchain: Rust (rustup auto-pins 1.92.0 via rust-toolchain.toml), Python via `uv`, Node + yarn 1.22, MSVC build tools, MSYS2 (`git`, `rsync`), the `n2` build tool (`bash tools/install-n2`), `just`.
2. Clone the fork branch: `git clone -b <branch> https://github.com/spinkicks/anki` — the Briefcase Windows/mac templates are now vendored IN-TREE (no submodule fetch needed; only the `ftl/*` submodules remain and are optional for the installer).
3. Build: `just build`; installer: `uv run python qt/tools/build_installer.py --version $(cat .version) build && … package`.
4. NO network is required for the installer TEMPLATE step. (`ftl/*` submodules need network only if translations are rebuilt.)
Note: the `render.rs` OS-path-separator fix (already committed) is required for n2 on Windows.
