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

A wave is when a repository's first crate becomes buildable. Wave 1 is the spine and the platform; later waves follow the dependency rings outward. The public `Roadmap` project mirrors the catalog's waves, layers, readiness and rings as fields.

## Changes that cross a repository

Anything that changes an interface or touches more than one repository goes through an RFC in the `rfcs` repository: a template, a comment window, a decision log. Interfaces are WIT packages and wire schemas in `interfaces`; binding crates are generated from them.

## Sign-off and licensing

Every commit carries a Developer Certificate of Origin sign-off (`git commit -s`); the organization enforces it. Code is licensed `Apache-2.0 OR MIT`; content and specifications are `CC-BY-4.0`.

## Branches, reviews, releases

- `main` takes changes by pull request, with one approving review, code-owner review, resolved threads, signed commits and a linear history. Platform-ring repositories require two reviews.
- Release branches are `release/**`; release tags are immutable.
- The `suite` repository pins every crate in one lockfile and builds the whole suite nightly. Release trains are named by year and number; the first is `2027.1`.

## Where the code lives

GitHub is a mirror. The canonical home of the organization will be its own forge, built in the `forge` repository; until then, every repository mirrors to it automatically once the mirror is stood up.
