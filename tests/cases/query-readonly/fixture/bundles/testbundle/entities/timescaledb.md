---
type: entity
title: TimescaleDB
aliases:
  - Timescale
updated: 2026-01-02
---

# TimescaleDB

TimescaleDB is an open-source time-series database implemented as a
PostgreSQL extension, so existing PostgreSQL tooling keeps working
unchanged. ([source](../sources/2026-01-02-timescaledb-notes.md))

Data is stored in hypertables, transparently partitioned by time into
chunks, so a query only touches the chunks its time range covers.
([source](../sources/2026-01-02-timescaledb-notes.md))

Compression is available but falls under the Timescale License rather
than the Apache-2.0 core.
([source](../sources/2026-01-02-timescaledb-notes.md))

## Sources

- [TimescaleDB evaluation notes](../sources/2026-01-02-timescaledb-notes.md)
