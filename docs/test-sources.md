# External PDF test sources

Formwork's distributable demo uses original fixtures with fictional content. The files below are small, public upstream regression examples used for local compatibility checks; no third-party PDF binary has been committed here.

## Three AcroForm text examples

All three are maintained in Mozilla's official [PDF.js repository](https://github.com/mozilla/pdf.js). Each has one page, an AcroForm text field named `Text2`, and no `/XFA` entry in the inspected version.

| File | Purpose | Upstream URL |
| --- | --- | --- |
| `annotation-tx.pdf` | Basic text widget with existing text | [Source](https://github.com/mozilla/pdf.js/blob/master/test/pdfs/annotation-tx.pdf) |
| `annotation-tx2.pdf` | Alternate text-widget appearance | [Source](https://github.com/mozilla/pdf.js/blob/master/test/pdfs/annotation-tx2.pdf) |
| `annotation-tx3.pdf` | Multiline value with carriage returns | [Source](https://github.com/mozilla/pdf.js/blob/master/test/pdfs/annotation-tx3.pdf) |

These are closely related regression fixtures, not evidence of broad compatibility with three independently authored real-world forms. A release check also needs unseen ordinary forms with meaningful labels and more than one field.

## Rejection examples

The upstream [choice-widget example](https://github.com/mozilla/pdf.js/blob/master/test/pdfs/annotation-choice-widget.pdf) and [button-widget example](https://github.com/mozilla/pdf.js/blob/master/test/pdfs/annotation-button-widget.pdf) contain `/XFA` as well as AcroForm fields. They are useful for verifying explicit XFA refusal; they should not be used as supported-AcroForm success examples.

## Additional compatibility probes

- The official [OPM SF-182 training form](https://www.opm.gov/forms/pdf_fill/sf182.pdf) was readable, with nine pages and 88 field-tree entries, including text, choices, buttons, and signatures. It did not contain XFA in the inspected download. The current engine preserves empty signature widgets, but this form is still refused because of unsupported pushbuttons and interactive formatting actions.
- The official [IRS W-9](https://www.irs.gov/pub/irs-pdf/fw9.pdf) contained both AcroForm fields and XFA in the inspected download. It is a rejection case, not a supported-form example.
- The [pdf-lib character-sheet example](https://pdf-lib.js.org/assets/dod_character.pdf) had one page and 14 text/button fields, without XFA. It was refused because of its image-upload pushbuttons and interactive actions. It is not an original Formwork fixture, and its file-specific redistribution terms have not been verified.

The three Mozilla text examples were also filled and their rendered results inspected locally. Do not commit or redistribute upstream PDFs on the basis of this compatibility note alone.

## Licensing and reproducibility

The repository publishes an [Apache License 2.0](https://github.com/mozilla/pdf.js/blob/master/LICENSE). Retain attribution and check for file-specific notices before redistributing any PDF. Linking to and locally inspecting upstream examples does not make them Formwork-authored fixtures.

The links above follow the upstream default branch and can change. Before adding a reproducible automated download check, pin the upstream commit and record SHA-256 values. Automated tests must run offline against original fixtures unless the caller explicitly opts into network compatibility checks.
