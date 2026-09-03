# Provenance

This repository is a spec-first cleanroom implementation. Record here what was consulted.

## Specifications used
- CommonMark 0.31.2 (https://spec.commonmark.org/), as the dialect the link check reads Markdown in, through the
  `pulldown-cmark` crate (MIT).
- TOML 1.1.0 (https://toml.io/en/v1.1.0), the catalog's format, through the `toml` crate (Apache-2.0 OR MIT).

## Behavioural references (cited, not copied)
- mdBook documentation (https://rust-lang.github.io/mdBook/, the tool is MPL-2.0; its source was not consulted):
  the `SUMMARY.md` grammar (`format/summary.html`: prefix, numbered, draft and suffix chapters, part titles,
  separators) and the `[book]` and `[build]` configuration keys (`format/configuration/general.html`), for what
  `pub-docs-aggregate` reads from a repository's book and writes into the handbook's `SUMMARY.md`.
- `pulldown-cmark` 0.13 API documentation (https://docs.rs/pulldown-cmark, MIT): the link and image tag fields
  and the offset iterator the link check uses.

## Copyleft sources
None consulted. Contributors who have studied GPL/AGPL implementations of this domain do not author the corresponding modules (two-team rule; see the Charter §09).

## AI assistance
Prompts point at the specifications and conformance suites above, never at copyleft source. Generated code is reviewed against this list before merge.
