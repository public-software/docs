# Introduction

Public Software is a from-scratch, spec-first reimplementation of the software world as one suite: firmware, kernel, toolchain, desktop, office, media, engineering, enterprise. It is written in Rust and held in public.

Every repository in the organization signs the same contracts, so the parts fit together. Nothing here is a fork of an existing project; where a standard exists, the suite implements the standard, and where a standard is paywalled or closed, the `specs` repository keeps a living, executable one.

## What this handbook is

This is the reference for how the suite is organized and how it is built. It is generated from the same catalog that configures the GitHub organization, so what it says about repositories, rings, layers and waves is what the organization actually enforces.

- [The suite](suite.md) lists every repository, what it is for, which layers of the stack it serves, and when it becomes buildable.
- [How we work](how-we-work.md) states the contracts: spec-first cleanroom, RFCs, sign-off, licensing, the release train.
- [Contributing](contributing.md) is the short path from a first issue to a merged change.
- [Glossary](glossary.md) defines the terms the catalog uses.

## Status

The organization was bootstrapped on 2026-09-02. Every repository exists with its skeleton, its team, its rulesets and its labels. The first release train is `2027.1`. No crate has shipped yet; the handbook will say so, per repository, until one does.
