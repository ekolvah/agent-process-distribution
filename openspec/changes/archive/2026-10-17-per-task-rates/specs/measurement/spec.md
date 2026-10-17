## ADDED Requirements

### Requirement: The dashboard draws step events per 100 requests next to the count
The rendered dashboard's compactions panel SHALL draw, per task, `compactions` per 100
`api_requests`, and its failed-and-denied panel SHALL draw `failed` plus `denied` per 100
`api_requests`, each as an added line on a right axis; the count and its trailing-mean trend
SHALL stay.

#### Scenario: Rate panels
- **WHEN** the dashboard is rendered for one repository
- **THEN** each of the two panels draws its count with its trend, and its rate on a right axis
