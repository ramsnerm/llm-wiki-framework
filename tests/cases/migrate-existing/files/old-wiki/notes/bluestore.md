# BlueStore

Ceph's storage backend since Luminous. Writes to raw block devices.

Checksums on every read — under two percent overhead for large objects,
much worse for small ones (from the paper).

> [!NOTE]
> This callout is Obsidian syntax and should not survive migration.
