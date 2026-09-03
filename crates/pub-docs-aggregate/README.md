# pub-docs-aggregate

The `docs-aggregate` command of [docs](https://github.com/public-software/docs), part of Public Software. Kind: `app`; the binary is `docs-aggregate`.

Folds every repository's `docs/` into the one handbook site. Given the catalog, a directory of checkouts (one per
repository, named as in the catalog) and the handbook's mdBook root, it writes a site tree: the handbook copied
whole, then a `# Repositories` part in `SUMMARY.md` (in ring order, spine first) with one chapter per catalog
repository: a generated index page (purpose, ring, wave, layers, the GitHub link), the repository's own book when
`docs/src/SUMMARY.md` or `docs/book.toml` names one, and its architecture decision records from `docs/adr/`
(the `0000-template.md` excluded). A repository that is not checked out still gets its index page. After writing
the tree it checks every relative link and image in every Markdown page and exits 1 naming each one whose target
is not in the tree, `page:line: dangling link to <destination>`. It does not run mdBook; `mdbook build <out>`
renders the tree.

```sh
cargo run -p pub-docs-aggregate -- --catalog ../catalog/catalog/catalog.toml --repos .. --handbook site/handbook --out target/site
cargo run -p pub-docs-aggregate -- --version
cargo nextest run -p pub-docs-aggregate      # unit tests and tests/cli.rs, which runs the built binary on tests/fixtures
```

Its entry in the repository's `CATALOG.toml`:

```toml
[[component]]
crate     = "pub-docs-aggregate"
kind      = "app"
ledger    = "mdBook site"
readiness = "seed"
effort    = 2
specs     = []
provides  = []
requires  = []
```
