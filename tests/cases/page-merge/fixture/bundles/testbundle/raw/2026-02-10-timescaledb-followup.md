# TimescaleDB — follow-up after the pilot

Two corrections to the earlier evaluation, after running a pilot for six
weeks.

Compression is not merely a licensing footnote. On our workload it
reduced storage for chunks older than seven days by roughly 92 percent,
which changes the cost picture entirely and makes retention of two years
practical where we had budgeted for three months.

The claim that "existing PostgreSQL tooling keeps working unchanged"
needs qualifying. pg_dump works, but restoring a dump into a database
where the extension is not yet installed fails in a way that is hard to
read. The extension has to be created first.

One thing not covered before: hypertables can be partitioned by a second
dimension besides time, typically a device or tenant identifier. That
only pays off above a few thousand distinct values.
