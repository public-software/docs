#!/usr/bin/env python3
"""The public site: a landing page in the identity, one page per repository and the mdBook handbook,
built and deployed by this repository's Pages workflow (.github/workflows/pages.yml).

  python3 site/build.py build  --catalog-dir DIR [--repos DIR] [--out DIR]   # → <out>/www/ (the pages) and <out>/handbook/ (mdBook source)
  python3 site/build.py status --catalog-dir DIR [--repos DIR]               # the readiness count line the org profile README carries
  python3 site/build.py readiness --catalog-dir DIR [--repos DIR]            # name<TAB>readiness per repository (what the Roadmap project mirrors)

Inputs, all next to this file unless a flag says otherwise: org.env (the organization values, rendered by the
bootstrap kit), catalog.lock (the catalog this site is built from: the build refuses a catalog.toml that does not
hash to the lock), brand/ (metaphors.py, objects.py, paradigms.py and the rendered PNGs, vendored by the kit) and
handbook/. --catalog-dir holds catalog.toml and catalog.schema.json: the catalog repository's catalog/ directory
checked out at the lock's ref, or the kit's config/. What has shipped comes from each repository's own CATALOG.toml
([[component]] entries: crate, kind, readiness), read through `gh api` at build time, or from local checkouts
under --repos DIR (offline; what the kit's tests use).

The build also writes state.json at the site root, the one machine-readable state the landing page's map, the
handbook and agents read:

  {"as_of": "YYYY-MM-DD",                       # the build date
   "status": "N of M repositories have a first crate, as of YYYY-MM-DD[; K could not be read]",
   "waves": {"1": {"repositories": 42, "with_crate": 7}, ...},
   "repositories": [{"name": "kernel", "ring": "system", "wave": 1, "layers": ["L3", "L4"],
                     "readiness": "partial",   # the highest component readiness (none|seed|partial|shipped),
                                               # "no crate yet" when none is listed, "unknown" when unreadable
                     "components": [{"crate": "pub-kernel-core", "kind": "lib", "readiness": "partial"}, ...]},
                    ...]}                      # components: [] for no crate yet, null for unknown
"""
import argparse
import base64
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent / "target" / "site"
RINGS = [
    ("spine", "Spine", "defines, assembles and documents everything else"),
    ("platform", "Platform", "the crates every repository uses"),
    ("system", "System", "toolchain, silicon, kernel, base, infrastructure, media, shells"),
    ("domain", "Domain", "the products"),
    ("standards", "Standards", "living specs and open data"),
]
LAYERS = [f"L{i}" for i in range(19)]                # the ledger, L0 (silicon) to L18 (content)
BANDS = {"L0": "silicon", "L4": "system", "L8": "platform", "L12": "apps", "L16": "content"}   # the brand's five bands, by first layer
ALL_LAYERS = "all"                                   # the spine's layer value: the whole ledger


def org_env(path: Path) -> dict:
    """KEY="value" lines of an org.env file (the kit's config/org.env, or site/org.env rendered from it)."""
    env = {}
    for line in path.read_text().splitlines():
        m = re.match(r'^([A-Z_]+)="(.*?)"', line)
        if m:
            env[m.group(1)] = m.group(2)
    return env


def load_catalog(catalog_dir: Path) -> list[dict]:
    """Every repository but .github, from catalog.toml in the catalog directory."""
    with (catalog_dir / "catalog.toml").open("rb") as f:
        return [x for x in tomllib.load(f)["repo"] if x["name"] != ".github"]


def check_lock(catalog_dir: Path, lock: Path) -> None:
    """catalog.lock names the sha256 of the catalog.toml this site is built against; any other file is drift."""
    if not lock.is_file():
        return
    want = str(tomllib.loads(lock.read_text()).get("sha256", ""))
    have = hashlib.sha256((catalog_dir / "catalog.toml").read_bytes()).hexdigest()
    if want != have:
        sys.exit(f"catalog drift: {catalog_dir / 'catalog.toml'} hashes to {have}, but {lock} names {want}; "
                 "check the catalog out at the lock's ref, or let the bootstrap kit re-render the lock with the catalog")


# ---------------------------------------------------------------- the brand: the marks are drawn by the vendored modules

METAPHORS: dict = {}
RING_COLORS: dict = {}
ORG: dict = {}
contour_mark = None


def load_brand(brand_dir: Path) -> None:
    """metaphors.py, objects.py and paradigms.py under brand/ (the kit vendors them there)."""
    global METAPHORS, RING_COLORS, ORG, contour_mark
    sys.path.insert(0, str(brand_dir))
    import metaphors  # noqa: E402
    import paradigms  # noqa: E402
    METAPHORS, RING_COLORS, ORG, contour_mark = metaphors.METAPHORS, paradigms.RING_COLORS, paradigms.ORG, paradigms.contour_mark


def render(text: str, env: dict) -> str:
    for k, v in env.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def transparent(svg: str) -> str:
    return svg.replace('<rect width="64" height="64" fill="#F2F3F1"/>', "", 1)


# ---------------------------------------------------------------- readiness: what each repository's CATALOG.toml says has shipped

READINESS = ["none", "seed", "partial", "shipped"]   # the [[component]] vocabulary of the skeleton's CATALOG.toml, lowest first
NO_CRATE = "no crate yet"                            # the file lists no component
UNKNOWN = "unknown"                                  # the file could not be read or parsed
FETCH_WORKERS = 8
Components = list[dict] | None                       # None: unreadable


def parse_components(text: str) -> Components:
    """The [[component]] entries of one CATALOG.toml (crate, kind, readiness); None when it does not parse."""
    try:
        doc = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return None
    entries = doc.get("component", [])
    return [{"crate": str(c.get("crate", "?")), "kind": str(c.get("kind", "?")), "readiness": str(c.get("readiness", "none"))}
            for c in entries if isinstance(c, dict)]


def read_checkout(repos_dir: Path, name: str) -> Components:
    """<repos_dir>/<name>/CATALOG.toml; None when there is no such checkout."""
    try:
        return parse_components((repos_dir / name / "CATALOG.toml").read_text())
    except OSError:
        return None


def fetch_catalog(org: str, name: str) -> Components:
    """CATALOG.toml through `gh api` (the JSON content response, base64); None when gh cannot read it."""
    r = subprocess.run(["gh", "api", f"/repos/{org}/{name}/contents/CATALOG.toml", "--jq", ".content"], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        return parse_components(base64.b64decode(r.stdout).decode())
    except (ValueError, UnicodeDecodeError):
        return None


def components(env: dict, repos: list[dict], repos_dir: Path | None) -> dict[str, Components]:
    """name → its [[component]] entries, from local checkouts under repos_dir or from GitHub."""
    names = [r["name"] for r in repos]
    if repos_dir is not None:
        return {n: read_checkout(repos_dir, n) for n in names}
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        return dict(zip(names, pool.map(lambda n: fetch_catalog(env["ORG"], n), names)))


def repo_readiness(parts: Components) -> str:
    """The highest component readiness; NO_CRATE when none is listed; UNKNOWN when the file could not be read."""
    if parts is None:
        return UNKNOWN
    if not parts:
        return NO_CRATE
    return max((p["readiness"] for p in parts), key=lambda r: READINESS.index(r) if r in READINESS else -1)


def status_line(shipped: dict[str, Components], as_of: str) -> str:
    """'N of M repositories have a first crate, as of <date>', and how many could not be read when some could not."""
    with_crate = sum(1 for p in shipped.values() if p)
    unread = sum(1 for p in shipped.values() if p is None)
    line = f"{with_crate} of {len(shipped)} repositories have a first crate, as of {as_of}"
    return f"{line}; {unread} could not be read" if unread else line


# ---------------------------------------------------------------- state: state.json and the map the landing page draws from it

def state(repos: list[dict], shipped: dict[str, Components], as_of: str) -> dict:
    """The site's machine-readable state (the shape is in the module docstring)."""
    waves: dict[str, dict] = {}
    for r in repos:
        w = waves.setdefault(str(r["wave"]), {"repositories": 0, "with_crate": 0})
        w["repositories"] += 1
        w["with_crate"] += 1 if shipped[r["name"]] else 0
    entries = [{"name": r["name"], "ring": r["ring"], "wave": r["wave"], "layers": r["layers"],
                "readiness": repo_readiness(shipped[r["name"]]), "components": shipped[r["name"]]} for r in repos]
    return {"as_of": as_of, "status": status_line(shipped, as_of), "waves": dict(sorted(waves.items())), "repositories": entries}


def verdict(st: dict) -> str:
    """The 'are we X yet' answer: yes when every repository has shipped, otherwise how far it has come."""
    entries = st["repositories"]
    n, with_crate = len(entries), sum(1 for e in entries if e["components"])
    shipped = sum(1 for e in entries if e["readiness"] == "shipped")
    if shipped == n:
        return "Yes."
    if shipped:
        return f"Getting there: {shipped} of {n} repositories have shipped a component, and {with_crate} have a first crate."
    if with_crate:
        return f"Not yet, but it has started: {with_crate} of {n} repositories have a first crate; none has shipped a component."
    return f"Not yet: none of the {n} repositories has a first crate."


def wave_bars(st: dict) -> str:
    """One bar per wave: 'wave 1: 7 of 42 repositories have a first crate'."""
    out = ""
    for wave, c in st["waves"].items():
        pct = round(100 * c["with_crate"] / c["repositories"]) if c["repositories"] else 0
        out += (f'<div class="wave"><span>wave {wave}: {c["with_crate"]} of {c["repositories"]} repositories have a first crate</span>'
                f'<i><b style="width:{pct}%"></b></i></div>')
    return out


def components_text(parts: Components) -> str:
    """'crate (kind, readiness), ...' for the tile's title and detail box; the honest word when there is nothing to list."""
    if parts is None:
        return UNKNOWN
    if not parts:
        return NO_CRATE
    return ", ".join(f'{p["crate"]} ({p["kind"]}, {p["readiness"]})' for p in parts)


def tile(repo: dict, parts: Components) -> str:
    """One repository on the map: a link to its page, coloured by readiness, carrying its facts for the filter and the detail box."""
    readiness = repo_readiness(parts)
    cls = "none" if readiness == NO_CRATE else readiness if readiness in READINESS else UNKNOWN
    layers, comps = ", ".join(repo["layers"]), html.escape(components_text(parts), quote=True)
    title = f'{repo["name"]} · {repo["ring"]} ring · wave {repo["wave"]} · {layers} · {readiness} · {comps}'
    return (f'<a class="tile r-{cls}" href="/{repo["name"]}/" data-wave="{repo["wave"]}" data-ring="{repo["ring"]}" data-layers="{layers}" '
            f'data-readiness="{readiness}" data-components="{comps}" title="{title}">{repo["name"]}</a>')


def ledger_grid(repos: list[dict], shipped: dict[str, Components]) -> str:
    """The ledger: one row per layer L0–L18 (labelled by band), one column per ring; a repository sits in the row of its first
    catalog layer, and the spine repositories serving every layer share one cell spanning the whole ledger."""
    tiles = {r["name"]: tile(r, shipped[r["name"]]) for r in repos}
    at = {(r["ring"], r["layers"][0]): [] for r in repos}
    for r in repos:
        at[(r["ring"], r["layers"][0])].append(tiles[r["name"]])
    heads = "".join(f'<div class="col{" spine" if k == "spine" else ""}" style="--ring:{RING_COLORS[k]}">{t}</div>' for k, t, _ in RINGS)
    rows = f'<div class="corner">layer</div>{heads}\n<div class="cell all" data-ring="spine">{"".join(at.get(("spine", ALL_LAYERS), []))}</div>\n'
    for layer in LAYERS:
        band = f"<small>{BANDS[layer]}</small>" if layer in BANDS else ""
        cells = "".join(f'<div class="cell" data-layer="{layer}" data-ring="{k}">{"".join(at.get((k, layer), []))}</div>' for k, _, _ in RINGS)
        rows += f'<div class="layer"><b>{layer}</b>{band}</div>{cells}\n'
    return f'<div class="ledger">\n{rows}</div>'


STATE_CSS = """
.verdict { font-size:22px; font-weight:700; letter-spacing:-0.3px; margin:0 0 10px; text-wrap:balance; }
.bars { display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:10px 28px; margin:0 0 20px; }
.wave span { display:block; font-family:"JetBrains Mono", Menlo, monospace; font-size:12px; color:var(--muted); margin-bottom:5px; overflow-wrap:anywhere; }
.wave i { display:block; height:8px; border-radius:4px; background:var(--paper); border:1px solid var(--line); overflow:hidden; }
.wave b { display:block; height:100%; background:var(--blue); min-width:2px; }
.tools { display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap; margin:0 0 12px; }
.waves { display:flex; gap:6px; } .waves button { font:inherit; font-size:13px; font-weight:600; padding:5px 11px; border:1px solid var(--line); border-radius:7px; background:var(--paper); color:var(--ink); cursor:pointer; }
.waves button[aria-pressed="true"] { background:var(--blue); border-color:var(--blue); color:#fff; }
.legend { display:flex; gap:14px; flex-wrap:wrap; font-family:"JetBrains Mono", Menlo, monospace; font-size:11px; color:var(--muted); }
.legend span { display:inline-flex; align-items:center; gap:6px; } .legend i { width:14px; height:14px; border-radius:3px; display:inline-block; }
.scroll { overflow-x:auto; border:1px solid var(--line); border-radius:12px; background:var(--paper); }
.ledger { display:grid; grid-template-columns:82px max-content max-content repeat(4, minmax(120px, 1fr)); gap:2px; min-width:760px; padding:2px; }
.ledger > div { background:var(--page); min-height:34px; padding:4px 6px; }
.ledger .corner, .ledger .col { font-family:"JetBrains Mono", Menlo, monospace; font-size:11px; font-weight:600; letter-spacing:0.6px; text-transform:uppercase; color:var(--muted); display:flex; align-items:center; gap:8px; }
.ledger .col::before { content:""; width:12px; height:12px; border-radius:3px; background:var(--ring); flex:none; } .ledger .col.spine { grid-column:span 2; }
.ledger .layer { font-family:"JetBrains Mono", Menlo, monospace; font-size:11px; color:var(--muted); display:flex; flex-direction:column; justify-content:center; }
.ledger .layer b { font-weight:600; color:var(--ink); } .ledger .layer small { font-size:10px; letter-spacing:0.5px; text-transform:uppercase; }
.ledger .cell { display:flex; flex-wrap:wrap; gap:4px; align-content:center; }
.ledger .cell.all { grid-column:2; grid-row:2 / span 19; flex-direction:column; justify-content:center; flex-wrap:nowrap; gap:6px; }
.ledger .cell.all::before { content:"all layers"; font-family:"JetBrains Mono", Menlo, monospace; font-size:10px; letter-spacing:0.5px; text-transform:uppercase; color:var(--muted); margin-bottom:4px; }
.tile { font-family:"JetBrains Mono", Menlo, monospace; font-size:11.5px; font-weight:600; padding:3px 8px; border-radius:5px; border:1px solid transparent; color:var(--ink); transition:opacity .12s; }
.tile:hover, .tile:focus { text-decoration:none; outline:2px solid var(--blue); outline-offset:1px; }
.r-none, .legend .r-none { background:var(--paper); border-color:var(--line); border-style:dashed; color:var(--muted); }
.r-seed, .legend .r-seed { background:var(--seed); border-color:var(--seed); }
.r-partial, .legend .r-partial { background:var(--partial); border-color:var(--partial); color:var(--partial-ink); }
.r-shipped, .legend .r-shipped { background:var(--blue); border-color:var(--blue); color:#fff; }
.r-unknown, .legend .r-unknown { background:repeating-linear-gradient(45deg, var(--paper) 0 4px, var(--line) 4px 6px); border-color:var(--line); color:var(--muted); }
#state[data-wave="1"] .tile:not([data-wave="1"]), #state[data-wave="2"] .tile:not([data-wave="2"]), #state[data-wave="3"] .tile:not([data-wave="3"]), #state[data-wave="4"] .tile:not([data-wave="4"]), #state[data-wave="5"] .tile:not([data-wave="5"]) { opacity:0.15; }
.detail { margin:12px 0 0; min-height:24px; font-family:"JetBrains Mono", Menlo, monospace; font-size:12.5px; color:var(--muted); }
.detail b { color:var(--ink); }
"""

STATE_JS = """<script>
(function () {
  var s = document.getElementById('state'), w = s.querySelector('.waves'), d = document.getElementById('detail');
  w.hidden = false;
  w.addEventListener('click', function (e) {
    var b = e.target.closest('button'); if (!b) return;
    s.dataset.wave = b.dataset.wave;
    w.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
  });
  function show(t) {
    var b = document.createElement('b'); b.textContent = t.textContent;
    d.textContent = ''; d.appendChild(b);
    d.appendChild(document.createTextNode(' · ' + t.dataset.ring + ' ring · wave ' + t.dataset.wave + ' · ' + t.dataset.layers + ' · ' + t.dataset.readiness + ' · ' + t.dataset.components));
  }
  s.addEventListener('mouseover', function (e) { var t = e.target.closest('.tile'); if (t) show(t); });
  s.addEventListener('focusin', function (e) { var t = e.target.closest('.tile'); if (t) show(t); });
})();
</script>"""


def state_section(st: dict, repos: list[dict], shipped: dict[str, Components]) -> str:
    """The landing page's state section: the verdict, one bar per wave, the wave filter and legend, the ledger, the detail box."""
    buttons = '<button data-wave="all" aria-pressed="true">All waves</button>' + "".join(
        f'<button data-wave="{w}">Wave {w}</button>' for w in st["waves"])
    legend = "".join(f'<span><i class="r-{c}"></i>{c}</span>' for c in READINESS + [UNKNOWN])
    return f"""<section id="state" data-wave="all">
  <h2>Is the suite built yet?</h2>
  <p class="verdict">{verdict(st)}</p>
  <p class="sub">The ledger: every repository in its ring, at the layer it serves first, coloured by what its own <code>CATALOG.toml</code> says has shipped. Rebuilt nightly from the same data as <a href="/state.json">state.json</a>. Hover or focus a tile for its components; click through to the repository.</p>
  <div class="bars">{wave_bars(st)}</div>
  <div class="tools"><div class="waves" hidden>{buttons}</div><div class="legend">{legend}</div></div>
  <div class="scroll">{ledger_grid(repos, shipped)}</div>
  <div class="detail" id="detail" aria-live="polite">{st["status"]}.</div>
</section>"""


# ---------------------------------------------------------------- landing page

CSS = """
:root { --page:#FAFAF8; --paper:#F2F3F1; --ink:#14181F; --muted:#5B6472; --line:#DADDD9; --blue:#1F4E8C; --blue-ink:#163B6B; --seed:#D6E3F5; --partial:#7FA7DE; --partial-ink:#14181F; }
@media (prefers-color-scheme: dark) { :root { --page:#0F141B; --paper:#171D26; --ink:#EEF0EC; --muted:#9AA3AE; --line:#2A323D; --blue:#7FA7DE; --blue-ink:#A9C4EC; --seed:#23344D; --partial:#3A5F95; --partial-ink:#EEF0EC; } }
* { box-sizing:border-box; }
body { margin:0; background:var(--page); color:var(--ink); font-family:"Public Sans", system-ui, -apple-system, sans-serif; line-height:1.5; -webkit-font-smoothing:antialiased; }
a { color:var(--blue); text-decoration:none; } a:hover { text-decoration:underline; }
.wrap { max-width:1120px; margin:0 auto; padding:0 24px; }
header.top { display:flex; align-items:center; justify-content:space-between; padding:22px 0; }
.brand { display:flex; align-items:center; gap:12px; font-weight:800; letter-spacing:-0.3px; color:var(--ink); }
.brand img { width:34px; height:34px; }
nav a { margin-left:22px; font-weight:600; color:var(--ink); } nav a:hover { color:var(--blue); text-decoration:none; }
.hero { display:grid; grid-template-columns:1.05fr 1fr; gap:40px; align-items:center; padding:36px 0 56px; }
.hero img { width:100%; height:auto; border-radius:10px; }
h1 { font-size:clamp(34px, 5vw, 54px); line-height:1.05; letter-spacing:-1.5px; font-weight:800; margin:0 0 18px; text-wrap:balance; }
h1 em { font-style:normal; color:var(--blue); }
.lede { font-size:18px; color:var(--muted); max-width:52ch; margin:0 0 26px; }
p.status { font-family:"JetBrains Mono", Menlo, monospace; font-size:13px; color:var(--muted); margin:-12px 0 26px; }
.cta { display:flex; gap:12px; flex-wrap:wrap; }
.cta a { padding:11px 18px; border-radius:8px; font-weight:700; border:1.5px solid var(--blue); }
.cta a.primary { background:var(--blue); color:#fff; } .cta a.primary:hover { background:var(--blue-ink); border-color:var(--blue-ink); text-decoration:none; }
.cta a:hover { text-decoration:none; }
h2 { font-size:26px; font-weight:800; letter-spacing:-0.5px; margin:0 0 6px; }
.sub { color:var(--muted); margin:0 0 22px; max-width:66ch; }
section { padding:40px 0; border-top:1px solid var(--line); }
.start { display:grid; grid-template-columns:repeat(3, 1fr); gap:18px; }
.start a { display:block; padding:20px; border:1px solid var(--line); border-radius:12px; color:var(--ink); background:var(--paper); }
.start a:hover { border-color:var(--blue); text-decoration:none; }
.start b { display:block; font-size:17px; margin-bottom:6px; } .start span { color:var(--muted); font-size:14.5px; }
.start code { font-family:"JetBrains Mono", Menlo, monospace; font-size:13px; }
h3.ring { font-family:"JetBrains Mono", Menlo, monospace; font-size:13px; font-weight:600; letter-spacing:0.6px; text-transform:uppercase; margin:30px 0 4px; display:flex; align-items:center; gap:10px; }
h3.ring i { width:12px; height:12px; border-radius:3px; display:inline-block; }
p.ringsub { color:var(--muted); margin:0 0 14px; font-size:14.5px; }
.repos { display:grid; grid-template-columns:repeat(auto-fill, minmax(250px, 1fr)); gap:12px; }
.repo { position:relative; display:grid; grid-template-columns:56px 1fr; gap:14px; padding:14px; border:1px solid var(--line); border-radius:12px; color:var(--ink); align-items:start; }
.repo:hover, .repo:focus-within { border-color:var(--blue); }
.repo a.cover { color:inherit; } .repo a.cover::after { content:""; position:absolute; inset:0; border-radius:12px; }
.repo a.cover:hover { text-decoration:none; }
.repo a.gh { position:absolute; top:10px; right:10px; z-index:2; display:inline-flex; align-items:center; gap:6px; padding:5px 9px; border-radius:7px; background:var(--blue); color:#fff; font-size:12px; font-weight:700; opacity:0; transition:opacity .12s; }
.repo:hover a.gh, .repo a.gh:focus, .repo:focus-within a.gh { opacity:1; } .repo a.gh:hover { text-decoration:none; background:var(--blue-ink); }
.repo a.gh svg { width:14px; height:14px; fill:currentColor; }
@media (hover:none) { .repo a.gh { opacity:1; } }
.repo svg { width:56px; height:56px; border-radius:10px; background:var(--paper); }
.repo b { font-family:"JetBrains Mono", Menlo, monospace; font-size:14px; font-weight:600; }
.repo span { display:block; color:var(--muted); font-size:13.5px; line-height:1.4; margin-top:3px; }
.repo small { display:block; color:var(--muted); font-family:"JetBrains Mono", Menlo, monospace; font-size:11px; margin-top:6px; letter-spacing:0.3px; }
.how { display:grid; grid-template-columns:repeat(2, 1fr); gap:22px 40px; }
.how b { display:block; margin-bottom:4px; } .how p { margin:0; color:var(--muted); }
footer { padding:36px 0 56px; border-top:1px solid var(--line); color:var(--muted); font-size:14px; display:flex; justify-content:space-between; gap:20px; flex-wrap:wrap; }
footer a { color:var(--ink); }
@media (max-width:820px) { .hero, .start, .how { grid-template-columns:1fr; } nav a { margin-left:14px; } }
"""


GITHUB_ICON = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/></svg>'


def landing(env: dict, repos: list[dict], st: dict, shipped: dict[str, Components]) -> str:
    org, name, cli = env["ORG"], env["ORG_DISPLAY_NAME"], env["CLI"]
    by_ring: dict[str, list[dict]] = {}
    for r in repos:
        by_ring.setdefault(r["ring"], []).append(r)
    rings_html = ""
    for key, title, blurb in RINGS:
        cards = "".join(
            f'<div class="repo">{transparent(contour_mark(r, "paper"))}'
            f'<div><a class="cover" href="/{r["name"]}/"><b>{r["name"]}</b></a><span>{r["purpose"]}</span><small>{", ".join(r["layers"])} · wave {r["wave"]}</small></div>'
            f'<a class="gh" href="https://github.com/{org}/{r["name"]}" aria-label="{r["name"]} on GitHub">{GITHUB_ICON}GitHub</a></div>'
            for r in by_ring.get(key, [])
        )
        rings_html += f'<h3 class="ring"><i style="background:{RING_COLORS[key]}"></i>{title}</h3><p class="ringsub">{blurb}.</p><div class="repos">{cards}</div>'
    count = len(repos)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}</title>
<meta name="description" content="{env["ORG_DESCRIPTION"]}">
<meta property="og:title" content="{name}">
<meta property="og:description" content="{env["ORG_DESCRIPTION"]}">
<meta property="og:image" content="{env["ORG_URL"]}/assets/social.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/assets/mark-460.png">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap">
<style>{CSS}{STATE_CSS}</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <a class="brand" href="/"><img src="/favicon.svg" alt="">{name}</a>
  <nav><a href="#state">State</a><a href="/handbook/">Handbook</a><a href="#suite">The suite</a><a href="https://github.com/{org}/rfcs/pulls">RFCs</a><a href="https://github.com/{org}">GitHub</a></nav>
</header>

<section class="hero" style="border-top:0">
  <div>
    <h1>The whole software stack, <em>rebuilt from scratch in Rust</em>, as one open suite.</h1>
    <p class="lede">Firmware to office suite: {count} repositories that sign the same contracts, so the parts fit. Spec-first, cleanroom, held in public. Nothing here is a fork.</p>
    <p class="status">{env["STATUS_LINE"]}.</p>
    <div class="cta"><a class="primary" href="/handbook/">Read the handbook</a><a href="https://github.com/{org}/catalog">The catalog</a></div>
  </div>
  <img src="/assets/ledger.png" alt="The {name} ledger: five slabs, each wider than the one above" width="1000" height="1000">
</section>

{state_section(st, repos, shipped)}

<section>
  <h2>Start here</h2>
  <div class="start">
    <a href="/handbook/"><b>New to the suite</b><span>How it is organized: rings, layers, waves, the contracts every repository signs.</span></a>
    <a href="/handbook/contributing.html"><b>Want to build</b><span><code>cargo install {cli}</code> then <code>{cli} suite pull</code>. Rust {env["MSRV"]}, edition {env["EDITION"]}.</span></a>
    <a href="https://github.com/search?q=org%3A{org}+label%3A%22good+first+issue%22+state%3Aopen&type=issues"><b>Want to help</b><span>Good first issues across every repository, and the open RFCs.</span></a>
  </div>
</section>

<section id="suite">
  <h2>The suite</h2>
  <p class="sub">Every repository, in its dependency ring. Dependencies only point inward. Each mark is the repository's own, drawn from what it is.</p>
  {rings_html}
</section>

<section>
  <h2>How we work</h2>
  <div class="how">
    <div><b>Spec-first cleanroom</b><p>Implement the standard, not the incumbent. Closed standards get a living spec and an executable conformance suite in <a href="https://github.com/{org}/specs">specs</a>.</p></div>
    <div><b>RFCs for anything that crosses a repository</b><p>Interfaces are WIT packages in <a href="https://github.com/{org}/interfaces">interfaces</a>; changing one is a proposal with a decision log.</p></div>
    <div><b>Signed off, signed, reviewed</b><p>DCO on every commit, signed commits and a linear history on <code>main</code>, one approving code-owner review; two in the platform ring.</p></div>
    <div><b>{env["LICENSE_SPDX"]}</b><p>Code under either licence; specs and content under {env["CONTENT_LICENSE_SPDX"]}. No CLA. GitHub is a mirror of our own forge.</p></div>
  </div>
</section>

<footer>
  <div>{name} · <a href="mailto:{env["ORG_EMAIL"]}">{env["ORG_EMAIL"]}</a> · <a href="/.well-known/security.txt">security.txt</a></div>
  <div><a href="https://github.com/{org}/.github/blob/main/CODE_OF_CONDUCT.md">Code of conduct</a> · <a href="https://github.com/{org}/.github/blob/main/CONTRIBUTING.md">Contributing</a> · <a href="https://github.com/{org}/{env["DOCS_REPO"]}">Site source</a></div>
</footer>
</div>
{STATE_JS}
</body>
</html>
"""


REPO_CSS = """
.crumbs { font-family:"JetBrains Mono", Menlo, monospace; font-size:13px; color:var(--muted); margin:6px 0 18px; }
.crumbs a { color:var(--muted); }
.rhero { display:grid; grid-template-columns:220px 1fr; gap:36px; align-items:center; padding:18px 0 40px; }
.rhero img { width:100%; height:auto; border-radius:14px; background:var(--paper); }
.rhero h1 { font-family:"JetBrains Mono", Menlo, monospace; font-size:clamp(30px, 4vw, 44px); letter-spacing:-1px; margin:0 0 10px; }
.ringtag { display:inline-flex; align-items:center; gap:8px; font-family:"JetBrains Mono", Menlo, monospace; font-size:12px; letter-spacing:0.6px; text-transform:uppercase; color:var(--muted); margin-bottom:10px; }
.ringtag i { width:12px; height:12px; border-radius:3px; display:inline-block; }
.facts { display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:12px; }
.fact { padding:14px 16px; border:1px solid var(--line); border-radius:12px; background:var(--paper); }
.fact b { display:block; font-family:"JetBrains Mono", Menlo, monospace; font-size:11px; letter-spacing:0.6px; text-transform:uppercase; color:var(--muted); margin-bottom:6px; }
.fact span { font-size:15px; }
ul.parts { columns:2; gap:32px; padding-left:20px; margin:0; } ul.parts li { margin:0 0 6px; break-inside:avoid; }
table.parts { border-collapse:collapse; width:100%; max-width:66ch; }
table.parts th, table.parts td { text-align:left; padding:8px 12px 8px 0; border-bottom:1px solid var(--line); }
table.parts th { font-family:"JetBrains Mono", Menlo, monospace; font-size:11px; letter-spacing:0.6px; text-transform:uppercase; color:var(--muted); font-weight:600; }
table.parts code { font-family:"JetBrains Mono", Menlo, monospace; font-size:13px; }
.links { display:flex; gap:12px; flex-wrap:wrap; }
.links a { padding:10px 16px; border:1.5px solid var(--blue); border-radius:8px; font-weight:700; }
.links a.primary { background:var(--blue); color:#fff; }
.siblings { display:flex; gap:10px; flex-wrap:wrap; }
.siblings a { display:inline-flex; align-items:center; gap:8px; padding:8px 12px; border:1px solid var(--line); border-radius:10px; color:var(--ink); font-family:"JetBrains Mono", Menlo, monospace; font-size:13px; }
.siblings svg { width:28px; height:28px; border-radius:6px; background:var(--paper); }
@media (max-width:720px) { .rhero { grid-template-columns:1fr; } ul.parts { columns:1; } }
"""


def components_html(env: dict, name: str, parts: Components) -> str:
    """The shipped components of one repository: a table, or the honest sentence when there are none or it is unknown."""
    if parts is None:
        return '<p class="sub">This repository\'s <code>CATALOG.toml</code> could not be read when the site was built, so what it publishes is unknown.</p>'
    if not parts:
        return f'<p class="sub">No crate yet. The first release train is {env["FIRST_TRAIN"]}.</p>'
    rows = "".join(
        f'<tr><td><a href="https://github.com/{env["ORG"]}/{name}/tree/main/crates/{p["crate"]}"><code>{p["crate"]}</code></a></td>'
        f'<td>{p["kind"]}</td><td>{p["readiness"]}</td></tr>'
        for p in parts
    )
    return (f'<p class="sub">What this repository publishes, from its own <code>CATALOG.toml</code>.</p>'
            f'<table class="parts"><thead><tr><th>Crate</th><th>Kind</th><th>Readiness</th></tr></thead><tbody>{rows}</tbody></table>')


def repo_page(env: dict, repo: dict, repos: list[dict], shipped: Components) -> str:
    org, name = env["ORG"], repo["name"]
    ring = repo["ring"]
    ring_title = next(t for k, t, _ in RINGS if k == ring)
    parts = [p.strip() for p in repo["contents"].split("·") if p.strip()]
    siblings = [r for r in repos if r["ring"] == ring and r["name"] != name]
    sib_html = "".join(f'<a href="/{r["name"]}/">{transparent(contour_mark(r, "paper"))}{r["name"]}</a>' for r in siblings)
    layers = ", ".join(repo["layers"])
    why = METAPHORS[name]["why"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} · {env["ORG_DISPLAY_NAME"]}</title>
<meta name="description" content="{repo["purpose"]}">
<meta property="og:title" content="{org}/{name}">
<meta property="og:description" content="{repo["purpose"]}">
<meta property="og:image" content="{env["ORG_URL"]}/assets/social.png">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap">
<style>{CSS}{REPO_CSS}</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <a class="brand" href="/"><img src="/favicon.svg" alt="">{env["ORG_DISPLAY_NAME"]}</a>
  <nav><a href="/handbook/">Handbook</a><a href="/#suite">The suite</a><a href="https://github.com/{org}/rfcs/pulls">RFCs</a><a href="https://github.com/{org}">GitHub</a></nav>
</header>
<div class="crumbs"><a href="/">{env["ORG_DISPLAY_NAME"]}</a> / <a href="/#suite">{ring_title.lower()} ring</a> / {name}</div>

<section class="rhero" style="border-top:0">
  <img src="/assets/marks/{name}.png" alt="The {name} mark: {why.lower().rstrip('.')}" width="512" height="512">
  <div>
    <div class="ringtag"><i style="background:{RING_COLORS[ring]}"></i>{ring_title} ring</div>
    <h1>{name}</h1>
    <p class="lede">{repo["purpose"]}</p>
    <div class="links"><a class="primary" href="https://github.com/{org}/{name}">Repository</a><a href="https://github.com/{org}/{name}/issues">Issues</a><a href="https://github.com/{org}/{name}/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22">Good first issues</a></div>
  </div>
</section>

<section>
  <div class="facts">
    <div class="fact"><b>Layers</b><span>{layers}</span></div>
    <div class="fact"><b>Wave</b><span>{repo["wave"]}</span></div>
    <div class="fact"><b>Tier</b><span>incubating</span></div>
    <div class="fact"><b>Readiness</b><span>{repo_readiness(shipped)}</span></div>
    <div class="fact"><b>Maintainers</b><span><a href="https://github.com/orgs/{org}/teams/maint-{name}">maint-{name}</a></span></div>
    <div class="fact"><b>Licence</b><span>{env["LICENSE_SPDX"]}</span></div>
  </div>
</section>

<section>
  <h2>Components</h2>
  {components_html(env, name, shipped)}
</section>

<section>
  <h2>Planned components</h2>
  <p class="sub">What this repository will contain, from the catalog.</p>
  <ul class="parts">{"".join(f"<li>{p}</li>" for p in parts)}</ul>
</section>

<section>
  <h2>The mark</h2>
  <p class="sub">{why} Every repository's mark is built from the same parts, in the colour of its ring.</p>
</section>

<section>
  <h2>Also in the {ring_title.lower()} ring</h2>
  <p class="sub">{next(b for k, _, b in RINGS if k == ring).capitalize()}.</p>
  <div class="siblings">{sib_html}</div>
</section>

<footer>
  <div>{env["ORG_DISPLAY_NAME"]} · <a href="mailto:{env["ORG_EMAIL"]}">{env["ORG_EMAIL"]}</a> · <a href="/.well-known/security.txt">security.txt</a></div>
  <div><a href="/handbook/">Handbook</a> · <a href="https://github.com/{org}/.github/blob/main/CONTRIBUTING.md">Contributing</a> · <a href="https://github.com/{org}/{env["DOCS_REPO"]}">Site source</a></div>
</footer>
</div>
</body>
</html>
"""


def suite_md(env: dict, repos: list[dict], shipped: dict[str, Components]) -> str:
    out = ["# The suite", "",
           f"The [state map]({env['ORG_URL']}/#state) on the site shows every repository as one tile in its ring and layer, coloured by "
           f"readiness, with the same data behind it as [state.json]({env['ORG_URL']}/state.json).", "",
           "Every repository in the organization, by dependency ring. Generated from the catalog; the readiness column is the highest "
           "readiness among the components each repository's own `CATALOG.toml` lists, read when the site was built.", ""]
    for key, title, blurb in RINGS:
        out += [f"## {title}", "", f"{blurb.capitalize()}.", "", "| Repository | Purpose | Layers | Wave | Contents | Readiness |", "|---|---|---|---|---|---|"]
        for r in repos:
            if r["ring"] == key:
                out.append(f"| [{r['name']}](https://github.com/{env['ORG']}/{r['name']}) | {r['purpose']} | {', '.join(r['layers'])} | "
                           f"{r['wave']} | {r['contents']} | {repo_readiness(shipped.get(r['name']))} |")
        out.append("")
    return "\n".join(out)


def security_txt(env: dict) -> str:
    expires = (date.today() + timedelta(days=365)).isoformat() + "T00:00:00.000Z"
    return (f"Contact: mailto:security@{env['DOMAIN']}\nContact: https://github.com/{env['ORG']}/.github/security/policy\n"
            f"Expires: {expires}\nPreferred-Languages: en\nCanonical: {env['ORG_URL']}/.well-known/security.txt\n"
            f"Policy: https://github.com/{env['ORG']}/.github/blob/main/SECURITY.md\n")


def wasm_pkg_registry(env: dict) -> str:
    """The wkg namespace map (RFC-0002): <WIT_NAMESPACE>:<name>@<v> is ghcr.io/<org>/<WIT_NAMESPACE>/<name>:<v>,
    so `wkg get` resolves the organization's WIT packages with no client configuration."""
    return json.dumps({"ociRegistry": "ghcr.io", "ociNamespacePrefix": f"{env['ORG']}/"}, indent=2) + "\n"


def served_schema(env: dict, catalog_dir: Path) -> str:
    """The catalog's catalog.schema.json, byte for byte, served at the site root: that URL is the schema's $id, so
    the build refuses a schema whose $id is not where the site would serve it."""
    text = (catalog_dir / "catalog.schema.json").read_text()
    declared, served = json.loads(text).get("$id"), f"{env['ORG_URL']}/catalog.schema.json"
    if declared != served:
        raise ValueError(f"catalog.schema.json declares $id {declared!r}, but the site serves it at {served}")
    return text


HANDBOOK_PAGES = [   # (file, title, one line for llms.txt)
    ("", "Introduction", "how the suite is organized: rings, layers, waves, the contracts every repository signs, and its status"),
    ("suite.html", "The suite", "every repository by dependency ring, with what its CATALOG.toml says has shipped"),
    ("how-we-work.html", "How we work", "the catalog, the RFC process, the WIT packages, the CI contract, the branch rules"),
    ("contributing.html", "Contributing", "the toolchain, the review rubric, what CI proves, the provenance trailer"),
    ("glossary.html", "Glossary", "the words the handbook uses"),
]


def llms_txt(env: dict, repos: list[dict]) -> str:
    """The agent-facing map of the site (llmstxt.org): an H1, a blockquote summary, then H2 sections of links."""
    url, org = env["ORG_URL"], env["ORG"]
    lines = [f"# {env['ORG_DISPLAY_NAME']}", "",
             f"> {env['ORG_DESCRIPTION']} {len(repos)} repositories that sign the same contracts, in five dependency rings; "
             f"spec-first, cleanroom, held in public. {env['STATUS_LINE']}.", "",
             "## Handbook", ""]
    lines += [f"- [{title}]({url}/handbook/{page}): {note}" for page, title, note in HANDBOOK_PAGES]
    lines += ["", "## The catalog and the source", "",
              f"- [catalog.toml](https://github.com/{org}/catalog/blob/main/catalog/catalog.toml): the source of truth: every repository, its ring, layers, wave, purpose and planned contents",
              f"- [catalog.schema.json]({url}/catalog.schema.json): the JSON Schema (2020-12) the catalog validates against",
              f"- [state.json]({url}/state.json): the state of the initiative, rebuilt nightly: the build date, the status line, per repository "
              f"its ring, wave, layers, readiness and components, and per wave how many repositories have a first crate",
              f"- [Site source](https://github.com/{org}/{env['DOCS_REPO']}): site/build.py, the handbook and the Pages workflow that builds this site",
              f"- [RFCs](https://github.com/{org}/rfcs): every decision that crosses a repository, with its decision record"]
    for key, title, blurb in RINGS:
        lines += ["", f"## {title} ring: {blurb}", ""]
        lines += [f"- [{r['name']}]({url}/{r['name']}/): {r['purpose']}" for r in repos if r["ring"] == key]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- build

def build(env: dict, catalog_dir: Path, brand: Path, repos_dir: Path | None, out: Path) -> Path:
    """<out>/www: every page and asset the site serves; <out>/handbook: the mdBook source mdbook builds into www/handbook."""
    load_brand(brand)
    repos = load_catalog(catalog_dir)
    shipped = components(env, repos, repos_dir)
    st = state(repos, shipped, date.today().isoformat())
    env["STATUS_LINE"] = st["status"]
    if out.exists():
        shutil.rmtree(out)
    www = out / "www"
    (www / "assets" / "marks").mkdir(parents=True)
    (www / ".well-known").mkdir(parents=True)
    (www / "index.html").write_text(landing(env, repos, st, shipped))
    (www / "state.json").write_text(json.dumps(st, indent=1) + "\n")
    (www / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {env['ORG_URL']}/sitemap.txt\n")
    (www / "sitemap.txt").write_text("".join(f"{env['ORG_URL']}/{p}\n" for p in ["", "handbook/", "llms.txt", "state.json"] + [f"{r['name']}/" for r in repos]))
    (www / "llms.txt").write_text(llms_txt(env, repos))
    (www / ".well-known" / "security.txt").write_text(security_txt(env))
    (www / ".well-known" / "wasm-pkg").mkdir()
    (www / ".well-known" / "wasm-pkg" / "registry.json").write_text(wasm_pkg_registry(env))
    (www / "catalog.schema.json").write_text(served_schema(env, catalog_dir))
    (www / "favicon.svg").write_text(transparent(contour_mark(ORG, "paper")) + "\n")
    for f in ("ledger.png", "social-preview.png", "mark-460.png"):
        shutil.copy(brand / f, www / "assets" / ("social.png" if f == "social-preview.png" else f))
    for r in repos:
        (www / "assets" / "marks" / f"{r['name']}.svg").write_text(transparent(contour_mark(r, "paper")) + "\n")
        shutil.copy(brand / "repos" / f"{r['name']}.png", www / "assets" / "marks" / f"{r['name']}.png")
        (www / r["name"]).mkdir()
        (www / r["name"] / "index.html").write_text(repo_page(env, r, repos, shipped[r["name"]]))
    book = out / "handbook"
    (book / "src").mkdir(parents=True)
    for f in HERE.glob("handbook/*"):
        if f.is_file():
            (book / f.name).write_text(render(f.read_text(), env))
    for f in HERE.glob("handbook/src/*.md"):
        (book / "src" / f.name).write_text(render(f.read_text(), env))
    (book / "src" / "suite.md").write_text(suite_md(env, repos, shipped))
    print(f"  ✓ site built in {out} ({len(repos)} repositories; {env['STATUS_LINE']})")
    return out


def main(argv: list[str]) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["build", "status", "readiness"])
    ap.add_argument("--catalog-dir", type=Path, metavar="DIR", required=True, help="the directory holding catalog.toml and catalog.schema.json")
    ap.add_argument("--org-env", type=Path, metavar="FILE", default=HERE / "org.env", help="the organization values (default: org.env next to this file)")
    ap.add_argument("--brand", type=Path, metavar="DIR", default=HERE / "brand", help="the vendored brand modules and PNGs (default: brand/ next to this file)")
    ap.add_argument("--lock", type=Path, metavar="FILE", default=HERE / "catalog.lock", help="the catalog lock `build` checks the catalog against (default: catalog.lock next to this file)")
    ap.add_argument("--repos", type=Path, metavar="DIR", help="read each repository's CATALOG.toml from the checkout <DIR>/<name> instead of gh api")
    ap.add_argument("--out", type=Path, metavar="DIR", default=DEFAULT_OUT, help=f"where `build` writes (default: {DEFAULT_OUT})")
    a = ap.parse_args(argv)
    env = org_env(a.org_env)
    if a.command == "status":
        print(status_line(components(env, load_catalog(a.catalog_dir), a.repos), date.today().isoformat()))
    elif a.command == "readiness":
        for name, parts in components(env, load_catalog(a.catalog_dir), a.repos).items():
            print(f"{name}\t{repo_readiness(parts)}")
    else:
        check_lock(a.catalog_dir, a.lock)
        build(env, a.catalog_dir, a.brand, a.repos, a.out)


if __name__ == "__main__":
    main(sys.argv[1:])
