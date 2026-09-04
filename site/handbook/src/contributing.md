# Contributing

| Fact | Value |
|---|---|
| Toolchain | Rust `1.90` or newer, edition `2024`; `cargo install pub` |
| Find work | [open good first issues](https://github.com/search?q=org%3Apublic-software+label%3A%22good+first+issue%22+state%3Aopen&type=issues); [open RFCs](https://github.com/public-software/rfcs/pulls) |
| Sign-off | `git commit -s` on every commit; `main` requires signed commits |
| Checks | `pub check` locally; the repository's CI (`suite / <job>`) on the pull request and in the merge queue |
| Reviews | one approving review from a code owner; two in the platform ring |
| Review gate | an agent applies the [rubric](https://github.com/public-software/.github/blob/main/review/RUBRIC.md) before a human reviews; a hard finding fails `suite / policy` |
| Writing | Simplified Technical English (ASD-STE100); the rules are in [WRITING.md](https://github.com/public-software/.github/blob/main/WRITING.md) |
| Provenance | say in the pull request what you consulted; `PROVENANCE.md` says what may be consulted |
| Conduct | the [code of conduct](https://github.com/public-software/.github/blob/main/CODE_OF_CONDUCT.md) applies everywhere |
| Security | `hello@publicsoftware.dev`, or private vulnerability reporting on the repository; the [security policy](https://github.com/public-software/.github/blob/main/SECURITY.md) |

1. Open an issue, or pick one. If the change touches an interface or more than one repository, open an RFC first ([how](https://github.com/public-software/rfcs/blob/main/CONTRIBUTING.md)).
2. Branch from `main`. Keep the change to one concern.
3. Sign every commit off: `git commit -s`. Sign it too; `main` requires signed commits.
4. `pub check` must pass. So must the repository's CI.
5. Open a pull request. One approving review from a code owner merges it; platform-ring repositories need two.

## In depth

### Find something to do

Every repository labels beginner-friendly work `good first issue`. The organization-wide search is the fastest way in: [open good first issues across the organization](https://github.com/search?q=org%3Apublic-software+label%3A%22good+first+issue%22+state%3Aopen&type=issues).

Design questions that cross repositories are RFCs: [open RFCs](https://github.com/public-software/rfcs/pulls).

### Set up

```sh
cargo install pub
pub suite pull        # every repository, at the pinned revisions
pub check             # the conventions every repository must pass
```

Rust `1.90` or newer, edition `2024`.

### Write

Write every public document in Simplified Technical English (ASD-STE100). This applies to every repository: README files, this handbook, the site, crate documentation, RFC text and release notes. The rules, the names of the suite and where to get the specification are in [WRITING.md](https://github.com/public-software/.github/blob/main/WRITING.md). Short sentences, one topic each, active voice, one word for one thing.

### Provenance

If you consulted an existing implementation while working, say so in the pull request. `PROVENANCE.md` in each repository records what may and may not be consulted for that component; the `kind/provenance` label is for questions about it.

### The review gate

Every pull request is read by an agent before a human reviews it. The agent applies the seven rules below and reports a finding for each rule the change breaks. A **hard** finding fails the required check `suite / policy`, so the pull request cannot merge until it is fixed; a **soft** finding is advice in the review comment. `trailer` and `provenance` are also checked deterministically, so they block even on a fork's pull request, where the agent does not run (it cannot see the organization secret; a maintainer pushes the branch into the repository for the agent pass). The merge queue reuses the verdict recorded on the pull request.

| Rule | Severity | The reviewer asks | Self-check before opening the pull request |
|---|---|---|---|
| `scope` | soft, hard when the change does something the issue or RFC never asked for | Does the change do one thing, the thing its issue or RFC describes? An interface change or a change across repositories needs an RFC. | Link the issue. Split unrelated changes. |
| `tests` | hard when a behaviour change ships without a test that fails without it | Is there a test that fails on `main` and passes with the change? Documentation-only and mechanical changes are exempt. | Run the new test against `main` once. |
| `provenance` | hard | Was anything copyleft (GPL, AGPL, LGPL, SSPL, EUPL) consulted, cited or ported? Is every reference that was consulted listed in `PROVENANCE.md`? | Only specifications, conformance suites and permissive references; list them. |
| `trailer` | hard | Does every commit carry a `Signed-off-by:` trailer (Developer Certificate of Origin)? | `git commit -s`; `git rebase --signoff` fixes a branch. |
| `secrets` | hard | Does the diff add a credential, token, private key or a personal address that is not the author's sign-off? | Search the diff for `key`, `token`, `secret`, `BEGIN` before pushing. |
| `semver` | soft, hard when a public interface changes and the description says nothing about it | Does the description state the semver impact of a public API change (breaking, feature, fix)? | One line in the description: "semver: minor (new function ...)". |
| `agents` | soft | Does the change follow the repository's `AGENTS.md` (conventions, forbidden paths, required checks) when there is one? | Read `AGENTS.md`; run `pub check`. |

### What CI proves

The same checks run on every pull request and again in the merge queue; a check that has nothing to do (no crate yet, no `unsafe`, not a pull request) reports success, so a new repository is green from its first commit.

| Check | What it proves | When it fails, do this |
|---|---|---|
| `test` | The workspace builds, tests pass on Linux, macOS and Windows, docs build without warnings. | Fix the test or the doc comment. |
| `mutants` | The tests notice when the code the pull request changed is broken: `cargo mutants --in-diff` mutates only the changed lines and expects a test to fail for each mutant. Advisory until 2026-10-03, then required. | Write the test that catches the surviving mutant listed in the job log. |
| `vet` | Every third-party crate the workspace builds has an audit: the repository's own, or one imported from the Mozilla and Google audit sets. `cargo vet --locked` runs against the committed `supply-chain/`. | Run `cargo vet` locally; it pulls matching audits into `imports.lock`. Audit what is left (`cargo vet suggest`, `cargo vet certify`) and commit `supply-chain/`. |
| `audit` | No dependency has a RustSec advisory or is yanked (`cargo audit`). | Bump the dependency; if no fixed release exists, say so in the pull request and add the advisory to `deny.toml`. |
| `deny` | Licences are on the allow-list, sources are crates.io only (`cargo deny`). | Replace the dependency; MPL-2.0 is the only copyleft allowed, and only in domain-ring applications. |
| `semver` | A public API change is versioned as it should be (`cargo semver-checks`; advisory until the first release). | Bump the version, or state the break in the description. |
| `typos` | No misspelling in code or prose (`typos`). | Fix it, or list the word in `_typos.toml` when it is a name. |
| `miri` | `unsafe` code has no undefined behaviour under Miri; runs only when a crate says `unsafe`. | Fix the unsafe code. Miri is slow: keep unsafe crates small. |
| `policy` | The review gate above. | See the review comment. |

Disagree with a finding in the review thread. A maintainer can merge over a hard finding that is wrong, and the rubric itself lives in the [`.github` repository](https://github.com/public-software/.github/blob/main/review/RUBRIC.md), where it is corrected like any other file. CodeRabbit comments on every pull request as a free second opinion; it is advisory and never blocks.

### Conduct and security

The [code of conduct](https://github.com/public-software/.github/blob/main/CODE_OF_CONDUCT.md) applies everywhere in the organization. Security reports go to `hello@publicsoftware.dev` or through private vulnerability reporting on the repository; see the [security policy](https://github.com/public-software/.github/blob/main/SECURITY.md).
