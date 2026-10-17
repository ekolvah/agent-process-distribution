## ADDED Requirements

### Requirement: The dashboard draws step events per 100 requests
The rendered dashboard's compactions panel SHALL draw, per task, `compactions` per 100
`api_requests`, and its failed-and-denied panel SHALL draw `failed` plus `denied` per 100
`api_requests`; each panel's trend SHALL be the trailing mean of that rate.

#### Scenario: Rate panels
- **WHEN** the dashboard is rendered for one repository
- **THEN** each of the two panels draws its rate and windows its trend over it
