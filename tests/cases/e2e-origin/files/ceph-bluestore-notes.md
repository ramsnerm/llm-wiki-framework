# Ceph BlueStore — operational notes

BlueStore is the storage backend Ceph OSDs use to write directly to raw
block devices, replacing the older FileStore which wrote through a local
filesystem. Removing that layer removed the double-write penalty of the
journal, which is where most of the throughput gain comes from.

Metadata lives in RocksDB alongside the data device. On spinning disks it
is usually worth putting that RocksDB database and the write-ahead log on
a separate SSD; the rule of thumb is roughly four percent of the data
device size, and undersizing it causes spillover back onto the slow
device, which is hard to notice and expensive.

Checksums are computed on every write and verified on every read, so
silent corruption surfaces as a read error rather than as wrong data.
That is a change in kind from FileStore, which trusted the filesystem.

Compression is per-pool and off by default. It is worth enabling for
cold archival pools and rarely worth it for anything latency-sensitive.
