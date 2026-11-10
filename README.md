# Formwork

Complete a packet of PDF forms from the documents you already have, with the evidence beside every proposed answer.

Formwork is a Hermes Agent plugin with a dedicated Desktop workspace. It keeps the original pages visible while you review answers, resolve missing information, and export completed copies of the original forms.

> Development preview. Local PDF and packet checks are running. Installation into Hermes, the native workspace, and a live configured model still need end-to-end verification.

## The workflow

1. Add fillable PDF forms and supporting documents to one packet.
2. Ask Hermes to propose answers from the supporting documents.
3. Review each answer on the original form page. Open its supporting source and correct anything that needs changing.
4. Supply facts the documents do not contain, then export completed copies.

The important part is the review: the form, proposed value, and supporting document stay together. Formwork does not replace the original PDF with a newly designed document.

## First-release scope

- Existing AcroForm text fields, checkboxes, and supported single-select combo boxes, with unsupported documents identified during import.
- Source-backed text suggestions that remain editable before export. Proposals require an exact source-page quote containing the suggested value.
- Original-page previews and source-page navigation.
- Local packet state that can be reopened.
- Completed PDFs exported as new files, preserving the uploaded originals.
- Explicit review of model proposals before export, including conflicts. A manual correction clears its stale source citation.
- A ZIP containing completed forms and a review manifest, with an explicit option to include supporting source PDFs.

Arbitrary scanned forms, XFA forms, radio groups, encrypted PDFs, signed PDFs, and forms with calculations or interactive actions are outside the initial scope. Formwork does not sign documents; an empty signature field stays blank and requires separate completion. Text export is conservatively limited to printable ASCII so that the saved appearance can be checked. Checkbox decisions are entered by the user; the model does not infer consent. No receipt arithmetic is performed. A PDF can have visible boxes without having fillable fields; such a document is not automatically a supported form.

Packets are limited to ten PDFs, 12 MB per file, and 35 MB total. Model extraction accepts at most twelve form pages and 200,000 characters of extracted packet text; oversized inputs are refused rather than silently truncated.

## Requirements

- Hermes Agent and Hermes Desktop. The target integration is Hermes 0.23.1 or newer; end-to-end compatibility is still being checked.
- Python dependencies declared by the plugin, including `pypdf` for AcroForms and `pypdfium2` for page rendering.
- A model configured in Hermes for answer proposals. Importing, reviewing, and exporting are separate from model-assisted extraction.

Installation commands and the release repository will be added once the package passes a clean installation check.

## Data and model use

Formwork stores packet files and SQLite review state under the active Hermes host's `plugin-data/formwork` directory. Requesting model-assisted extraction sends document text, field descriptions, and rendered form pages to the model configured in Hermes. Normal model charges apply. The plugin does not select a different provider or obtain model credentials itself.

Imported originals, generated previews, exports, and job records remain in that directory. **New packet** archives the previous packet's metadata and starts an empty packet; it preserves the previous originals and exports. Archives currently have no restore interface. Automatic retention cleanup is not provided, and removing the plugin does not erase its data.

Review proposed answers before exporting. A source citation shows where a proposal came from; it does not establish that the source is current or that an interpretation is correct.

## Development

- [Verification plan](docs/verification.md)
- [Submission checklist](docs/submission.md)
- [External PDF test sources](docs/test-sources.md)

No test result, platform support claim, or catalog acceptance is implied by this development preview.
