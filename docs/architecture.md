# Integration contract

This document records the initial implementation contract. Check it against the running package before treating it as an API reference.

## Package boundaries

- Product name and plugin identifier: `Formwork` / `formwork`.
- `desktop/plugin.js` contributes the native Desktop workspace through `@hermes/plugin-sdk`.
- `dashboard/plugin_api.py` registers a FastAPI router in Hermes's plugin API namespace.
- `formwork/store.py` owns packet persistence and coordinates the PDF engine through `PacketStore(root: Path)`.
- The PDF engine imports existing AcroForms, extracts supporting text, renders pages with PDFium, and fills exported copies.

The frontend calls `ctx.rest` with namespace-relative paths. It should not derive credentials, assume a localhost port, or access Hermes's internal DOM.

The store's direct methods are `packet()`, `new_packet()`, `upload(files)`, `update_values(updates)`, `export(include_sources=False)`, and `render(form_id=None, source_id=None, page=1)`. Model assistance uses `extraction_input()` and `apply_proposals(proposals, expected_revision=None)`. Invalid requests raise `PacketError`, a `ValueError` subclass.

## Initial routes

All paths below are relative to `/api/plugins/formwork`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/packet` | Read the current packet's public state |
| POST | `/new` | Require `{"archiveCurrent": true}`; archive metadata and start a fresh packet without erasing original files or exports |
| POST | `/upload` | Add `{"files": [{"name": "...", "data": "<base64>"}]}` |
| POST | `/extract` | Returns a clear instruction to use the host-bound extraction RPC |
| GET | `/jobs/<id>` | Read extraction progress or a terminal failure |
| POST | `/values` | Apply `{"updates": [{"formId": "...", "fieldId": "...", "value": "..."}]}` |
| POST | `/export` | Accept optional `{"includeSources": true}`; return completed copies and a ZIP as `{"exports": [{"name": "...", "path": "...", "size": 0}]}` |
| GET | `/render` | Render one form or source page; query `formId` or `sourceId`, plus `page` |

A value update can additionally carry `sourceId`, `page`, `quote`, and `origin` (`user` or `model`). These fields are untrusted input and must be checked against the packet before they are persisted as evidence.

The `/values` route accepts only explicit user review (`origin: "user"`). Model proposals enter through `apply_proposals`, which validates their evidence and preserves user-origin fields. Selecting one conflict candidate can supply its source citation; changing a value without a new valid citation clears the old evidence.

## Extraction RPC

The native workspace starts extraction with `host.request('plugin.formwork.extract', {})`. The plugin's `register(ctx)` registers that method, captures the request context, starts a worker thread, and immediately returns `{"jobId": "...", "status": "running"}`. The workspace polls the ordinary REST job route. The worker calls the host-supplied `ctx.llm.complete_structured`; it never constructs its own model facade or chooses credentials.

Preparing model input, rendering form pages, and the model call all happen in the worker. A profile switch does not redirect that job to another profile's packet. An error produces a terminal `failed` job; no guessed answer replaces the missing model result.

Render responses have the shape `{"dataUrl": "data:image/png;base64,...", "width": 0, "height": 0}`. Public page numbers start at **1**. Public page coordinates use a **top-left** origin. The engine must normalize PDF bottom-left coordinates and page rotation before the frontend draws field overlays.

## Downloads

Use the SDK's `captureGatewayFileDownload()` immediately before the export/list REST request, retain the returned save action beside those results, and invoke it on an explicit Save click with the backend-provided persisted path. This binds the eventual download to the gateway/profile that produced the file even if the user switches connections.

Do not open a remote path using `file://` or reconstruct a download path from the visible filename.

## Ownership and race conditions

Model suggestions, user answers, and imported source documents have different roles. A model result completing after a user correction must not silently replace that correction. A failed extraction should leave the packet available for manual completion.

Upload display names must not control storage paths. Export must create new files and preserve the uploaded originals. State and rendered-page cache keys must include the correct document identifier and revision.

Starting a new packet changes its identifier and increases the revision monotonically. An old extraction cannot pass its revision check against a fresh packet. Archived metadata, originals, previews, and previous exports remain on disk; there is no automatic archive retention or restore UI in this version.

## Official SDK references

- [Desktop Plugin SDK](https://hermes-agent.nousresearch.com/docs/developer-guide/desktop-plugin-sdk)
- [Build a Hermes plugin](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins)
- [Catalog submission](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission)

The native Desktop SDK, web-dashboard SDK, and Python plugin layer are separate interfaces. The plugin API namespace is shared; their frontend APIs are not interchangeable.
