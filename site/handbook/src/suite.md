# The suite

Every repository in the organization, by dependency ring. Generated from the catalog; the readiness column is the highest readiness among the components each repository's own `CATALOG.toml` lists, read when the site was built.

## Spine

Defines, assembles and documents everything else.

| Repository | Purpose | Layers | Wave | Contents | Readiness |
|---|---|---|---|---|---|
| [catalog](https://github.com/public-software/catalog) | Machine-readable ledger + roadmap; source of truth for GitHub descriptions, topics, properties and the org README. | L18 | 1 | catalog.toml aggregate · schema · site generator · plugin registry · blob-free hardware list | no crate yet |
| [interfaces](https://github.com/public-software/interfaces) | Every cross-repo API as WIT packages and wire schemas, with generated binding crates. | all | 1 | public:doc/* · ui/* · plugin/* · identity/* · store/* · media/* · net/*; pub-interfaces-* crates | no crate yet |
| [suite](https://github.com/public-software/suite) | The superproject: lockfile pinning every crate, nightly whole-suite build, compatibility matrix, release trains, reference images. | all | 1 | Cargo.lock · compat-matrix · release notes assembler · reference platform images | no crate yet |
| [rfcs](https://github.com/public-software/rfcs) | Design proposals that cross repos or change an interface. Template, comment window, decision log. | all | 1 | RFC-0000 template · accepted/ · rejected/ | no crate yet |
| [docs](https://github.com/public-software/docs) | The suite handbook: architecture, contracts, contributor guide, per-repo mdBooks aggregated into one site. | all | 1 | mdBook site · architecture · contributor guide · glossary | seed |
| [pub](https://github.com/public-software/pub) | The org CLI: scaffold repos from templates, lint conventions, sync catalog → GitHub, pull and build the whole suite. | L2 | 1 | pub new · pub check · pub catalog sync/render · pub suite pull/build · pub labels sync · pub a11y-audit | partial |
| [templates](https://github.com/public-software/templates) | Repo and crate templates the CLI stamps out: lib, app, service, plugin, spec. | all | 1 | template-lib · template-app · template-service · template-plugin · template-spec | no crate yet |

## Platform

The crates every repository uses.

| Repository | Purpose | Layers | Wave | Contents | Readiness |
|---|---|---|---|---|---|
| [platform](https://github.com/public-software/platform) | Foundational crates every repo uses: errors, config layering, tracing facade, paths, i18n (fluent), settings schema, diagnostics bundle. | L4 | 1 | pub-platform-config · -log · -i18n · -paths · -settings · -diagnose · -secrets-client | partial |
| [design-system](https://github.com/public-software/design-system) | Tokens, type scale, icons, motion, shortcut map, command palette spec — the one look and feel. | L10 | 1 | tokens (JSON+Rust) · icon set · shortcut registry · theme engine | partial |
| [ui](https://github.com/public-software/ui) | The GUI toolkit driven to GTK/Qt completeness with AccessKit and IME built in; app shell, window/tab model, settings UI, command palette. | L10, L4 | 2 | pub-ui (toolkit) · pub-ui-shell · pub-ui-widgets · pub-ui-a11y · pub-ui-ime | no crate yet |
| [doc-model](https://github.com/public-software/doc-model) | CRDT document graph + container format + embed/export protocol. Every productivity and creative document is one of these. | L12 | 1 | pub-doc-model · pub-doc-container · pub-doc-sync · export adapters | seed |
| [plugin-runtime](https://github.com/public-software/plugin-runtime) | WASM Component Model host, capability policy, plugin test-kit, plugin packaging. | L2 | 1 | pub-plugin-host · pub-plugin-sdk · pub-plugin-testkit · pub-plugin-pack | seed |
| [identity](https://github.com/public-software/identity) | IdP (Kanidm-derived), OIDC/passkeys client, account picker, secrets vault client, attestation verifier (later), digital ID wallet core. | L6 | 1 | pubd-idp · pub-identity-client · pub-vault · pub-attest (wave 4) · pub-wallet | seed |
| [pkg](https://github.com/public-software/pkg) | Content-addressed reproducible package manager (Nix model) and the build cache; the distribution mechanism for the suite. | L4 | 1 | pub-pkg · pubd-cache · store format · transparency-log client | seed |
| [observe](https://github.com/public-software/observe) | Metrics/trace/log schema, OTel exporters, dashboards & alerting product (Grafana-class) on the Rust stores. | L8 | 1 | pub-observe · pubd-dash · alert rules · SIEM UI (with security) | seed |

## System

Toolchain, silicon, kernel, base, infrastructure, media, shells.

| Repository | Purpose | Layers | Wave | Contents | Readiness |
|---|---|---|---|---|---|
| [compiler](https://github.com/public-software/compiler) | Rust-native optimizing backend on Cranelift, bootstrap seed, scripting runtimes to parity, C→Rust migration tooling. | L2 | 1 | cg-clif optimization · seed interpreter · rustpython/piccolo parity · c2rust idiomatic pass | no crate yet |
| [linker](https://github.com/public-software/linker) | Wild linker with Mach-O and PE, assembler and object tooling for all targets. | L2 | 1 | pub-ld · pub-as · object tooling | no crate yet |
| [devtools](https://github.com/public-software/devtools) | Native debugger (DAP), pure-Rust fuzzer, profilers, formal-verification harness integration. | L2 | 1 | pub-dbg · pub-fuzz · pub-prof · verify harness | no crate yet |
| [firmware](https://github.com/public-software/firmware) | Rust UEFI implementation, oreboot on openSIL boards, TPM 2.0 firmware, BMC (Redfish), firmware update service. | L1 | 1 | pub-uefi · oreboot ports · pub-tpm · pub-bmc · pubd-fwupd | no crate yet |
| [hdl](https://github.com/public-software/hdl) | Rust HDL, fast cycle simulator, verification library; the root of the silicon chain. | L0 | 1 | pub-hdl (language) · pub-sim · pub-hdl-verify | no crate yet |
| [eda](https://github.com/public-software/eda) | RTL-to-GDS flow, FPGA bitstream reverse engineering and place-and-route, targeting IHP/sky130 and open FPGAs. | L0 | 2 | pub-synth · pub-pnr · pub-timing · pub-drc · fpga-bits | no crate yet |
| [silicon](https://github.com/public-software/silicon) | Open chip designs: root of trust, RF front-end control, FPGA GPU, reference RISC-V platform definitions; shuttle submissions. | L0 | 3 | rot chip · rf-fe · fpga-gpu · riscv-platform · shuttle/ runs | no crate yet |
| [kernel](https://github.com/public-software/kernel) | Kernel hardening (Redox-derived microkernel and Asterinas-style Linux-ABI), scheduler, capability security, driver ABI, libc. | L3, L4 | 1 | pub-kernel · pub-libc (relibc) · syscall ABI · capability model | no crate yet |
| [drivers](https://github.com/public-software/drivers) | Device drivers: GPU (Nova/Tyr/Asahi tracks + Rust Vulkan userspace), storage, USB, network, Wi-Fi/BT host, audio server, camera, input, power. | L3 | 2 | gpu/ · storage/ · usb/ · net/ · wifi-bt/ · audio (PipeWire-class) · camera · input · power | no crate yet |
| [base](https://github.com/public-software/base) | Init & service manager, journal, util-linux/procps parity, disk encryption, accessibility bus, screen reader. | L4 | 1 | pubd-init · pubd-journal · utils · pub-crypt (LUKS2) · pub-a11y-bus · pub-reader | no crate yet |
| [virt](https://github.com/public-software/virt) | Type-1 hypervisor, VMM integration, container runtime integration, sandboxing. | L3 | 2 | pub-hv · vmm glue · sandbox profiles | no crate yet |
| [net](https://github.com/public-software/net) | Host TCP/IP stack, routing suite + dataplane, 5G core, push distributor, SSH daemon, VPN suite. | L5 | 1 | pub-netstack · pubd-route · pubd-5gc · pubd-push · pubd-ssh · vpn | no crate yet |
| [sdr](https://github.com/public-software/sdr) | SDR framework with GPU DSP, GNSS receiver, SDR 4G/5G UE (lab/private-network) — the modem programme. | L0, L5 | 1 | pub-sdr · pub-gnss · pub-ue | no crate yet |
| [store](https://github.com/public-software/store) | Relational engine (Postgres-class), KV, cache (Valkey-compatible), graph, object/block store (Ceph-class), streaming (Kafka-protocol), ETL, spreadsheet engine. | L7 | 1 | pubd-sql · pub-kv · pubd-cache · pubd-graph · pubd-objstore · pubd-stream · pubd-flow · pub-calc | no crate yet |
| [cloud](https://github.com/public-software/cloud) | Container orchestration control plane (K8s-API compatible), IaaS control plane, IaC engine, config management, OCI registry, CI runner. | L8 | 1 | pubd-orch · pubd-iaas · pub-iac · pub-cfg · pubd-registry · pubd-ci | no crate yet |
| [forge](https://github.com/public-software/forge) | Code forge (repos, issues, reviews, packages, federation) on gitoxide; the future canonical home of this org. | L8 | 2 | pubd-forge · ForgeFed · mirror bot | no crate yet |
| [security](https://github.com/public-software/security) | Secrets manager + PKCS#11, CA product, endpoint sensor + detection engine, SIEM correlation, transparency log. | L6 | 1 | pubd-secrets · pubd-ca · pub-sensor · pubd-detect · pubd-translog | no crate yet |
| [comms](https://github.com/public-software/comms) | Mail client, chat clients (Matrix, Signal-class), SIP/PBX, video-meeting SFU + client, federated social server. | L5, L12 | 1 | pub-mail · pub-chat · pubd-pbx · pubd-meet · pubd-social | no crate yet |
| [graphics](https://github.com/public-software/graphics) | Shader toolchain hardening (naga), software Vulkan/WebGPU rasterizer, colour management, OCR. | L9 | 1 | pub-naga-ext · pub-swrast · pub-cms · pub-ocr | no crate yet |
| [media](https://github.com/public-software/media) | FFmpeg-class framework, Opus encoder + IAMF, player, streaming server, screen capture / live production. | L9 | 1 | pub-media (framework) · pub-opus · pub-iamf · pub-player · pubd-stream-media · pub-studio | no crate yet |
| [js](https://github.com/public-software/js) | JavaScript engine with JIT tiers; Node-class runtime on it. | L11 | 2 | pub-js (Boa-derived) · pub-js-jit · pub-node | no crate yet |
| [desktop](https://github.com/public-software/desktop) | Compositor features, desktop environment completeness, input methods, portals, session. | L10 | 2 | pub-comp · pub-desktop · pub-ime · portals | no crate yet |
| [mobile](https://github.com/public-software/mobile) | Mobile OS assembly: modem quarantine architecture, app store + reproducible builds, push, wallet integration, device support. | L10 | 3 | pub-mobile · modem-iso · pub-store · device/ | no crate yet |
| [web](https://github.com/public-software/web) | Servo work (a11y, layout, editing), browser product, PDF render/edit, maps renderer + router, CMS, analytics. | L11 | 1 | servo tracks · pub-browser · pub-pdf · pub-maps · pubd-cms · pubd-analytics | no crate yet |
| [ai](https://github.com/public-software/ai) | Burn/CubeCL work on open backends, inference server, distributed training, TTS, voice assistant, CV, model recipes. | L15 | 1 | burn tracks · cubecl-vulkan · pubd-infer · pub-dist · pub-tts · pub-assistant · pub-cv · recipes/ | no crate yet |

## Domain

The products.

| Repository | Purpose | Layers | Wave | Contents | Readiness |
|---|---|---|---|---|---|
| [office](https://github.com/public-software/office) | Word processor, spreadsheet application, presentations, document format libraries. | L12, L7 | 1 | pub-office-docfmt · pub-office-writer · pub-office-sheets · pub-office-slides | no crate yet |
| [workspace](https://github.com/public-software/workspace) | Notes & knowledge base, project management, file sync, whiteboard, design tool, e-signature, calendar/contacts server, personal finance, e-book library, translation. | L12 | 1 | pub-notes · pub-pm · pubd-sync · pub-board · pub-design · pub-sign · pubd-cal · pub-money · pub-books · pubd-translate | no crate yet |
| [home](https://github.com/public-software/home) | Home automation hub with Matter, assistant integration, TV/set-top shell, wearables. | L12, L10 | 2 | pubd-home · pub-tv · pub-watch | no crate yet |
| [imaging](https://github.com/public-software/imaging) | Raster editor (Graphite raster), vector editor, RAW development, page layout, font editor. | L13 | 1 | pub-raster · pub-vector · pub-raw · pub-layout · pub-fonted | no crate yet |
| [video](https://github.com/public-software/video) | Video editor (NLE) and compositing / motion graphics. | L13 | 3 | pub-nle · pub-comp | no crate yet |
| [audio](https://github.com/public-software/audio) | Digital audio workstation, audio editor, music notation, plugin collection. | L13 | 2 | pub-daw · pub-audioedit · pub-notation · plugins/ | no crate yet |
| [3d](https://github.com/public-software/3d) | 3D content creation suite (Blender-class) and game engine editor (Godot-class on Bevy), XR runtime. | L13, L17 | 2 | pub-dcc · pub-engine-editor · pub-xr | no crate yet |
| [cad](https://github.com/public-software/cad) | B-rep CAD kernel, parametric CAD application, CAM, meshing. | L14 | 1 | pub-brep · pub-mcad · pub-cam · pub-mesh | no crate yet |
| [engineering](https://github.com/public-software/engineering) | PCB EDA, SPICE, FEA, CFD, systems modelling (Modelica), PLC runtime, SCADA/HMI, DAQ, robotics tooling. | L14 | 1 | pub-pcb · pub-spice · pub-fea · pub-cfd · pub-modelica · pub-plc · pub-scada · pub-daq · pub-robot | no crate yet |
| [science](https://github.com/public-software/science) | Numerical computing environment, statistics, computer algebra, notebooks, GIS, medical imaging viewer, bioinformatics, solvers. | L14 | 1 | pub-num · pub-stats · pub-cas · pubd-notebook · pub-gis · pub-dicom · pub-bio · pub-solve | no crate yet |
| [business](https://github.com/public-software/business) | Accounting core, ERP, CRM, billing/e-invoicing, HR & payroll, e-commerce, helpdesk, BI, PLM/MES. | L16 | 2 | pub-ledger · pub-erp · pub-crm · pub-billing · pub-hr · pub-shop · pub-desk · pub-bi · pub-plm | no crate yet |
| [finance](https://github.com/public-software/finance) | Core banking, trading & market data, account-to-account wallet. | L16 | 2 | pubd-bank · pub-trade · pub-wallet-pay | no crate yet |
| [health](https://github.com/public-software/health) | FHIR-native EHR, LIMS, open clinical terminology. | L16 | 1 | pub-ehr · pub-lims · openmed/ | no crate yet |
| [civic](https://github.com/public-software/civic) | Rules engine (tax/benefits), rules-as-code corpus tooling, LMS, elections, legal research. | L16 | 1 | pub-rules · corpus tooling · pub-lms · pub-vote · pub-law | no crate yet |
| [games](https://github.com/public-software/games) | Win32/DirectX compatibility layer, emulation & preservation, server-authoritative anti-cheat standard + reference, storefront/launcher. | L17 | 1 | pub-compat · pub-emu · pub-fairplay · pub-launcher | no crate yet |

## Standards

Living specs and open data.

| Repository | Purpose | Layers | Wave | Contents | Readiness |
|---|---|---|---|---|---|
| [specs](https://github.com/public-software/specs) | Living specs and executable conformance suites for paywalled or closed standards, and for the suite's own formats. | L18 | 1 | step-living · iec61131-living · iso8583-living · doc-container spec · plugin ABI spec · attestation spec | no crate yet |
| [content](https://github.com/public-software/content) | Open data the suite depends on: rules-as-code corpus, open clinical terminology, blob-free hardware list, camera RAW profiles, localizations (chart of accounts, tax tables). | L18 | 1 | rules/ · openmed/ · hardware/ · raw-profiles/ · l10n/ | no crate yet |
