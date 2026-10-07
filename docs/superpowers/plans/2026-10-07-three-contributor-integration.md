# Three Contributor Week Two Integration Plan

> **For agentic workers:** Execute inline in this task as requested by the user. Keep each source contribution traceable and commit each completed change.

**Goal:** Integrate Tang Jinrui, Wu Heqing, and Lu Hao's week-two deliveries on `main`, close verifiable gaps, and leave an evidence-based acceptance record.

**Architecture:** Wu and Lu's reviewed work is already an ancestor of `main`; preserve it. Merge Tang's `origin/feature/api-week2` and the photo-supplement commit `codex/tang-photo-supplement`, then resolve integration gaps against the existing API contract, frontend stores, tests, and week-two acceptance checklist. Do not mark campus-only or environment-dependent acceptance items complete without their required evidence.

**Tech Stack:** Git, FastAPI/Python/pytest/Ruff, Vue 3/Vitest/TypeScript/Vite, MySQL 8, algorithm validation scripts, Markdown acceptance records.

---

### Task 1: Integrate Tang's branch and photo supplement

**Files:** Merge `origin/feature/api-week2` and `codex/tang-photo-supplement` into `main`; preserve user-owned untracked files.

- [x] Confirm Wu and Lu commits are already ancestors of `main` and identify all Tang-only commits.
- [x] Merge the Tang API/algorithm branch, resolve any conflicts without reverting the reviewed UI work, and merge the 80-photo supplement commit.
- [x] Run relevant backend, algorithm, frontend, and design checks; retain the exact commands and results for the acceptance record.

### Task 2: Close frontend/API integration gaps

**Files:** `frontend/src/`, `frontend/tests/`, backend contract tests, and API documentation where the existing implementations show a concrete mismatch.

- [x] Add a failing regression test for each uncovered C1/C2/C3 request/response or error-handling mismatch before changing production code.
- [x] Connect the charging-status, statistics, and configuration pages to the merged API contract while preserving pagination and vehicle CRUD behavior already on `main`.
- [x] Verify the three pages with Vitest, TypeScript, ESLint, production build, and real HTTP E2E coverage.

### Task 3: Recheck algorithm and database evidence

**Files:** `algo/`, `backend/`, `scripts/verify_mysql.py`, and `docs/acceptance/`.

- [x] Validate Tang's real-weight selection, recognition result shape, simulator timeout/time-zone handling, image/label manifests, and MySQL verification evidence on the integrated tree.
- [x] Use authorized workspace/runtime evidence: no campus four-class photo set was present; installed MySQL 8.0.46 locally and reverified the dedicated test DB 19/19.
- [x] Keep the 80 unlabelled web photos as a licensed acquisition pool until labels and split metadata make them training-ready.

### Task 4: Reconcile acceptance records and final gates

**Files:** `docs/WEEK2_ACCEPTANCE.md`, `docs/TASK_TRACKING_TANG.md`, `docs/TASK_TRACKING_LUHAO.md`, `docs/TASK_TRACKING_WU.md`, and relevant progress/evidence documents.

- [x] Update statuses only where merged code and reproducible evidence satisfy the original acceptance criterion; retain open items with a named next action.
- [x] Run backend pytest/Ruff, frontend Vitest/type/lint/build, design checks, algorithm tests available in the environment, and the expanded 20-item E2E suite.
- [x] Perform a self-review of the complete `main` diff, run `git diff --check`, and commit the integrated result.
