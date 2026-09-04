# Glossary

- **Catalog.** The machine-readable ledger of every repository: purpose, ring, layers, wave, contents. It lives in the `catalog` repository and is the source of truth for GitHub descriptions, topics, custom properties, the organization README and this handbook.
- **Ring.** A repository's dependency tier: `spine`, `platform`, `system`, `domain` or `standards`. Dependencies point inward only. Each ring has a colour in the identity.
- **Layer.** A rung of the stack, `L0` (silicon) to `L18` (content). A repository serves one or more layers; `all` means the whole ledger.
- **Wave.** The roadmap phase in which a repository's first crate becomes buildable; the catalog assigns waves {{WAVE_RANGE}}.
- **Readiness.** How far a repository's flagship component has come: `shipped`, `partial`, `seed` or `none`.
- **Tier.** The review tier of a repository: `incubating`, `stable`, `core` or `archived`.
- **Release train.** A coordinated release of the whole suite, named by year and number, for example `2027.1`. The `suite` repository's lockfile pins it.
- **Spec-first cleanroom.** Implementing from a specification and its conformance suite rather than from another implementation, with provenance recorded.
- **RFC.** A design proposal that crosses repositories or changes an interface; lives in the `rfcs` repository with a decision log.
- **DCO.** Developer Certificate of Origin; the `Signed-off-by` line every commit carries.
- **WIT.** The WebAssembly Interface Types language, used in `interfaces` to define every cross-repository API as `public:<area>/<interface>@x.y.z` packages.
- **`pub`.** The organization's command-line tool: scaffolds repositories, checks conventions, syncs the catalog to GitHub, pulls and builds the suite.
