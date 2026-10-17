## ADDED Requirements

### Requirement: The dashboard draws step events per 100 requests next to the count
The rendered dashboard's `compactions` panel SHALL draw, besides the per-task count and its
trend, `compactions` per 100 `api_requests` per task on a right axis. The `failed + denied
calls` panel SHALL do the same for `failed + denied`.

#### Scenario: Rate panels
- **WHEN** the dashboard is rendered for one repository
- **THEN** each of the two panels reads `api_requests` and draws the count, its trend, and
  `per 100 requests` on the right axis, but not `api_requests`
