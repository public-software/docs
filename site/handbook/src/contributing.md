# Contributing

## Find something to do

Every repository labels beginner-friendly work `good first issue`. The organization-wide search is the fastest way in: [open good first issues across the organization](https://github.com/search?q=org%3Apublic-software+label%3A%22good+first+issue%22+state%3Aopen&type=issues).

Design questions that cross repositories are RFCs: [open RFCs](https://github.com/public-software/rfcs/pulls).

## Set up

```sh
cargo install pub
pub suite pull        # every repository, at the pinned revisions
pub check             # the conventions every repository must pass
```

Rust `1.90` or newer, edition `2024`.

## Make the change

1. Open an issue, or pick one. If the change touches an interface or more than one repository, open an RFC first.
2. Branch from `main`. Keep the change to one concern.
3. Sign every commit off: `git commit -s`. Sign it too; `main` requires signed commits.
4. `pub check` must pass. So must the repository's CI.
5. Open a pull request. One approving review from a code owner merges it; platform-ring repositories need two.

## Provenance

If you consulted an existing implementation while working, say so in the pull request. `PROVENANCE.md` in each repository records what may and may not be consulted for that component; the `kind/provenance` label is for questions about it.

## Conduct and security

The [code of conduct](https://github.com/public-software/.github/blob/main/CODE_OF_CONDUCT.md) applies everywhere in the organization. Security reports go to `hello@publicsoftware.dev` or through private vulnerability reporting on the repository; see the [security policy](https://github.com/public-software/.github/blob/main/SECURITY.md).
