# ZFS

Used on the backup boxes, not on the cluster. Kept here because we keep
comparing it to [[ceph]].

Copy-on-write, checksummed, and the snapshot story is far better. It does
not scale out, which is why it lost for the archive tier.
