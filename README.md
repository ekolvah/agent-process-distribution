# agent-process-distribution

A Claude Code plugin that runs an OpenSpec plan → implement → review → deliver process with
enforced gates in a GitHub repository.

## What it is

- **The `agent-process` plugin** for Claude Code: commands, agents, hooks and the
  `agent-process` and `openspec` launchers.
- **A portable skill**, [`skills/agent-process/SKILL.md`](skills/agent-process/SKILL.md): how an
  agent plans a change with OpenSpec, implements it test-first and delivers it as a reviewed PR.
- **Enforced gates** installed into the adopting repository: a quality check, a Claude review of
  every PR head, and a ruleset so the person's approval merges.

## Install

Once per machine, outside any project:

```sh
claude plugin marketplace add "ekolvah/agent-process-distribution#stable"
# then in Claude Code: /plugin -> Marketplaces -> Enable auto-update for agent-process-marketplace
claude plugin install agent-process@agent-process-marketplace
```

Then, in Claude Code inside the repository to adopt, run `/agent-process:init`. It does a dry
run first and asks before changing anything. The full procedure is
[Install](skills/agent-process/SKILL.md#install).

## Usage

In an adopted repository:

- `/opsx:propose <what to build>` plans a change: proposal, specs, design, tasks and an
  architect review.
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

Changes go through the process itself: an issue, an OpenSpec change, a PR reviewed by the
`agent-review` check and merged by the owner's approval. Agents start from
[`CLAUDE.md`](CLAUDE.md); the delivery steps are in
[Delivery](skills/agent-process/SKILL.md#delivery).

## License

[MIT](LICENSE) © ekolvah
