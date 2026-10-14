## ADDED Requirements

### Requirement: The dashboard renders for a list of repositories
`agent-process dashboard <owner/name>...` SHALL print a Grafana dashboard JSON whose Infinity
datasource is the import input `DS_INFINITY`. Each data panel SHALL hold one query per listed
repository, which reads
`https://raw.githubusercontent.com/<owner/name>/task-readings/task-readings.csv` and gives
every row a `repository` column holding `<owner/name>`, and SHALL merge its queries.
In the table, `task_id` SHALL link to `https://github.com/<repository>/issues/<N>` for the
`<N>` of its `issue-<N>`. An argument that is not `<owner>/<name>` (a name of `.` or `..`
included), or no argument, SHALL exit 2 and print nothing on stdout. A repository listed twice,
in any letter case, SHALL render once, as first spelled.

#### Scenario: One repository
- **WHEN** the dashboard is rendered for `ekolvah/kinozal_scraper`
- **THEN** every data panel has exactly one query, which reads that repository's CSV through
  `${DS_INFINITY}`, and the table's `task_id` link resolves to that repository's issue

#### Scenario: Several repositories
- **WHEN** the dashboard is rendered for two repositories
- **THEN** every data panel has two queries, one per repository, each with its own
  `repository` value, and merges them into one result

#### Scenario: Repeated repository
- **WHEN** the dashboard is rendered for a repository, another, and the first again in upper case
- **THEN** every data panel has two queries, in first-listed order

#### Scenario: Malformed repository
- **WHEN** the dashboard is rendered for `kinozal_scraper`
- **THEN** the command exits 2, names the argument, and prints nothing on stdout
