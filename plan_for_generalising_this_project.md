# Modernization Plan: Foxpoint Nanomodem Library

This plan outlines the steps to transform this "hacking" repo into a professional, namespaced Python library (`foxpoint.nanomodem`) that is easy to consume in ROS2, GUI apps, and other projects.

### Phase 0: Cleanup & Branching
*Goal: Start fresh and remove legacy clutter.*
- [ ] Create a new development branch: `git checkout -b refactor/modernize-library`.
- [ ] Delete the old `gui/` folder (not the one in `take2`).
- [ ] Move contents of `take2/` to the root (temporarily) to flatten the structure.
- [ ] Delete any other "dead" files or folders identified during the move.

### Phase 1: Repository & Branding
*Goal: Establish the new identity and clean the slate.*
- [ ] Rename GitHub Repository to `nanomodem-python` (or similar).
- [ ] Rename local folder: `mv testing-acoustic-modems nanomodem-python`.
- [ ] Update local git remote: `git remote set-url origin <new-url>`.
- [ ] Create a `.gitignore` if missing (ensure `__pycache__`, `.venv`, and `dist/` are ignored).

### Phase 2: Package Structure (The "Namespace")
*Goal: Organize files so they can be imported as `foxpoint.nanomodem`.*
- [ ] Create the nested directory structure: `mkdir -p src/foxpoint/nanomodem`.
- [ ] Create `src/foxpoint/__init__.py` (leave empty, this enables the namespace).
- [ ] Create `src/foxpoint/nanomodem/__init__.py` (this will be your public API).
- [ ] Create sub-folders for organization: `mkdir -p src/foxpoint/nanomodem/{transports,codecs,drivers}`.

### Phase 3: Core Logic Refactor
*Goal: Implement the "Pluggable" architecture we discussed.*
- [ ] **Protocols**: Define `TransportProtocol` and `DriverProtocol` in `src/foxpoint/nanomodem/protocols.py`.
- [ ] **Drivers**: Move the `$Pxxx` command logic into `src/foxpoint/nanomodem/drivers/v3.py`.
- [ ] **Node**: Implement the high-level `AcousticNode` in `src/foxpoint/nanomodem/node.py` (using Dependency Injection for Driver/Transport).
- [ ] **Types**: Define `Coord` and `NodeState` as `dataclasses` in `src/foxpoint/nanomodem/types.py`.
- [ ] **Exports**: Update `src/foxpoint/nanomodem/__init__.py` to export the main classes for easy import.

### Phase 4: Dependency Management (Poetry)
*Goal: Make the project "installable" and manageable.*
- [ ] Initialize Poetry: `poetry init` (follow prompts, use `foxpoint-nanomodem` as name).
- [ ] Configure `pyproject.toml` to use the `src` layout.
- [ ] Add dependencies: `poetry add pyserial` (and any others needed).
- [ ] **Check**: Ensure `build-backend = "poetry.core.masonry.api"` is in `pyproject.toml` for ROS2 compatibility.

### Phase 5: Legacy & Examples
*Goal: Move existing "hacking" code out of the library path.*
- [ ] Move `take2/gui` to `apps/gui`.
- [ ] Move `take2/nanomodem` (old version) to a `legacy/` folder or delete if no longer needed.
- [ ] Update GUI imports to use the new `foxpoint.nanomodem` package.

### Phase 6: Versioning & Publishing (Optional/Future)
*Goal: Move from "commit hashes" to "tags".*
- [ ] **Decision**: Start with `version = "0.1.0-dev"` in `pyproject.toml`.
- [ ] Use `pip install git+https://...` for consumption.
- [ ] (Future) Set up `commitizen` for local tagging.
- [ ] (Future) Add GitHub Action for auto-tagging on merge to main.
- [ ] (Future) Add Discord notification on releases.
- [ ] (Future) Always run tests in PRs and similar.
- [ ] (Future) Make the git repo public.
- [ ] (Future) Cursor rules and Claude rules.

---
**Note on Decisions:**
- We chose **`foxpoint.nanomodem`** as the namespace to avoid collisions and look professional.
- We chose **`dataclasses`** over `TypedDict` for better Intellisense and methods.
- We chose **Poetry** for the modern "NPM-like" experience.
- We are **skipping** automatic tagging for now to stay fast.
