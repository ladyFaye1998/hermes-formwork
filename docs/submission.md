# Hackathon submission checklist

The plugin must be complete and reviewable before publishing its entry. This checklist records the official requirements and the remaining account dependencies; it does not mean the entry has been submitted.

## Required entry materials

- A public plugin repository with the finished code and a clear README.
- A catalog pull request against `NousResearch/hermes-agent`, following the [catalog submission guide](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/catalog-submission).
- A demo video posted on X, tagging `@NousResearch`, showing the plugin working in under 90 seconds.
- Both links submitted through the [official Typeform](https://form.typeform.com/to/FwJLvOln).

The catalog PR may be open when the form is submitted; it need not already be merged. The entry is the plugin itself, judged on usefulness, reliability, polish, and creativity. The announcement favors functionality that exceeds a prompt or a skill. No numerical weights are published in the announcement.

Source: [official announcement](https://x.com/NousResearch/status/2118094256438936062).

## Deadline

The announcement states **November 11, 2026, 5 PM EST** (22:00 UTC; midnight entering November 12 in Israel). The Typeform thank-you text contains an earlier 1 PM PST time. Use the agreed safe submission target of **November 11, 23:00 Israel time** (21:00 UTC), before both times.

Do not treat the form's technical closing time as an extension of eligibility.

## Typeform fields

The public form definition checked on November 10 requires:

1. Plugin Title
2. Plugin Description
3. Email Address
4. Discord Username
5. X Demo Post Link
6. GitHub Link to the Hermes Plugin Pull Request

There is no code upload in the form. Provide the catalog PR URL, rather than only the plugin repository URL.

## Packaging checks before publication

- Pin the catalog entry to a full 40-character commit SHA containing the verified release.
- Run the catalog validator on that exact checkout.
- Keep imports, dependencies, capabilities, permissions, model access, and disclosures consistent with the implementation.
- Use public Hermes extension APIs. Do not patch core code or Desktop markup at runtime.
- State actual supported PDF types, platforms, and tested Hermes version.
- Exclude credentials, real personal documents, local packet state, and temporary exports from the repository and demo.
- Open the exported demonstration PDFs and verify their stored values and rendering.

## Account dependencies checked

- The GitHub connector can access repositories for `ladyFaye1998` and exposes branch, tree, commit, file, and PR operations. It does not expose repository creation.
- The connected Metricool brand has Instagram, with no connected X account. It cannot publish the required X demo in this state. A signed-in X browser session is a possible alternative.
- The required Discord username still needs to be obtained from an authorized existing account surface or supplied by the entrant.

Account discovery was read-only. No repository, PR, X post, or Typeform submission has been created by these checks.
