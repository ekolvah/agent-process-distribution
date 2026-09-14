## 0. Delivery

- [ ] 0.1 Tracking issue for this change (ask the person for the priority, set the Project field); `gh issue develop -c <N>`; `set_status <N> "In progress"`

## 1. Collector and launcher

- [ ] 1.1 Collector config with project/task/attempt labels; launcher creating task and attempt ids and the version tag
- [ ] 1.2 Report per merged PR: tokens by role, cycle time, review rounds, share without fixer commit, turns per issue
- [ ] 1.3 Tests named after `Consumer without telemetry`, `Two agents on one task`, `v1 vs v2 report`, `Filtering`, `Direct launch`, `One session, two issues`

## 2. Verify

- [ ] 2.1 v1 vs v2 report on the same task types

## 3. Deliver

- [ ] 3.1 `ci_check` green; open the PR (body: change name, tracked deferrals as issue links)
- [ ] 3.2 `wait_for_pr`; apply every unresolved thread or reply on the one left to the person; repeat until nothing is unresolved
- [ ] 3.3 `finish_change v2-6-telemetry` — marks this task, `openspec archive v2-6-telemetry -y`, commit, push, `wait_for_pr` on that head
