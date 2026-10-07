# Web-Sourced MVP Scene Pack Implementation Plan

> **For agentic workers:** This plan is being executed inline in the current task, as already authorized by the user.

**Goal:** Add a traceable, openly licensed image pack and four 30-case scenario fixtures so the charging-scene workflow can be smoke-tested without treating simulated states as photo ground truth.

**Architecture:** Reuse the existing 80-image supplement by reference and add only individually reviewed source images to a new small directory. A JSON case manifest will model four 30-case scenarios with `training_eligible=false`; a test will validate counts, file references, attribution, and hashes.

**Tech Stack:** Python standard library, pytest, CSV/JSON, Git.

---

### Task 1: Define the smoke-test data contract

**Files:**
- Create: `algo/tests/test_dataset_scene_mvp.py`
- Create: `algo/dataset_scene_mvp/scene_cases.json`
- Create: `algo/dataset_scene_mvp/licenses.csv`

- [x] Write the test first and confirm it fails because the manifest does not exist.
- [x] Require 30 cases for each of the four named scenario categories.
- [x] Require each referenced image to exist, have attribution and an allowed public license, and match its SHA-256.
- [x] Require every scenario label to be marked simulated and excluded from training.

### Task 2: Curate and register open images

**Files:**
- Create: `algo/dataset_scene_mvp/images/`
- Create: `algo/dataset_scene_mvp/README.md`
- Modify: `algo/dataset_scene_mvp/licenses.csv`

- [x] Copy the 29 visually reviewed, permissively licensed images into the pack.
- [x] Register those images and the existing 80-image supplement in a unified attribution index.
- [x] Assign only visible image-level tags; keep long-dwell/full-not-moved states synthetic.

### Task 3: Populate cases and verify

**Files:**
- Modify: `algo/dataset_scene_mvp/scene_cases.json`
- Modify: `algo/dataset_scene_mvp/README.md`

- [x] Add 30 deterministic smoke-test cases per scenario, each using a distinct image within that scenario.
- [x] Run the targeted test and the algorithm test suite.
- [x] Commit only the plan, new scene pack, and its test; preserve existing untracked user files.
