# Introduction

| Fact | Value |
|---|---|
| Organization | [Public Software](https://github.com/public-software), `public-software` on GitHub |
| Site | [https://publicsoftware.dev](https://publicsoftware.dev) |
| Repositories | {{REPO_COUNT}}, in five rings: {{RING_COUNTS}} |
| Layers | {{LAYER_RANGE}} |
| Waves | {{WAVE_RANGE}} |
| Language | Rust `1.90` or newer, edition `2024` |
| Licences | code `Apache-2.0 OR MIT`; content and specifications `CC-BY-4.0` |
| Catalog | tag `v1.0.0` (tooling pins a tag, never `main`) |
| First release train | `2027.1` |
| Bootstrapped | 2026-09-02 |

- [The suite](suite.md) lists every repository, what it is for, which layers it serves, and when it becomes buildable.
- [How we work](how-we-work.md) states the contracts: spec-first cleanroom, RFCs, sign-off, licensing, the release train.
- [Contributing](contributing.md) is the short path from a first issue to a merged change.
- [Glossary](glossary.md) defines the terms the catalog uses.

## State

{{STATE_WIDGET}}

## In depth

### What the suite is

Public Software is a from-scratch, spec-first reimplementation of the software world as one suite: firmware, kernel, toolchain, desktop, office, media, engineering, enterprise. It is written in Rust and held in public.

Every repository in the organization signs the same contracts, so the parts fit together. Nothing here is a fork of an existing project. Where a standard exists, the suite implements the standard. Where a standard is paywalled or closed, the `specs` repository keeps a living, executable one.

### What this handbook is

This is the reference for how the suite is organized and how it is built. It is generated from the same catalog that configures the GitHub organization. So what it says about repositories, rings, layers and waves is what the organization enforces.

Each page opens with a facts box and the rules. The explanation follows under *In depth*.

### Status

The organization was bootstrapped on 2026-09-02. Every repository exists with its skeleton, its team, its rulesets and its labels. The first release train is `2027.1`. {{STATUS_LINE}}. [The suite](suite.md) says it per repository: the readiness column and each repository's page on the site are read from that repository's own `CATALOG.toml` when the site is built, so they say what has shipped, not what was planned.
