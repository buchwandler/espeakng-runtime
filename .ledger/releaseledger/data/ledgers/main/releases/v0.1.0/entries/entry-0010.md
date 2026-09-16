---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0010
release_version: v0.1.0
kind: fixed
summary:
  Fixed CLI fallback after native initialization failures and normalized native
  and CLI data paths
status: accepted
audience: null
scopes: []
source_refs: []
paths:
  - espeakng_runtime/runtime.py
  - espeakng_runtime/backends/cli.py
  - espeakng_runtime/backends/native.py
  - tests/test_runtime_selection.py
issues: []
prs: []
sources:
  - git:bfe71567fd5d39c1f5744c5d23701d05d67d66af
contributors: []
breaking: false
internal: false
order: 10
---
