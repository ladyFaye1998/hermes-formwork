# External PDF test sources

Formwork's distributable demo should use original fixtures with fictional content. The files below are small, public upstream regression examples for additional compatibility checks. They have been downloaded into memory and inspected with `pypdf`; no third-party PDF binary has been committed here.

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

- The official [OPM SF-182 training form](https://www.opm.gov/forms/pdf_fill/sf182.pdf) was readable, with nine pages and 88 field-tree entries, including text, choices, buttons, and signatures. It did not contain XFA in the inspected download. The signature fields put it outside Formwork's initial accepted scope.
- The official [IRS W-9](https://www.irs.gov/pub/irs-pdf/fw9.pdf) contained both AcroForm fields and XFA in the inspected download. It is a rejection case, not a supported-form example.
- The [pdf-lib character-sheet example](https://pdf-lib.js.org/assets/dod_character.pdf) had one page and 14 text/button fields, without XFA. This is an additional independent compatibility candidate, not an original Formwork fixture. Its file-specific redistribution terms have not been verified.

These downloads were inspected in memory only. Do not commit or redistribute them on the basis of this compatibility note.

## Licensing and reproducibility

The repository publishes an [Apache License 2.0](https://github.com/mozilla/pdf.js/blob/master/LICENSE). Retain attribution and check for file-specific notices before redistributing any PDF. Linking to and locally inspecting upstream examples does not make them Formwork-authored fixtures.

The links above follow the upstream default branch and can change. Before adding a reproducible automated download check, pin the upstream commit and record SHA-256 values. Automated tests must run offline against original fixtures unless the caller explicitly opts into network compatibility checks.
