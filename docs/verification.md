# Verification record

This record separates completed checks from release work that remains open. A passing local test or isolated model call does not establish that the installed native workflow works from import through download.

## Completed checks

Results below were recorded on November 10, 2026.

| Check | Observed result | Scope |
| --- | --- | --- |
| Current project suite, Python 3.12 | **52 passed: 22 engine and 30 packet tests** | Real original PDF fixtures and controlled model facades. This is the latest combined local result. |
| Hermes runtime, Python 3.14 | **45 passed on an earlier suite snapshot** | The latest 52-test suite has not yet been rerun in this runtime. |
| Minimum PDF-library version | **22 engine tests passed with pypdf 6.19.0** | Tested in an isolated dependency directory without changing the project environment. The project engine suite also passed with pypdf 6.21.4 and PDFium 5.15.2. |
| Clean Hermes validation | **`hermes plugins validate --install-deps` passed** | Hermes v0.23.1; exact first commit `e4e624263d7f9bcb1367ba6ce04656bf89f822cc`. Changes after that commit require another validation before the release is pinned. |
| Backend import | **Passed** | An isolated `python -I` process loaded `dashboard/plugin_api.py` by absolute path and discovered its seven routes. This checks import behavior, not authenticated route mounting by itself. |

### PDF engine

The engine tests exercise actual PDFs rather than only mocked PDF operations. Coverage includes text and multiline fields, checkboxes, supported single-select combo boxes, fields on separate pages, nested canonical names, repeated widgets, page rotation, and choice export values that differ from their displayed labels.

Export checks reopen the saved PDF and compare canonical field values with effective widget values. They inspect and render the saved appearance streams, check visible text and clipping, and render the complete pages. They also compare original-file hashes, page content and geometry, untouched values and appearances, and field flags. Output remains editable. Failed verification does not publish the candidate PDF.

Negative controls cover unsupported characters, overflow, invalid values, source or output replacement, ambiguous orphan widgets, XFA, radio fields, encrypted PDFs and signed PDFs. Empty signature widgets are preserved as manual work and excluded from editable fields; an exported document with a remaining manual signature is not marked complete.

Three related text-widget regression PDFs from Mozilla's PDF.js repository were filled successfully and their rendered results were inspected. This is limited compatibility evidence, not three independent ordinary business forms. The pdf-lib character-sheet example was refused because of its image-upload pushbuttons and interactive actions. OPM SF-182 was also refused: its empty signature widgets are now preserved, but its pushbuttons and interactive formatting actions remain outside the accepted scope. See [external test sources](test-sources.md).

Text export currently accepts printable ASCII. These results do not establish arbitrary PDF, font, scan or language compatibility.

### Packet behavior

The 30 packet tests cover original-file preservation, persistent packet state, distinct storage identifiers for duplicate filenames, atomic imports and edits, invalid uploads and identifiers, source-linked proposals, invalid citation refusal, conflicting evidence, explicit review, stale extraction results, and preservation of user corrections.

They also cover editable export, previews reflecting saved values, the review manifest, optional inclusion of exact source files in the ZIP, asynchronous job context and error handling, retry after extraction setup failure, bounded retries around brief Windows publication locks, and starting a new packet while preserving earlier originals, exports and metadata.

Model facades in these tests are controlled test implementations. Their responses must not appear in a demo as if a real provider generated them.

## Native Hermes observations

The current Formwork workspace has loaded in Hermes Desktop. The following actions have been observed through the installed native contribution:

- Opening the folder picker.
- Importing the four original synthetic forms and four source PDFs.
- Viewing original-form previews.
- Persisting and reopening the packet.
- Completing a genuine asynchronous model extraction and displaying its 20 proposals in the native workspace.
- Approving all 20 sourced proposals through the review dialog.
- Entering `Vegetarian` for the workshop dietary field, then explicitly selecting and updating the matching venue field.
- Saving photograph consent as an explicit unchecked user decision, bringing the packet to 23 reviewed fields.
- Exporting four filled PDFs and a ZIP with supporting source attachments disabled.
- Saving the actual ZIP through native Save to `output/native-demo/completed-packet.zip`.

The complete native demonstration workflow has now been exercised from import through the saved ZIP. The actual downloaded speaker form was subsequently opened in Chrome's PDF viewer and its visible values and editable fields were checked. The remaining final release checks are listed below.

## Configured-model extraction and proposal audit

An earlier genuine isolated `PluginContext` call used the current extraction input and profile and returned 20 proposals. That isolated result was not applied to the packet and was not counted as native integration success.

The native asynchronous RPC path subsequently succeeded for job `4d27117440ca4fba8d9fe7bca07e36ba`, using provider `nous` and model `openai/gpt-6.1-sol`. It persisted **20 proposals** at packet revision **3**, and those proposals were visible in the native UI. Earlier native attempts had returned provider HTTP 400; they remain failed attempts rather than successful demo runs.

A separate read-only audit called `PacketStore.packet()` through the backend API module. All 20 proposed values matched the fictional source facts used by `examples/make_demo.py`. Every cited quote occurred literally on its recorded source page and contained the proposed value. The eight imported document hashes matched the original demonstration PDFs. No semantic error was found in this one synthetic packet.

At that pre-review checkpoint, the proposals consisted of six speaker-profile answers, six supplier-onboarding answers, four venue-access answers and four workshop-registration answers. The two dietary-requirement fields remained empty. Photograph consent remained an untouched checkbox with `origin: ""` and `status: "empty"`, not a reviewed negative answer. The packet's public JSON digest was unchanged before and after the audit.

This establishes genuine native extraction and a checked demonstration result for this packet, not accuracy on other documents.

## Actual downloaded export audit

After native review, the persisted packet was at revision **8**, with all **23 fields** marked as reviewed user values. A separate audit checked the actual native download, not replacement PDFs produced by a test script. It did not modify packet state.

The downloaded ZIP's SHA-256 was `b4e9c2714c2c77b323f0c036fb64059b114a07b7fd36909d3610d6bf88c3d93e`, identical to the ZIP published by the packet store. Its five members were four completed PDFs and `review.json`; no supporting source PDFs were included. Member paths, duplicate destinations, link attributes and size limits were checked before extraction beneath `output/native-demo/unpacked`.

Each downloaded PDF matched its published and manifest SHA-256. Reopening the files confirmed retained AcroForm fields, all 23 expected canonical values, agreeing effective widget values, and nonempty saved normal appearance streams. The photograph-consent field had `/V` and `/AS` set to `/Off`. All four documents remained editable, and their original page-content streams were preserved. The review manifest matched the persisted reviewed fields and recorded source inclusion as false.

The eight stored original documents still matched both their imported hashes and the original demonstration PDFs. The packet's public JSON digest was unchanged before and after the audit.

All four actual downloaded output pages were rendered to PNGs under `output/native-demo/renders` and visually inspected. The expected values were visible and aligned, the biography wrapped across two lines, both dietary fields showed `Vegetarian`, and photograph consent was visibly unchecked. No clipping or missing text was observed. The local audit details are in `output/native-demo/download-audit.json`.

The actual downloaded speaker form was also opened in Chrome's PDF viewer. Its filled values and editable fields were checked there; this is separate from the PDFium rendering audit above. This external-viewer observation covers that downloaded form, not every possible PDF viewer or document.

## Remaining release checks

- Validate the final release commit with dependencies from a clean Hermes profile, then pin that exact commit in the catalog entry.
- Finish checking native extraction progress, failure recovery and preservation of existing review work around retries and later edits.
- Check profile/connection handling, plugin disable/disposal, narrow-window layout and primary keyboard actions.
- Record and inspect the actual-screen demonstration using fictional documents. Show genuine model results and make any cut around waiting or repetitive review apparent.
- Publish the demo post, open the catalog PR and submit both links through the entry form. These publication and submission steps remain pending.

The current 52-test suite also passed in the Hermes Python 3.14 runtime. Receipt arithmetic, signing, service submission and universal PDF compatibility are outside this release. A source quote establishes provenance for a proposed value; it does not establish that the source is current or that the interpretation is correct.
