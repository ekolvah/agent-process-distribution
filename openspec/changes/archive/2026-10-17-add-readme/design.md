## Context

No `README.md` or `LICENSE` exists. Install lives in the Install section of `skills/agent-process/SKILL.md` and
the `plugin-channel` row of `skills/agent-process/scripts/manual.py`. Every tracked `.md` file's
relative links and anchors are already checked by
`tests/agent_process/test_doc_links.py::test_every_internal_link_resolves`, which the declared
`test` runs; the README is covered once tracked.

## Decisions

**D1 — Root `README.md`, standard-readme order, under 100 lines.** Sections: title
`agent-process-distribution`; the one-line description (D3); Why (the problems it solves, one row per spec Purpose: planning, implementation, review-and-merge, state, measurement, distribution); what it is (the Claude Code plugin
`agent-process`, the portable skill, the enforced gates); Install (the three machine-level steps
of the `plugin-channel` row — `claude plugin marketplace add`, Enable auto-update under `/plugin`
→ Marketplaces, `claude plugin install` — then `/agent-process:init` in the target repository);
Usage (`/opsx:propose`, `/opsx:apply`); Where things live (specs, changes, ADRs, principles,
`CHANGELOG.md`); Contributing (changes go through the process itself: links `CLAUDE.md` and the
Delivery section of `SKILL.md`); License: MIT, linking `LICENSE` (the owner chose free use; MIT is the common permissive license, copyright `ekolvah`). No table of contents:
standard-readme makes it optional under 100 lines. Alternative: `.github/README.md` — hidden from
a clone's root listing.

**D2 — Links, not copies.** Each section is a few lines and links its owner; no version number
(release-please would leave it stale); no issue number (the `no-issue-refs` hook). The Install
block is the one copy: the `plugin-channel` row of `manual.py` owns it, and drift is accepted
because `init`'s manual output, printed in every installation, stays authoritative; no check is
added. Alternative: a full install walkthrough — a second home that drifts from `SKILL.md`.

**D3 — One description, said plainly.** The README's description names what the process does,
e.g. "A Claude Code plugin that runs an OpenSpec plan → implement → review → deliver process with
enforced gates in a GitHub repository", and `gh repo edit --description` sets the same text, so the
About sidebar and the README agree. The plugin and marketplace manifest descriptions are left as
they are. Alternative: copy the current description — it is the line that fails to explain.
