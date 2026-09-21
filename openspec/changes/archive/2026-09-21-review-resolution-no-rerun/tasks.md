## 0. Continue the active delivery

- [x] 0.1 Reuse tracking issue 112, branch `v2-2-delivery`, and pull request 151 for this bounded review correction.

## 1. Prove the corrected close round RED

- [x] 1.1 Change the focused resolver contract to require settled-run check, resolve, and reply with no workflow rerun; observe the focused suite RED before implementation.

## 2. Implement the correction

- [x] 2.1 Remove the rerun transport and recovery branch while preserving pre-write settled-head validation and post-resolve reply recovery.
- [x] 2.2 Amend the archived issue-112 design and scenario map for the corrected advisory-review boundary.

## 3. Verify and archive

- [x] 3.1 Run strict OpenSpec validation and the complete repository quality command GREEN.
- [ ] 3.2 Archive `review-resolution-no-rerun` before the next push.

## 4. Review the correction

- [ ] 4.1 Request and wait for current-head review on PR 151; leave this box unchecked because ticking it moves the reviewed head.

## Scenario → test map

| Capability | Scenario | Test evidence |
|---|---|---|
| implementation | Blocking thread addressed | `tests/publisher/test_resolve_review_thread.py::test_close_round_resolves_and_replies_without_rerunning_the_head` |
