# Modernization Plan: Nanomodem Library

This plan outlines the steps to transform this "hacking" repo into a Python library (`nanomodem`) that is easy to consume in ROS2, GUI apps, and other projects.

### Phase 0: Cleanup & Branching
*Goal: Start fresh and remove legacy clutter.*
- [x] Create a new development branch: `git checkout -b refactor/modernize-library`.
- [x] Delete the old `gui/` folder (not the one in `take2`).
- [x] Move contents of `take2/` to the root (temporarily) to flatten the structure.
- [x] Delete any other "dead" files or folders identified during the move.

### Phase 1: Repository & Branding
*Goal: Establish the new identity and clean the slate.*
- [x] Rename GitHub Repository to `nanomodem-python` (or similar).
- [x] Rename local folder: `mv testing-acoustic-modems nanomodem-python`.
- [x] Update local git remote: `git remote set-url origin <new-url>`.
- [x] Create a `.gitignore` if missing (ensure `__pycache__`, `.venv`, and `dist/` are ignored).

### Phase 2: Package Structure (The "Namespace")
*Goal: Organize files so they can be imported as `nanomodem`.*
- [x] Create the nested directory structure: `mkdir -p src/nanomodem`.
- [x] Create `src/__init__.py` (leave empty, this enables the namespace).
- [x] Create `src/nanomodem/__init__.py` (this will be your public API).
- [x] Create sub-folders for organization: `mkdir -p src/nanomodem/{transports,codecs,drivers}`.
- [x] Skip the namespacing completely
- [x] Remove foxpoint from readme. Are there more occurrences of this?
- [x] Remove words like "professional" and other silly stuff like that.
- [x] Rename gui to gui_controller or something similar?

### Intermediate phase
- [x] Fix proper type checking and/or linting.

### Phase 3: Core Logic Refactor
*Goal: Implement the "Pluggable" architecture we discussed.*
- [x] **Protocols**: Define `TransportProtocol` and `DriverProtocol` in `src/nanomodem/protocols.py`.
- [x] **Drivers**: Move the `$Pxxx` command logic into `src/nanomodem/drivers/v3.py`.
- [x] **Node**: Implement the high-level `AcousticNode` in `src/nanomodem/node.py` (using Dependency Injection for Driver/Transport).
- [x] **Types**: Define `Coord` and `NodeState` as `dataclasses` in `src/nanomodem/types.py`.
- [x] **Exports**: Update `src/nanomodem/__init__.py` to export the main classes for easy import.

### Phase 4: Dependency Management (Poetry)
*Goal: Make the project "installable" and manageable.*
- [ ] Initialize Poetry: `poetry init` (follow prompts, use `nanomodem` as name).
- [ ] Configure `pyproject.toml` to use the `src` layout.
- [ ] Add dependencies: `poetry add pyserial` (and any others needed).
- [ ] **Check**: Ensure `build-backend = "poetry.core.masonry.api"` is in `pyproject.toml` for ROS2 compatibility.

### Phase 5: Legacy & Examples
*Goal: Move existing "hacking" code out of the library path.*
- [x] Move `take2/gui` to `apps/gui`.
- [x] Move `take2/nanomodem` (old version) to a `legacy/` folder or delete if no longer needed.
- [x] Update GUI imports to use the new `nanomodem` package.

### Phase 6: Versioning & Publishing (Optional/Future)
*Goal: Move from "commit hashes" to "tags".*
- [ ] **Decision**: Start with `version = "0.1.0-dev"` in `pyproject.toml`.
- [ ] Use `pip install git+https://...` for consumption.
- [ ] (Future) Set up `commitizen` for local tagging.
- [ ] (Future) Add GitHub Action for auto-tagging on merge to main.
- [ ] (Future) Add Discord notification on releases.
- [ ] (Future) Always run tests in PRs and similar.
- [ ] (Future) Make the git repo public.
- [x] (Future) Cursor rules and Claude rules.
- [x] (Future) Easier way of running various things. PYTHONPATH and ugly stuff like that should be avoided. Should either be easy-to-use make targets, or other simple instructions in readme.

---
**Note on Decisions:**
- We chose **`dataclasses`** over `TypedDict` for better Intellisense and methods.
- We chose **Poetry** for the modern "NPM-like" experience.
- We are **skipping** automatic tagging for now to stay fast.
