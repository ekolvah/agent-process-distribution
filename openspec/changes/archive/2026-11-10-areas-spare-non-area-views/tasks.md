## 0. Delivery start

- [x] 0.1 On the branch of the `init-replaces-project-areas` PR (tracking issue 493)

## 1. Fix

- [x] 1.1 RED `tests/publisher/test_init_remote.py::test_areas_not_replaced[foreign-view]`; `project_areas.py` leaves a Project with a given area's non-area view `unchanged`, and fails the step on the copy; `test_areas_spare_a_non_area_view_of_the_copy` covers the copy

## 2. Deliver

- [x] 2.1 Run `agent-process archive_change areas-spare-non-area-views`

## Scenario → test map

| Scenario | Test |
| --- | --- |
| distribution / Areas not replaced | `tests/publisher/test_init_remote.py::test_areas_not_replaced` (gains `foreign-view`) |
| distribution / Copy keeps its other views | `tests/publisher/test_init_remote.py::test_areas_spare_a_non_area_view_of_the_copy` |
