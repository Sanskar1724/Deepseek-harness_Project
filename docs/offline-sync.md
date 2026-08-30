# Offline Sync Design (Phase 13)

## Overview

Field workers in the NER frequently operate in areas with no or intermittent
connectivity. The reporting system is designed to support offline-first
capture with reliable background sync.

## Client Architecture (Conceptual)

```
Field Device (mobile/tablet)
  -> Local store (IndexedDB / SQLite)
  -> Sync queue (FIFO)
  -> Sync worker (background, retries with exponential backoff)
```

## Server Contract

### `FieldReport` schema fields for sync

- `client_id` (string, UUID): Client-generated unique ID. Server uses
  `INSERT OR IGNORE`-like semantics: if a report with this `client_id`
  already exists, the server returns the existing record and sets
  `sync_status = "conflict"` on the duplicate.
- `sync_status` (string): One of `local`, `synced`, `conflict`.
  - `local`: Created on device, not yet uploaded.
  - `synced`: Server acknowledged.
  - `conflict`: Server detected a duplicate or mismatch.
- `timestamp` (datetime): When the observation happened (device clock).
- `received_at` (datetime): When the server stored it. Null until first sync.

### POST /api/v1/reports

- If `client_id` is new: insert, set `received_at`, return 201.
- If `client_id` exists: return existing record with `sync_status="conflict"`, 200.

### Sync Algorithm (client-side)

1. On capture: write to local store with `sync_status="local"`.
2. On connectivity: POST all `local` reports in batches.
3. On 2xx: mark `synced`.
4. On 409 (conflict): mark `conflict`, let user resolve.
5. On network error: retry with exponential backoff (1s, 2s, 4s, ..., max 5min).

## Limitations

- No Service Worker / PWA frontend in this build (Streamlit limitation).
- Conflict resolution is client-driven; server treats duplicates as idempotent.
- No partial-sync for large batches (max ~100 reports per POST recommended).