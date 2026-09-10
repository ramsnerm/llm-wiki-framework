# Ceph

Distributed storage system. We run it for the archive tier.

BlueStore is the backend — see [[bluestore]]. Writes go straight to the
block device, which is why it is roughly twice as fast as the old
FileStore setup. Source: the BlueStore paper in raw/.

Operationally the thing that bit us was the RocksDB device sizing. Four
percent of the data device, and if you undersize it you get spillover
that nobody notices for weeks.

Related: [[zfs]], [[erasure-coding]]
