# BlueStore: A High-Performance Storage Backend (excerpt)

BlueStore writes object data directly to the block device and keeps all
metadata in RocksDB. Eliminating the local filesystem removes the
journal write that FileStore required for consistency, roughly doubling
write throughput on the authors' hardware.

Checksums are stored per blob and verified on read. The paper measures
the overhead at under two percent for 4 MB objects and notes it rises
sharply for very small objects.

Allocation uses a bitmap-based allocator; the authors report
fragmentation staying under five percent after a year of simulated
mixed workload.
