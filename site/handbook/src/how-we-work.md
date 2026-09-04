# How we work

## Spec-first, cleanroom

A component starts from a specification, not from another implementation. Where a public standard exists, the suite implements it and runs its conformance suite. Where the standard is closed or paywalled, the `specs` repository keeps a living specification and an executable conformance suite, and the implementation targets that. Provenance is recorded per repository in `PROVENANCE.md`: what was consulted, and what was deliberately not.

## Rings and layers

Every repository sits in one dependency ring, and dependencies may only point inward:

| Ring | Contains | May depend on |
|---|---|---|
| spine | the catalog, the interfaces, the suite lockfile, RFCs, docs, the `pub` CLI, templates | nothing outside itself |
| platform | the crates every repository uses: config, logging, i18n, the UI toolkit, the document model, the plugin runtime, identity, packaging, observability | spine |
| system | toolchain, silicon, kernel, base, infrastructure, media, platform shells | spine, platform |
| domain | the products: office, workspace, home, imaging, video, audio, 3D, CAD, engineering, science, business, finance, health, civic, games | spine, platform, system |
| standards | living specs and open data | spine |

Layers `L0` to `L18` are the ledger: the rungs of the stack from silicon to content. A repository declares the layers it serves; the organization records them as a custom property on the repository.

## Waves

A wave is when a repository's first crate becomes buildable. The wave is assigned per repository in the catalog, not per ring: it is the `wave` field of the repository's entry, and the organization mirrors it as the `wave` custom property and the `wave-N` topic. Wave 1 spans every ring, from the spine to the standards. Within a wave, work proceeds ring by ring in dependency order (spine, platform, system, domain, standards), because a repository can only build once everything it depends on builds. The public `Roadmap` project mirrors the catalog's waves, layers, readiness and rings as fields.

## The catalog

`catalog/catalog.toml` in the `catalog` repository is the source of truth for every repository's ring, layers, wave, purpose and planned contents; GitHub descriptions, topics, custom properties, the organization README, this site and the brand are generated from it. Its JSON Schema (2020-12) is served at `https://publicsoftware.dev/catalog.schema.json`, the schema's `$id`. Every change is a pull request that also adds a line to the repository's `CHANGELOG.md`, and `pub catalog validate` runs on the pull request and again in the merge queue. After a merge, `pub catalog sync` converges every repository on GitHub from the new catalog. The catalog is released as immutable tags: a repository added is a minor release, one renamed or removed a major one, wording a patch. Tooling pins a tag (the current one is `v1.0.0`), never `main`.

## Changes that cross a repository

Anything that changes an interface or touches more than one repository goes through an RFC in the `rfcs` repository. The process is [RFC-0000](https://github.com/public-software/rfcs/blob/main/text/0000-rfc-process.md), the first RFC: copy the template to `text/0000-<slug>.md`, open a pull request, and the pull request number becomes the RFC number. An RFC is a `draft` while its pull request is open; it enters its `final comment period` (10 calendar days, the label `rfc/final-comment-period`) when the maintainers of the affected repositories are ready to decide; it ends `accepted` (merged into `text/`, with a decision record at the top of the file and a line in the decision log), `rejected` (closed with the reason) or `postponed`. A later RFC can supersede an accepted one; the old file stays and says so. Every RFC carries an Agent summary, one paragraph a coding agent can act on, and a How this is verified section naming the check that proves it is implemented. Open questions that are not yet a design go to the repository's Discussions; review happens on the pull request. Interfaces are WIT packages and wire schemas in `interfaces`; binding crates are generated from them. A package is `public:<name>@<version>` under `wit/` of `interfaces`, every item marked with the release that added it; the tag `<name>-v<version>` publishes it as an OCI artifact at `ghcr.io/public-software/public/<name>:<version>`, and `wkg get public:<name>@<version>` finds it through `https://publicsoftware.dev/.well-known/wasm-pkg/registry.json`. The rules are [RFC-0002](https://github.com/public-software/rfcs/blob/main/text/0002-wit-package-versioning.md).

## Sign-off and licensing

Every commit carries a Developer Certificate of Origin sign-off (`git commit -s`); the organization enforces it. Code is licensed `Apache-2.0 OR MIT`; content and specifications are `CC-BY-4.0`.

## Branches, reviews, releases

- `main` takes changes by pull request, with one approving review, code-owner review, resolved threads, signed commits and a linear history. Platform-ring repositories require two reviews.
- Release branches are `release/**`; release tags are immutable.
- The `suite` repository pins every crate in one lockfile and builds the whole suite nightly. Release trains are named by year and number; the first is `2027.1`.

## The checks

The status checks `main` requires are `suite / <job>`: the check runs the job `suite` of every repository's `ci.yml` and `review.yml` produces by calling the reusable workflows of the `.github` repository (`pub-check`, `probe`, `test`, `deny`, `semver`, `mutants`, `vet`, `audit`, `typos`, `miri`, `policy`). A check that has nothing to do (no crate yet, no `unsafe`, not a pull request) is skipped and reports success, so an empty repository is green. Both callers trigger on `pull_request` and on `merge_group`, so the same names serve the pull request and the merge queue; a queue entry waiting for a check that never reports never merges, and a job whose name depends on the run (a matrix leg) can never be required. Nothing on GitHub ties the names in the rulesets to the jobs in the workflows, so the `suite` repository's `conformance` crate (`pub-suite-conformance`) proves the contract on every change to either side: it reads the callers, the reusable workflows and the rules GitHub applies to `main`, and fails when a required check is not a check run the callers produce. It runs in `suite` against the release its `ci.yml` pins and in `.github` against the workflows under review.

## Where the code lives

GitHub is a mirror. The canonical home of the organization will be its own forge, built in the `forge` repository; until then, every repository mirrors to it automatically once the mirror is stood up.
