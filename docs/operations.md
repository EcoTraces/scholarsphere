# ScholarSphere Operations Baseline

## Environments

- Development: local dependencies and sandbox integrations.
- Testing: automated integration, API, migration, and browser tests.
- Staging: production-like infrastructure with synthetic data.
- Production: approved releases only, managed secrets, encrypted storage, and
  restricted administrative access.

## Release Gate

Production deployment is blocked unless:

- Automated tests and static analysis pass.
- Critical logic coverage is at least 80 percent.
- Mandatory eligibility rules have complete test coverage.
- No unresolved critical security finding exists.
- Database migrations are reviewed and reversible.
- A different administrator approves the production deployment.

Use immutable release versions and container image digests. Prefer blue-green
deployment for normal releases and canary deployment for higher-risk changes.
Retain the previous healthy version until production validation completes.

## Backup and Recovery

- Recovery Point Objective: 15 minutes.
- Recovery Time Objective: 4 hours.
- Full database backup: daily.
- Transaction-log backup: continuous, with no more than 15 minutes exposure.
- File-storage backup: daily and incremental where supported.
- Encryption: required in transit and at rest.
- Location: separate account or recovery region.
- Retention: 35 days by default.
- Restoration test: monthly in an isolated environment.

During a disaster, declare the incident, freeze unsafe writes, verify backup
integrity, restore in the recovery region, run security and data validation,
approve failover, and communicate through the status channel. Emergency
contacts and service restoration ownership must be maintained outside the
primary platform.

## Observability

Production services must emit structured logs, correlation IDs, distributed
traces, and metrics for request volume, error rate, latency, active users,
database connections and query time, queue depth and failed jobs, notification
failures, verification backlog, source failures, storage, CPU, memory, and
search-index health. Alert routes must be tested and incidents reviewed.
