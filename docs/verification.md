# Verification plan

This is the release checklist. Completed checks are recorded at the end; unchecked items remain requirements rather than claims.

## Packet behavior

- Import multiple forms and sources in one request. Preserve each original file byte for byte.
- Persist a packet, construct a new store instance, and verify that files, proposed answers, user corrections, and provenance survive.
- Give every form and source its own identifier. Duplicate filenames must not overwrite another document.
- Treat uploaded names as display labels. Reject traversal, oversized payloads, invalid base64, and unsupported content without leaving a partially usable packet.
- Keep field updates confined to the requested packet, form, and field. Unknown identifiers must not create arbitrary fields or access paths outside packet storage.
- Keep user corrections when a later extraction completes. An outdated result must not silently overwrite newer review work.
- Expose asynchronous extraction status, including a useful failure result. A failed model request must leave manual review and export usable.

## AcroForm correctness

Inspect both the canonical `/AcroForm/Fields` tree and page `/Widget` annotations. Values can look correct in one representation while being stale or missing in the other.

1. Import text, multiline, checkbox, and supported choice-field examples. Treat unsupported radio, signature, XFA, malformed, or ambiguous fields explicitly.
2. Fill all pages using fully qualified field names. Preserve unrelated existing values.
3. Export to a new PDF and reopen it with an independent reader.
4. Confirm expected fields and exact `/V` values, including non-ASCII text where supported.
5. Check the effective values of every affected widget, including parent inheritance and repeated widgets.
6. Confirm updated widgets have nonempty normal appearance streams.
7. Render the exported pages with PDFium and inspect visible values, page rotation, clipping, line wrapping, checkbox state, and alignment. Reading `/V` alone is insufficient.
8. Open the exported PDF in an external viewer during the final integration check.

Never repair ambiguous duplicate field trees blindly. Never flatten a signed form. Preserve editable fields by default unless a static export is an explicit supported option.

## Evidence and unanswered questions

- A model proposal must name an imported source, an existing page, and a quote actually present in that page's extracted text, allowing only documented whitespace normalization.
- Reject invented citations and invalid pages. Keep an unsupported answer visibly unsourced rather than attaching a plausible-looking source.
- Distinguish absence of evidence from a negative answer.
- Show conflicting evidence for review instead of selecting one fact silently.
- Ask for a repeated missing fact once only if the implementation actually groups equivalent fields; otherwise do not advertise this behavior.
- Numeric totals should be calculated deterministically from reviewed amounts. Check currency, decimal separators, negative amounts, duplicates, and rounding if receipt aggregation ships.

## Native integration

- Install into a clean Hermes profile and run `hermes plugins validate` on the exact commit to be submitted.
- Confirm the Desktop contribution loads through `@hermes/plugin-sdk` and appears under the expected plugin entry.
- Exercise upload, extraction, value edits, original/source rendering, export, and native Save through the installed plugin, not only a standalone development server.
- Test gateway/profile switching while requests are active. A download must retain the connection and profile that produced it.
- Reopen the workspace after a restart. Disable the plugin and confirm contributed UI and event listeners dispose cleanly.
- Verify narrow-window layout and keyboard access to the primary actions.

## Demo acceptance

Use fictional data and original fixtures. Show a genuine two-form packet, a source-backed answer, a missing fact answered once if implemented, and completed original PDFs opening outside the plugin. Keep the posted video under 90 seconds. State any time compression or replay plainly.

## Release record

- November 10: `.venv/Scripts/python.exe -m pytest tests/test_packet.py -q` passed **23 tests**. These use original synthetic PDFs and controlled test model facades. They cover source-backed proposals, evidence refusal, conflicts, explicit review, stale extraction, packet persistence, atomic uploads and edits, editable PDF export, original-file hashes, preview changes, opt-in source ZIP attachments, asynchronous job context/error handling, and starting a new packet while preserving old originals, exports, and metadata.
- November 10: an isolated `python -I` process loaded `dashboard/plugin_api.py` by its absolute path with `runpy.run_path`, discovering all seven routes without relying on the working directory or installing Formwork itself. This checks backend import behavior, not Hermes's authenticated route mounting.
- November 10: the combined local engine and packet suite passed 42 tests before the subsequent opt-in attachment test was added. The final release must record a fresh combined result after all changes.

Pending: actual Hermes validation on the release commit, installed Desktop smoke test, a live configured-model extraction, exported-page visual inspection, clean-install validation, and final platform/version claims. No test model response should appear as a live model call in a demo.
