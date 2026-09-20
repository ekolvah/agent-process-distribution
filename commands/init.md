---
description: Install or update agent-process in the current repository.
argument-hint: --test "<command>" [--setup "<command>"]
allowed-tools: Bash(python:*)
---

Load the `agent-process` skill and follow its **Install** section. Collect a required
literal test command and an optional literal setup command. Run the skill's `init.py`
with `--dry-run`, show its complete plan, ask once for confirmation, and rerun it with
`--confirm-remote`. Never ask for or read a secret value; the installer prints the
person-owned secret and UI steps.
