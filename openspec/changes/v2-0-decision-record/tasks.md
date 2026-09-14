## 1. ADR

- [ ] 1.1 Write ADR "v2" from `design.md`: context, decision, Considered options (trade study OpenSpec vs Spec Kit vs bespoke), Native alternatives considered, deletion condition
- [ ] 1.2 Mark ADR 0011, 0013, 0015, 0019, 0021, 0022, 0023 superseded by "v2"
- [ ] 1.3 Verify: `test_doc_links` green; the ADR has both sections required by this change's spec

## 2. Deliver

- [ ] 2.1 `ci_check` green; open the PR; address review threads
- [ ] 2.2 Last commit: `openspec archive v2-0-decision-record -y`; push; wait for the checks on that head (v1 delivery, `finish_change` arrives with v2-1)
