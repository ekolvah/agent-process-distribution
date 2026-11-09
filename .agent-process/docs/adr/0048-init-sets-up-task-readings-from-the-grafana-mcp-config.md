---
status: "accepted"
date: 2026-11-07
decision-makers: ekolvah
---

# Init sets up task readings from the Grafana MCP config

## Context and Problem Statement

[ADR 0041](0041-adopters-record-task-readings-in-their-own-stack.md) D4 left the
`GRAFANA_URL` variable, the `GRAFANA_SERVICE_ACCOUNT_TOKEN` secret and the per-task dashboard
import to the person, as the `manual task-readings` row. A machine that runs the `grafana` MCP
server already holds that stack's URL and a service account token in `~/.claude.json`, and the
agent did the three steps by hand from it; the OTLP endpoint of the session export names no
stack.

## Considered Options

* `init` reads the user-scope `grafana` MCP server config and sets up all three as steps
* A separate `task_readings_setup` command
* Create a dedicated Viewer service account in the stack

## Decision Outcome

Chosen: **steps of `init` from the MCP config.**

* **D1 — the source.** Only `mcpServers.grafana.env` of `~/.claude.json`: `GRAFANA_URL`, and
  `GRAFANA_SERVICE_ACCOUNT_TOKEN` or the content of `GRAFANA_SERVICE_ACCOUNT_TOKEN_FILE`, the
  forms mcp-grafana documents. Project-scope entries and `.mcp.json` are not read.
* **D2 — the token is copied.** The secret gets the MCP token on `gh`'s standard input; the
  dry-run's `task-readings-token` line names its source. Creating a service account needs
  `serviceaccounts:create`, which the observed token lacked.
* **D3 — after the pre-push step.** `task-readings-url`, `-token` and `-dashboard` are the
  run's last steps, so a failed Grafana write cannot stop the installation PR. A repository
  whose `GRAFANA_URL` names another stack gets no step and no Grafana request. The row prints
  only for what no step sets up, ending with `(not found: …)`, `(another stack: …)` or
  `(cannot read: …)`.

### Consequences

* Good, because on a machine with the MCP server the readings record from the first merged task
  PR without a manual step.
* Bad, because the repository secret holds the person's MCP token, which may have more than
  Viewer rights, and the repository's workflows can use it; the person can replace the secret
  with a Viewer token.
* Bad, because the dashboard is identified by its rendered title: a renamed dashboard leads to
  a second import.

### Pros and Cons of the Options

* Separate command — Install gains a step the agent must remember.
* Dedicated service account — needs a permission the observed token does not have.

### Confirmation

`tests/publisher/test_init_readings.py` holds D1–D3, and
`tests/publisher/test_init_remote.py::test_readings_prerequisites_are_printed` the row without
a config.
