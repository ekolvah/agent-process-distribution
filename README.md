# agent-process-distribution

A Claude Code plugin that takes a GitHub issue to a merged PR through a planned, tested and
reviewed process, where nothing reaches the default branch without passing checks, a Claude
review and the owner's approval.

## What it is

- **The `agent-process` plugin** for Claude Code: commands, agents, hooks and the
  `agent-process` and `openspec` launchers.
- **A portable skill**, [`skills/agent-process/SKILL.md`](skills/agent-process/SKILL.md): the
  procedure the agent follows. Each change is planned with
  [OpenSpec](https://github.com/Fission-AI/OpenSpec) — a proposal, spec deltas, a design and
  tasks under `openspec/` — implemented test-first and delivered as a PR.
- **Gates** installed into the adopting repository: a required quality check and a required
  Claude review on every PR, enforced by a branch ruleset. The agent opens PRs under its own bot
  account; the owner's approval merges them.

## Install

Requires: Claude Code, `gh` logged in with the `project` scope, admin rights on the repository,
and a bot GitHub account for the agent. The default quality baseline is a Python toolchain.

Once per machine, outside any project:

```sh
claude plugin marketplace add "ekolvah/agent-process-distribution#stable"
# then in Claude Code: /plugin -> Marketplaces -> Enable auto-update for agent-process-marketplace
claude plugin install agent-process@agent-process-marketplace
```

Then, in Claude Code inside the repository to adopt, run `/agent-process:init`. It dry-runs and
asks before changing anything. The full procedure is
[Install](skills/agent-process/SKILL.md#install).

## Usage

In an adopted repository:

- `/opsx:propose <what to build>` plans a change and has it reviewed by an architect agent.
- `/opsx:apply <change>` implements an approved plan and delivers it as a PR.

## Where things live

| Path | Holds |
| --- | --- |
| [`openspec/specs/`](openspec/specs/) | what the process does today |
| [`openspec/changes/`](openspec/changes/) | changes in flight |
| [`.agent-process/docs/adr/`](.agent-process/docs/adr/) | why: decisions and alternatives |
| [`skills/agent-process/always-on.md`](skills/agent-process/always-on.md) | goal function and principles |
| [`CHANGELOG.md`](CHANGELOG.md) | releases |

## Contributing

Changes go through the process itself: issue → OpenSpec change → reviewed PR. Agents start at
[`CLAUDE.md`](CLAUDE.md); see [Delivery](skills/agent-process/SKILL.md#delivery).

## License

[MIT](LICENSE) © ekolvah
