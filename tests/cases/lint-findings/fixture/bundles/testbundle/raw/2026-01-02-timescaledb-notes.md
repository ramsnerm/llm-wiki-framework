# TimescaleDB evaluation notes

TimescaleDB is an open-source time-series database built as an extension
to PostgreSQL. Because it is an extension rather than a separate engine,
existing PostgreSQL tooling — psql, pg_dump, standard drivers — keeps
working unchanged.

Its central idea is the hypertable: a table that is transparently
partitioned by time into chunks. Queries address the hypertable as if it
were an ordinary table, while the planner only touches the chunks a
query's time range actually covers.

Continuous aggregates are materialised views that refresh incrementally
rather than being recomputed. For dashboards over long ranges this is
the difference between a query that scans years of raw rows and one that
reads a few thousand pre-aggregated ones.

The licence is worth noting: the core is Apache 2.0, but several
features — including compression — are under the Timescale License,
which restricts offering the software as a managed service.
