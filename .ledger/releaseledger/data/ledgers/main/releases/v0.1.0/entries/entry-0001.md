---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0001
release_version: v0.1.0
kind: added
summary:
  Added native and CLI eSpeak NG backends for IPA phonemization, batching,
  voices, clauses, and diagnostics
status: accepted
audience: null
scopes: []
source_refs:
  - git:4ed12c47d3c3e5e436cdda82a04b0af50091b949
paths:
  - .codecrate.toml
  - .github/workflows/pre-commit.yml
  - .github/workflows/tests.yml
  - .gitignore
  - .ledger/ledger.toml
  - .ledger/releaseledger/.ledger-project.toml
  - .ledger/releaseledger/config.toml
  - .ledger/releaseledger/data/.ledger-project.toml
  - .ledger/taskledger/.ledger-project.toml
  - .ledger/taskledger/config.toml
  - .pre-commit-config.yaml
  - MIGRATION.md
  - README.md
  - espeakng_runtime/__init__.py
  - espeakng_runtime/_text.py
  - espeakng_runtime/backends/__init__.py
  - espeakng_runtime/backends/base.py
  - espeakng_runtime/backends/cli.py
  - espeakng_runtime/backends/native.py
  - espeakng_runtime/discovery.py
  - espeakng_runtime/errors.py
  - espeakng_runtime/py.typed
  - espeakng_runtime/runtime.py
  - espeakng_runtime/types.py
  - pyproject.toml
  - tests/test_discovery.py
  - tests/test_live_espeak.py
  - tests/test_packaging.py
  - tests/test_runtime_selection.py
  - tests/test_text.py
issues: []
prs: []
sources:
  - git:4ed12c47d3c3e5e436cdda82a04b0af50091b949
contributors:
  - "@holgern"
breaking: false
internal: false
order: 1
---
