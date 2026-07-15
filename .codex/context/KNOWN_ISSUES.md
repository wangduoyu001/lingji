# Known Issues

- The original project describes a site, but the inspected code is a background Python scheduler with no HTTP site.
- Qdrant Docker service is not running on this machine, so the second brain uses isolated embedded Qdrant by default.
- `bge-m3` was not installed at audit time; fallback embedding remains available.
- Initial Obsidian indexing can take time because every Markdown document needs an embedding. The watcher can remain off until the API is healthy.
