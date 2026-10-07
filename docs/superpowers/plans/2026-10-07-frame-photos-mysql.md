# Close week-two acceptance gaps

## Goal

Finish the user's requested integration solo: expose the latest frame endpoint and page, add traceable openly licensed online photo examples where the existing pool has a gap, and install/start an isolated MySQL 8 instance in the workspace. Preserve the original limitation that static images cannot prove time-dependent charging/parking states.

## Plan

- [x] Add failing backend regression tests for the latest-frame API, then implement the endpoint and enable the preview page.
- [x] Update the contract, E2E checks, and week-two acceptance record with the verified frame behavior.
- [x] Review the existing online photo pool and license records; retain the 80 openly licensed raw photos and document that the original four-class campus acceptance cannot be inferred or fabricated from static generic images.
- [x] Install MySQL 8 into an ignored workspace-local directory, bind only to loopback, initialize a dedicated test database, and run the schema verifier against it.
- [x] Run backend/frontend/algorithm/design checks and real HTTP E2E; complete self-review and commit the changes.
