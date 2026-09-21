## Context

See `proposal.md` — Why and the `roles`/`distribution` delta specs. Current `main` has the
stock OpenSpec entry points for both carriers, but the portable project procedure is copied
as long rule bodies in `openspec/config.yaml`, and the seven scripts those rules execute are
mixed into the repository-only `.agent-process/scripts/` control plane. The Claude plugin is
metadata-only at version `0.1.0`; this publisher does not enable it locally.

ADR 0027 already decides that the procedure is written once as Agent Skills and that delivery
uses a Claude plugin plus Codex skills. The frozen PR #151 demonstrates the concrete package
shape: a plugin-root `skills/agent-process/` directory with optional `scripts/`, and it exposed
path/import defects separately from installer defects. This change adopts only that package
boundary. Issues #155, #156, #153, #154, #114, and #115 own every later state transition.

## Goals / Non-Goals

**Goals:**

- Establish one reviewable portable procedure source for both carriers.
- Move only scripts the shared procedure directly invokes and preserve their current behavior.
- Make the publisher exercise the plugin/skill source without installing anything elsewhere.
- Leave a stable package boundary on which #155 can build the local installer.

**Non-Goals:**

- Any `init` command, installer template, consumer repository write, user checkout/link, or
  GitHub Project operation (#155 and #156).
- Landing or activating a workflow or required check (#153 and #154).
- Changing review policy, Project delivery state, v1 hooks, or the remaining control plane
  (#114 and #115).
- Publishing the immutable `v2.0.0` tag; that remains a person action after the full #112
  sequence merges.

## Decisions

### D1. One shared skill owns procedure; OpenSpec remains the entry point

Add `skills/agent-process/SKILL.md` with sections for proposal, specifications, design,
tasks, architect review, and delivery. The content is a structural move of the current
`openspec/config.yaml` rules, with paths adjusted only for D2; it does not adopt PR #151's
advisory-review procedure. The stock OpenSpec skills remain the user-facing entry points and
load project context from `openspec/config.yaml`. Each artifact rule in that config becomes a
short directive to follow the matching shared-skill section.

The Claude plugin discovers the skill from its standard `skills/` directory. The later Codex
installer will link this exact directory; this change adds no user-level link. The existing
Claude `architect-reviewer` remains the independent reviewer adapter and points to the shared
architect-review contract; Codex continues to self-review.

Alternative: keep full rules in `openspec/config.yaml`. Rejected because each consumer would
again own a copied procedure body. Alternative: replace the stock OpenSpec skills. Rejected
because ADR 0027 chose their maintained artifact workflow and both carriers already expose
them.

### D2. Move the seven portable scripts, not the control plane

Move `archive_change`, `check_red`, `create_tracking_issue`, `resolve_review_thread`,
`set_status`, `start_change`, and `wait_for_pr` under `skills/agent-process/scripts/`. These
are the scripts named by the portable procedure. Their command help and every emitted
continuation/recovery command use paths resolved from the skill directory. Sibling imports
use that directory directly, without importing the remaining repository-only `scripts`
package.

`start_change`, `create_tracking_issue`, and `archive_change` operate on the consumer
repository in which the command is invoked; their repository root is therefore `Path.cwd()`,
not a fixed number of parents above the installed skill. Tests import moved modules from
their file paths and explicitly prove consumer-root resolution from a temporary `cwd`.

All other `.agent-process/scripts/` files stay where they are. In particular,
`request_codex_review.py`, `review_gate.py`, hooks, CI, protection, and state/control-plane
scripts keep their present behavior and paths until their owning issues.

Alternative: copy the seven files and keep compatibility wrappers. Rejected because two
executable copies would make the package source ambiguous. Alternative: move the whole
script tree. Rejected because it would absorb #114/#115 and recreate PR #151's oversized
transition.

### D3. Package identity and publisher dogfood are source-only

Set both Claude manifests to `2.0.0` and add the two portable plugin keys to this repository's
existing `.claude/settings.json`, preserving its telemetry, permissions, and hooks. Publisher
tests prove manifest equality, exactly one shared skill directory, the expected seven scripts,
absence of installer/templates/hooks inside the plugin package, and retention of
repository-only settings outside that package.

The future immutable tag does not yet exist and no consumer references `v2.0.0` in this
change. The version denotes the in-repository package being assembled by #112; the person
creates the release tag only after the sequence completes.

Alternative: postpone all metadata until the installer. Rejected because the package PR
would not exercise the same plugin discovery path it claims to establish. Alternative:
publish/tag now. Rejected because #155/#156/#153/#154 are required before the package is a
usable release.

### D4. Pointer tests preserve every current proof

`tests/publisher/test_planning_workflow.py` reads the shared skill for every procedural
assertion it currently reads from `rules`, while separately proving that config retains the
project context and contains one pointer per artifact. Delivery-script and thread-resolution
tests load the moved source without changing assertions about issue creation, RED, archive,
wait settling, Codex request/fallback ordering, rerun, thread resolution, or the review gate.

No project-declared input is replaced and no guard is dropped: this is a source relocation.
The unchanged current-head CI/review workflow is the delivery catcher for this PR, and the
path-contract tests fail before implementation if any command or import still relies on an
old location.

Alternative: test only that files exist. Rejected because PR #151 showed that structural
presence does not prove consumer `cwd`, sibling imports, or emitted recovery commands.

### D5. The package has a hard stop before installer state

This change contains no `commands/init.md`, `init.py`, templates directory, consumer fixture,
user checkout/link, Project call, workflow replacement, ruleset payload, or protection API.
Tests enumerate the package tree and reject those additions. Documentation names #155 and
#156 as the next steps rather than describing not-yet-delivered installation behavior.

Alternative: include dormant templates for convenience. Rejected because template ownership
and version handoff are behavior of #155 and would make this package review depend on an
installer that does not exist yet.

## Risks / Trade-offs

- [Moving delivery scripts can break the flow used to deliver its own fix] → RED path/import,
  consumer-root, help, and recovery-command tests precede the move; the implementation PR
  remains protected by the unchanged v1 workflow and review gate.
- [A pointer is too vague for an agent to follow] → each pointer names one exact skill
  section, and planning tests assert the resolved section retains every current contract.
- [The `2.0.0` metadata exists before a release tag] → no consumer pin or installer ships in
  this change; manifest equality and the person-owned post-sequence tag boundary are explicit.
- [The publisher has settings consumers will never receive] → package tests distinguish the
  two portable plugin keys from telemetry, permissions, and v1 hooks retained only here.

## Migration Plan

1. Add RED tests for shared-source ownership, exact moved-script set, consumer-root/sibling
   path behavior, rule pointers, manifest identity, and publisher dogfood.
2. Add the shared skill by moving the current procedure text without policy changes; move
   the seven scripts and make the RED path tests green.
3. Point config and adapter/docs references at the shared source, enable the local plugin,
   and make package/version tests green.
4. Run strict OpenSpec validation and the complete current CI command; archive and deliver
   under the unchanged v1 workflow/review gate.
5. On failure, revert this PR as a unit. It creates no consumer, user-profile, Project,
   workflow, or protection state. After merge, #155 starts from the established package.
