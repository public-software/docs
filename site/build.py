#!/usr/bin/env python3
"""The public site: a landing page in the identity, one page per repository and the mdBook handbook,
built and deployed by this repository's Pages workflow (.github/workflows/pages.yml).

  python3 site/build.py build  --catalog-dir DIR [--repos DIR] [--activity FILE] [--history DIR] [--out DIR]   # → <out>/www/ (the pages) and <out>/handbook/ (mdBook source)
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
                     "components": [{"crate": "pub-kernel-core", "kind": "lib", "readiness": "partial"}, ...],
                     "activity": {"pushed_at": "2026-09-01T08:38:21Z", "open_issues": 3, "open_prs": 1,
                                  "good_first_issues": 2, "latest_release": "v0.1.0", "stars": 12}},
                    ...]}                      # components: [] for no crate yet, null for unknown;
                                               # activity: GitHub at build time (one GraphQL query per batch of
                                               # repositories through gh, or --activity FILE offline), null when unread

and state/history.json, the series the landing page's burn-up is drawn from. The Pages workflow keeps one state.json
per day as history/YYYY-MM-DD.json on the `state` branch of this repository (unguarded by the rulesets, so no bypass
actor); --history DIR reads that directory and today's build is the last point:

  {"since": "YYYY-MM-DD", "as_of": "YYYY-MM-DD", "days": 3,   # days: recorded days, today included
   "repositories": 57,                                        # the suite's size at the last point
   "points": [{"date": "YYYY-MM-DD", "repositories": 57, "with_crate": 9,
               "readiness": {"none": 0, "seed": 4, "partial": 5, "shipped": 0},   # the repositories with a first crate, by readiness
               "waves": {"1": {"repositories": 42, "with_crate": 7}, ...}}, ...]}
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


# ---------------------------------------------------------------- activity: what GitHub says is happening in each repository

Activity = dict | None                               # None: GitHub could not be read
ACTIVITY_BATCH = 25                                  # repositories per GraphQL query (one point each; 5,000 an hour)
GOOD_FIRST_ISSUE = "good first issue"
ACTIVITY_FIELDS = ("pushedAt stargazerCount issues(states: OPEN) { totalCount } pullRequests(states: OPEN) { totalCount } "
                   f'gfi: issues(states: OPEN, labels: ["{GOOD_FIRST_ISSUE}"]) {{ totalCount }} latestRelease {{ tagName }}')


def activity_query(org: str, names: list[str]) -> str:
    """One GraphQL query with an alias per repository (names come from the validated catalog)."""
    return "{ " + " ".join(f'r{i}: repository(owner: "{org}", name: "{n}") {{ {ACTIVITY_FIELDS} }}' for i, n in enumerate(names)) + " }"


def parse_activity(node: dict | None) -> Activity:
    """The repository node of the query into the state.json shape; None for a missing repository."""
    if not isinstance(node, dict):
        return None
    release = node.get("latestRelease") or {}
    return {"pushed_at": node.get("pushedAt"), "open_issues": node["issues"]["totalCount"], "open_prs": node["pullRequests"]["totalCount"],
            "good_first_issues": node["gfi"]["totalCount"], "latest_release": release.get("tagName"), "stars": node.get("stargazerCount", 0)}


def fetch_activity(org: str, names: list[str]) -> dict[str, Activity]:
    """One batch through `gh api graphql`; every repository of a failed query is None."""
    r = subprocess.run(["gh", "api", "graphql", "-f", f"query={activity_query(org, names)}"], capture_output=True, text=True)
    if r.returncode != 0:
        return {n: None for n in names}
    try:
        data = json.loads(r.stdout).get("data") or {}
    except ValueError:
        return {n: None for n in names}
    return {n: parse_activity(data.get(f"r{i}")) for i, n in enumerate(names)}


def activity(env: dict, repos: list[dict], activity_file: Path | None) -> dict[str, Activity]:
    """name → activity, from --activity FILE (offline) or from GitHub in batches; missing entries are None."""
    names = [r["name"] for r in repos]
    if activity_file is not None:
        known = json.loads(activity_file.read_text())
        return {n: known.get(n) for n in names}
    out: dict[str, Activity] = {}
    for i in range(0, len(names), ACTIVITY_BATCH):
        out.update(fetch_activity(env["ORG"], names[i:i + ACTIVITY_BATCH]))
    return out


# ---------------------------------------------------------------- state: state.json and the map the landing page draws from it

def state(repos: list[dict], shipped: dict[str, Components], acts: dict[str, Activity], as_of: str) -> dict:
    """The site's machine-readable state (the shape is in the module docstring)."""
    waves: dict[str, dict] = {}
    for r in repos:
        w = waves.setdefault(str(r["wave"]), {"repositories": 0, "with_crate": 0})
        w["repositories"] += 1
        w["with_crate"] += 1 if shipped[r["name"]] else 0
    entries = [{"name": r["name"], "ring": r["ring"], "wave": r["wave"], "layers": r["layers"], "readiness": repo_readiness(shipped[r["name"]]),
                "components": shipped[r["name"]], "activity": acts.get(r["name"])} for r in repos]
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


# ---------------------------------------------------------------- history: one state.json per day, the series and the burn-up

HISTORY_JSON = "state/history.json"
STACK_ORDER = ["shipped", "partial", "seed", "none"]   # the areas, bottom to top: what has shipped carries the rest
WAVE_DASHES = ["", "6 3", "2 3", "8 3 2 3", "1 3"]    # one stroke pattern per wave, so the lines need no colour
BURNUP_W, BURNUP_H = 720, 240
BURNUP_PAD = {"left": 44, "right": 76, "top": 14, "bottom": 30}
LABEL_GAP = 12                                        # the least distance between two wave labels, in SVG units


def history_point(st: dict) -> dict:
    """One point of the series from one day's state.json: the repositories with a first crate, by readiness and per wave."""
    by_readiness = {r: 0 for r in READINESS}
    waves: dict[str, dict] = {}
    for e in st["repositories"]:
        w = waves.setdefault(str(e["wave"]), {"repositories": 0, "with_crate": 0})
        w["repositories"] += 1
        if e.get("components"):                       # a first crate, as state() counts it
            w["with_crate"] += 1
            by_readiness[e["readiness"]] = by_readiness.get(e["readiness"], 0) + 1
    return {"date": st["as_of"], "repositories": len(st["repositories"]), "with_crate": sum(by_readiness.values()),
            "readiness": by_readiness, "waves": dict(sorted(waves.items()))}


def history(history_dir: Path | None, st: dict) -> dict:
    """The series served at state/history.json: every recorded day under --history DIR, then today's build (which replaces a record of the same day)."""
    points: dict[str, dict] = {}
    for f in sorted(history_dir.glob("*.json")) if history_dir is not None and history_dir.is_dir() else []:
        try:
            day = json.loads(f.read_text())
            points[day["as_of"]] = history_point(day)
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"  ! {f}: not a state.json ({e}), left out of the series", file=sys.stderr)
    points[st["as_of"]] = history_point(st)
    series = [points[d] for d in sorted(points)]
    return {"since": series[0]["date"], "as_of": st["as_of"], "days": len(series), "repositories": series[-1]["repositories"], "points": series}


def burnup_axes(hist: dict) -> tuple:
    """The x and y scales of the chart: calendar days since the first point (one point sits in the middle), 0 to every repository."""
    pts = hist["points"]
    n_total = max(hist["repositories"], 1)
    first = date.fromisoformat(pts[0]["date"])
    span = max((date.fromisoformat(pts[-1]["date"]) - first).days, 1)
    x0, x1 = BURNUP_PAD["left"], BURNUP_W - BURNUP_PAD["right"]
    y0, y1 = BURNUP_H - BURNUP_PAD["bottom"], BURNUP_PAD["top"]
    if len(pts) == 1:
        return (lambda d: (x0 + x1) / 2), (lambda v: y0 - v / n_total * (y0 - y1)), n_total
    return (lambda d: x0 + (date.fromisoformat(d) - first).days / span * (x1 - x0)), (lambda v: y0 - v / n_total * (y0 - y1)), n_total


def burnup_areas(pts: list[dict], x, y) -> str:
    """The whole suite by readiness, stacked: polygons over several days, one stacked bar over a single day."""
    out, lower = "", [0] * len(pts)
    for k in STACK_ORDER:
        upper = [lo + p["readiness"].get(k, 0) for lo, p in zip(lower, pts)]
        if len(pts) == 1:
            cx = x(pts[0]["date"])
            out += f'<rect class="area a-{k}" x="{cx - 9:.1f}" y="{y(upper[0]):.1f}" width="18" height="{y(lower[0]) - y(upper[0]):.1f}"/>'
        else:
            top = " ".join(f"{x(p['date']):.1f},{y(u):.1f}" for p, u in zip(pts, upper))
            bottom = " ".join(f"{x(p['date']):.1f},{y(lo):.1f}" for p, lo in zip(reversed(pts), reversed(lower)))
            out += f'<polygon class="area a-{k}" points="{top} {bottom}"><title>{k}: {upper[-1] - lower[-1]} at the last point</title></polygon>'
        lower = upper
    return out


def spread_labels(ys: list[float]) -> list[float]:
    """Wave labels at least LABEL_GAP apart: the lower ones are pushed down in the order they sit, so none covers another."""
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    placed, last = list(ys), None
    for i in order:
        placed[i] = ys[i] if last is None else max(ys[i], last + LABEL_GAP)
        last = placed[i]
    return placed


def burnup_waves(pts: list[dict], x, y) -> str:
    """One line per wave (a mark over a single day), each labelled at its right end."""
    waves = sorted({w for p in pts for w in p["waves"]}, key=int)
    values = [[p["waves"].get(w, {}).get("with_crate", 0) for p in pts] for w in waves]
    label_ys = spread_labels([y(v[-1]) for v in values])
    out, x_end = "", x(pts[-1]["date"])
    for i, (w, v) in enumerate(zip(waves, values)):
        dash = f' stroke-dasharray="{WAVE_DASHES[i % len(WAVE_DASHES)]}"' if WAVE_DASHES[i % len(WAVE_DASHES)] else ""
        if len(pts) == 1:
            out += f'<circle class="wave wave-{w}" cx="{x_end:.1f}" cy="{y(v[0]):.1f}" r="3.5"/>'
        else:
            line = " ".join(f"{x(p['date']):.1f},{y(n):.1f}" for p, n in zip(pts, v))
            out += f'<polyline class="wave wave-{w}" points="{line}"{dash}/>'
        out += f'<text class="lbl" x="{x_end + 8:.1f}" y="{label_ys[i] + 3.5:.1f}">wave {w}: {v[-1]}</text>'
    return out


def burnup_svg(hist: dict) -> str:
    """The burn-up: x calendar days, y repositories with a first crate; the areas the whole suite by readiness, the lines one per wave."""
    pts = hist["points"]
    x, y, n_total = burnup_axes(hist)
    x0, x1, y0 = BURNUP_PAD["left"], BURNUP_W - BURNUP_PAD["right"], BURNUP_H - BURNUP_PAD["bottom"]
    grid = "".join(f'<line class="grid" x1="{x0}" y1="{y(v):.1f}" x2="{x1}" y2="{y(v):.1f}"/><text class="lbl" x="{x0 - 6}" y="{y(v) + 3.5:.1f}" text-anchor="end">{v}</text>'
                   for v in sorted({0, n_total // 2}))
    scope = f'<line class="scope" x1="{x0}" y1="{y(n_total):.1f}" x2="{x1}" y2="{y(n_total):.1f}"/><text class="lbl" x="{x0}" y="{y(n_total) - 5:.1f}">{n_total} repositories</text>'
    if len(pts) == 1:                                 # the mark sits mid-axis with its labels; the date goes where the axis starts
        dates = f'<text class="lbl" x="{x0}" y="{y0 + 16}">{pts[0]["date"]}</text>'
    else:
        dates = (f'<text class="lbl" x="{x0}" y="{y0 + 16}">{pts[0]["date"]}</text>'
                 f'<text class="lbl" x="{x1}" y="{y0 + 16}" text-anchor="end">{pts[-1]["date"]}</text>')
    return (f'<svg class="burnup" role="img" viewBox="0 0 {BURNUP_W} {BURNUP_H}" aria-labelledby="burnup-title burnup-desc">'
            f'<title id="burnup-title">Repositories with a first crate, {hist["since"]} to {hist["as_of"]}</title>'
            f'<desc id="burnup-desc">Stacked areas: the whole suite by readiness (shipped, partial, seed, none). Lines: one per wave. '
            f'Dashed line: every repository, {n_total}. Last point: {pts[-1]["with_crate"]} of {pts[-1]["repositories"]}.</desc>'
            f'{grid}{scope}{burnup_areas(pts, x, y)}{burnup_waves(pts, x, y)}{dates}</svg>')


def history_caption(env: dict, hist: dict) -> str:
    """Under the chart: since when, how many recorded days, from → to; where the series and its record live."""
    pts, docs = hist["points"], env["DOCS_REPO"]
    if len(pts) == 1:
        lead = f'History starts today ({hist["as_of"]}): one point, {pts[0]["with_crate"]} of {pts[0]["repositories"]} repositories with a first crate.'
    else:
        lead = f'Since {hist["since"]}: {hist["days"]} recorded days, {pts[0]["with_crate"]} → {pts[-1]["with_crate"]} repositories with a first crate.'
    return (f'<p class="since">{lead} Areas: the whole suite by readiness. Lines: one per wave. The series is <a href="/{HISTORY_JSON}">{HISTORY_JSON}</a>, '
            f'one point per day, kept under <code>history/</code> on the <code>state</code> branch of the '
            f'<a href="https://github.com/{env["ORG"]}/{docs}/tree/state">{docs} repository</a>.</p>')


HISTORY_CSS = """
.history { margin-top:30px; } .history h3 { font-size:17px; font-weight:700; letter-spacing:-0.2px; margin:0 0 10px; }
.burnup { display:block; width:100%; height:auto; font-family:"JetBrains Mono", Menlo, monospace; }
.burnup .area { stroke:none; } .burnup .a-shipped { fill:var(--blue); } .burnup .a-partial { fill:var(--partial); } .burnup .a-seed { fill:var(--seed); } .burnup .a-none { fill:var(--line); }
.burnup .wave { fill:none; stroke:var(--ink); stroke-width:1.6; stroke-linejoin:round; stroke-linecap:round; } .burnup circle.wave { fill:var(--ink); stroke:none; }
.burnup .grid { stroke:var(--line); stroke-width:1; } .burnup .scope { stroke:var(--muted); stroke-width:1; stroke-dasharray:4 4; }
.burnup .lbl { fill:var(--muted); font-size:10.5px; }
.since { font-family:"JetBrains Mono", Menlo, monospace; font-size:12.5px; color:var(--muted); margin:8px 0 0; }
"""


def history_section(env: dict, hist: dict) -> str:
    """The 'Progress over time' block of the state section: the burn-up and its caption."""
    return f'<div class="history">\n  <h3 id="history">Progress over time</h3>\n  {burnup_svg(hist)}\n  {history_caption(env, hist)}\n</div>'


def state_section(env: dict, st: dict, repos: list[dict], shipped: dict[str, Components], hist: dict) -> str:
    """The landing page's state section: the verdict, one bar per wave, the wave filter and legend, the ledger, the detail box, the burn-up."""
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
{history_section(env, hist)}
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


def landing(env: dict, repos: list[dict], st: dict, shipped: dict[str, Components], hist: dict) -> str:
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
<style>{CSS}{STATE_CSS}{HISTORY_CSS}</style>
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

{state_section(env, st, repos, shipped, hist)}

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
.hchips { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin:0 0 16px; font-family:"JetBrains Mono", Menlo, monospace; font-size:12px; color:var(--muted); }
.chip { display:inline-flex; align-items:center; gap:8px; padding:4px 10px; border-radius:6px; border:1px solid transparent; font-family:"JetBrains Mono", Menlo, monospace; font-size:12.5px; font-weight:600; color:var(--ink); }
.chip code { font-size:12.5px; } .chip span { font-weight:400; opacity:0.85; }
.chip span::before { content:"·"; margin-right:8px; }
.chips { display:flex; gap:8px; flex-wrap:wrap; }
.strip { display:grid; grid-template-columns:repeat(19, 1fr); gap:3px; margin:0 0 6px; }
.lyr { height:34px; border-radius:5px; background:var(--paper); border:1px solid var(--line); font-family:"JetBrains Mono", Menlo, monospace; font-size:10px; color:var(--muted); display:flex; align-items:center; justify-content:center; }
.lyr.on { background:var(--ring); border-color:var(--ring); color:#fff; font-weight:600; }
.bands { display:grid; grid-template-columns:repeat(19, 1fr); gap:3px; margin:0 0 18px; font-family:"JetBrains Mono", Menlo, monospace; font-size:10px; letter-spacing:0.5px; text-transform:uppercase; color:var(--muted); }
.bands span { text-align:center; border-top:2px solid var(--line); padding-top:4px; }
.rings { display:flex; gap:8px; flex-wrap:wrap; margin:0 0 14px; }
.pill { display:inline-flex; align-items:center; gap:8px; padding:5px 12px; border-radius:999px; border:1px solid var(--line); font-family:"JetBrains Mono", Menlo, monospace; font-size:12px; color:var(--muted); }
.pill::before { content:""; width:10px; height:10px; border-radius:3px; background:var(--ring); }
.pill.on { background:var(--ring); border-color:var(--ring); color:#fff; font-weight:600; } .pill.on::before { background:#fff; }
.pill:hover { text-decoration:none; border-color:var(--ring); }
.peers { display:flex; gap:6px; flex-wrap:wrap; }
ul.plan { list-style:none; padding:0; margin:0; columns:2; gap:32px; } ul.plan li { margin:0 0 8px; padding-left:26px; position:relative; break-inside:avoid; color:var(--muted); }
ul.plan li::before { content:""; position:absolute; left:0; top:4px; width:14px; height:14px; border-radius:4px; border:1.5px dashed var(--line); }
ul.plan li.done { color:var(--ink); } ul.plan li.done::before { border:0; background:var(--blue); }
ul.plan li.done::after { content:""; position:absolute; left:4.5px; top:6px; width:4px; height:8px; border:solid #fff; border-width:0 2px 2px 0; transform:rotate(45deg); }
@media (max-width:720px) { .rhero { grid-template-columns:1fr; } ul.parts, ul.plan { columns:1; } .lyr { font-size:0; height:14px; } .bands { font-size:0; } }
"""


def band_of(layer: str) -> str:
    """The brand's band a layer belongs to (silicon, system, platform, apps, content)."""
    return next(b for first, b in reversed(BANDS.items()) if int(layer[1:]) >= int(first[1:]))


def ledger_strip(repo: dict) -> str:
    """The 19 layers as a strip, lit in the ring colour for the ones this repository serves ('all' lights every one)."""
    lit = set(LAYERS) if ALL_LAYERS in repo["layers"] else set(repo["layers"])
    cells = "".join(f'<span class="lyr{" on" if layer in lit else ""}" title="{layer} · {band_of(layer)}">{layer}</span>' for layer in LAYERS)
    firsts = list(BANDS) + ["L19"]
    bands = "".join(f'<span style="grid-column:span {int(firsts[i + 1][1:]) - int(f[1:])}">{b}</span>' for i, (f, b) in enumerate(BANDS.items()))
    return f'<div class="strip" style="--ring:{RING_COLORS[repo["ring"]]}">{cells}</div><div class="bands">{bands}</div>'


def ring_pills(ring: str) -> str:
    """The five rings as pills, this repository's filled."""
    return '<div class="rings">' + "".join(
        f'<a class="pill{" on" if k == ring else ""}" style="--ring:{RING_COLORS[k]}" href="/#suite">{t}</a>' for k, t, _ in RINGS) + "</div>"


def layer_peers(repo: dict, repos: list[dict]) -> list[dict]:
    """The other repositories sharing a layer: for an 'all' repository the other 'all' repositories, else any overlap."""
    mine = set(repo["layers"])
    if ALL_LAYERS in mine:
        return [r for r in repos if r["name"] != repo["name"] and ALL_LAYERS in r["layers"]]
    return [r for r in repos if r["name"] != repo["name"] and mine & set(r["layers"])]


def days_ago(pushed_at: str, today: date) -> str:
    """'today', 'yesterday' or 'N days ago' for an ISO timestamp."""
    n = (today - date.fromisoformat(pushed_at[:10])).days
    return "today" if n == 0 else "yesterday" if n == 1 else f"{n} days ago"


def activity_html(env: dict, name: str, act: Activity, as_of: str) -> str:
    """What GitHub says is happening in the repository, or the honest sentence when it could not be read."""
    if act is None:
        return "<p class=\"sub\">GitHub could not be read when the site was built, so its activity is unknown.</p>"
    gh = f"https://github.com/{env['ORG']}/{name}"
    pushed = f'{act["pushed_at"][:10]} ({days_ago(act["pushed_at"], date.fromisoformat(as_of))})' if act.get("pushed_at") else "never"
    release = f'<a href="{gh}/releases/latest">{act["latest_release"]}</a>' if act.get("latest_release") else "no release yet"
    return (f'<p class="sub">From GitHub, as of {as_of}. The nightly build refreshes it.</p><div class="facts">'
            f'<div class="fact"><b>Last push</b><span>{pushed}</span></div>'
            f'<div class="fact"><b>Open issues</b><span><a href="{gh}/issues">{act["open_issues"]}</a></span></div>'
            f'<div class="fact"><b>Open pull requests</b><span><a href="{gh}/pulls">{act["open_prs"]}</a></span></div>'
            f'<div class="fact"><b>Good first issues</b><span><a href="{gh}/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22">{act["good_first_issues"]}</a></span></div>'
            f'<div class="fact"><b>Latest release</b><span>{release}</span></div>'
            f'<div class="fact"><b>Stars</b><span>{act["stars"]}</span></div></div>')


def components_html(env: dict, name: str, parts: Components) -> str:
    """The shipped components of one repository as readiness chips, or the honest sentence when there are none or it is unknown."""
    if parts is None:
        return '<p class="sub">This repository\'s <code>CATALOG.toml</code> could not be read when the site was built, so what it publishes is unknown.</p>'
    if not parts:
        return f'<p class="sub">No crate yet. The first release train is {env["FIRST_TRAIN"]}.</p>'
    chips = "".join(
        f'<a class="chip r-{p["readiness"] if p["readiness"] in READINESS else UNKNOWN}" href="https://github.com/{env["ORG"]}/{name}/tree/main/crates/{p["crate"]}">'
        f'<code>{p["crate"]}</code><span>{p["kind"]}</span><span>{p["readiness"]}</span></a>'
        for p in parts
    )
    return f'<p class="sub">What this repository publishes, from its own <code>CATALOG.toml</code>.</p><div class="chips">{chips}</div>'


def part_shipped(part: str, parts: Components, tokens: list[str]) -> bool:
    """A planned part has a first crate when a component is named after its first word: exactly, or (for a hyphenated
    word such as pub-kernel) as the prefix of a crate no other planned part names exactly. A bare word such as `pub`
    never claims every pub-* crate."""
    token = part.split()[0].lower()
    crates = [p["crate"] for p in parts or []]
    if token in crates:
        return True
    return "-" in token and any(c.startswith(token + "-") and c not in tokens for c in crates)


def planned_html(repo: dict, parts: Components) -> str:
    """The catalog's planned contents as a checklist against what has shipped, with the count line."""
    planned = [p.strip() for p in repo["contents"].split("·") if p.strip()]
    tokens = [p.split()[0].lower() for p in planned]
    done = [part_shipped(p, parts, tokens) for p in planned]
    items = "".join(f'<li class="done">{p}</li>' if d else f"<li>{p}</li>" for p, d in zip(planned, done))
    return (f'<p class="sub">What this repository will contain, from the catalog: {sum(done)} of {len(planned)} planned parts have a first crate.</p>'
            f'<ul class="plan">{items}</ul>')


def repo_page(env: dict, repo: dict, repos: list[dict], shipped: dict[str, Components], acts: dict[str, Activity], as_of: str) -> str:
    org, name = env["ORG"], repo["name"]
    ring = repo["ring"]
    ring_title = next(t for k, t, _ in RINGS if k == ring)
    parts = shipped[name]
    readiness = repo_readiness(parts)
    siblings = [r for r in repos if r["ring"] == ring and r["name"] != name]
    sib_html = "".join(f'<a href="/{r["name"]}/">{transparent(contour_mark(r, "paper"))}{r["name"]}</a>' for r in siblings)
    peers_html = "".join(tile(r, shipped[r["name"]]) for r in layer_peers(repo, repos)) or "<span class=\"sub\">none</span>"
    layers = ", ".join(repo["layers"])
    serves = "every layer of the ledger" if ALL_LAYERS in repo["layers"] else f"layer{'s' if len(repo['layers']) > 1 else ''} {layers}"
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
<style>{CSS}{STATE_CSS}{REPO_CSS}</style>
</head>
<body>
<div class="wrap">
<header class="top">
  <a class="brand" href="/"><img src="/favicon.svg" alt="">{env["ORG_DISPLAY_NAME"]}</a>
  <nav><a href="/#state">State</a><a href="/handbook/">Handbook</a><a href="/#suite">The suite</a><a href="https://github.com/{org}/rfcs/pulls">RFCs</a><a href="https://github.com/{org}">GitHub</a></nav>
</header>
<div class="crumbs"><a href="/">{env["ORG_DISPLAY_NAME"]}</a> / <a href="/#suite">{ring_title.lower()} ring</a> / {name}</div>

<section class="rhero" style="border-top:0">
  <img src="/assets/marks/{name}.png" alt="The {name} mark: {why.lower().rstrip('.')}" width="512" height="512">
  <div>
    <div class="ringtag"><i style="background:{RING_COLORS[ring]}"></i>{ring_title} ring</div>
    <h1>{name}</h1>
    <p class="lede">{repo["purpose"]}</p>
    <div class="hchips"><span class="chip r-{"none" if readiness == NO_CRATE else readiness if readiness in READINESS else UNKNOWN}">{readiness}</span><span>wave {repo["wave"]} · {layers}</span><a href="/#state">on the map</a></div>
    <div class="links"><a class="primary" href="https://github.com/{org}/{name}">Repository</a><a href="https://github.com/{org}/{name}/issues">Issues</a><a href="https://github.com/{org}/{name}/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22">Good first issues</a></div>
  </div>
</section>

<section>
  <div class="facts">
    <div class="fact"><b>Layers</b><span>{layers}</span></div>
    <div class="fact"><b>Wave</b><span>{repo["wave"]}</span></div>
    <div class="fact"><b>Tier</b><span>incubating</span></div>
    <div class="fact"><b>Readiness</b><span>{readiness}</span></div>
    <div class="fact"><b>Maintainers</b><span><a href="https://github.com/orgs/{org}/teams/maint-{name}">maint-{name}</a></span></div>
    <div class="fact"><b>Licence</b><span>{env["LICENSE_SPDX"]}</span></div>
  </div>
</section>

<section>
  <h2>Where it sits</h2>
  <p class="sub">{name} serves {serves}, in the {ring_title.lower()} ring. Dependencies point inward only, and across rings only on the platform ring.</p>
  {ledger_strip(repo)}
  {ring_pills(ring)}
  <p class="sub">Shares a layer with, coloured by readiness as on <a href="/#state">the map</a>:</p>
  <div class="peers">{peers_html}</div>
</section>

<section>
  <h2>Activity</h2>
  {activity_html(env, name, acts.get(name), as_of)}
</section>

<section>
  <h2>Components</h2>
  {components_html(env, name, parts)}
</section>

<section>
  <h2>Planned components</h2>
  {planned_html(repo, parts)}
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
              f"- [state/history.json]({url}/{HISTORY_JSON}): the same over time: one point per recorded day (since, as_of, days; per point the repositories "
              f"with a first crate, by readiness and per wave), the series the landing page's burn-up is drawn from",
              f"- [Site source](https://github.com/{org}/{env['DOCS_REPO']}): site/build.py, the handbook and the Pages workflow that builds this site",
              f"- [RFCs](https://github.com/{org}/rfcs): every decision that crosses a repository, with its decision record"]
    for key, title, blurb in RINGS:
        lines += ["", f"## {title} ring: {blurb}", ""]
        lines += [f"- [{r['name']}]({url}/{r['name']}/): {r['purpose']}" for r in repos if r["ring"] == key]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- build

def build(env: dict, catalog_dir: Path, brand: Path, repos_dir: Path | None, activity_file: Path | None, history_dir: Path | None, out: Path) -> Path:
    """<out>/www: every page and asset the site serves; <out>/handbook: the mdBook source mdbook builds into www/handbook."""
    load_brand(brand)
    repos = load_catalog(catalog_dir)
    shipped = components(env, repos, repos_dir)
    acts = activity(env, repos, activity_file)
    st = state(repos, shipped, acts, date.today().isoformat())
    hist = history(history_dir, st)
    env["STATUS_LINE"] = st["status"]
    if out.exists():
        shutil.rmtree(out)
    www = out / "www"
    (www / "assets" / "marks").mkdir(parents=True)
    (www / ".well-known").mkdir(parents=True)
    (www / HISTORY_JSON).parent.mkdir(parents=True)
    (www / "index.html").write_text(landing(env, repos, st, shipped, hist))
    (www / "state.json").write_text(json.dumps(st, indent=1) + "\n")
    (www / HISTORY_JSON).write_text(json.dumps(hist, indent=1) + "\n")
    (www / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {env['ORG_URL']}/sitemap.txt\n")
    (www / "sitemap.txt").write_text("".join(f"{env['ORG_URL']}/{p}\n" for p in ["", "handbook/", "llms.txt", "state.json", HISTORY_JSON] + [f"{r['name']}/" for r in repos]))
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
        (www / r["name"] / "index.html").write_text(repo_page(env, r, repos, shipped, acts, st["as_of"]))
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
    ap.add_argument("--activity", type=Path, metavar="FILE", help="read each repository's GitHub activity from this JSON file (name → activity) instead of gh api graphql")
    ap.add_argument("--history", type=Path, metavar="DIR", help="the recorded days (one state.json per day, YYYY-MM-DD.json: the state branch's history/) the burn-up is drawn from; today alone without it")
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
        build(env, a.catalog_dir, a.brand, a.repos, a.activity, a.history, a.out)


if __name__ == "__main__":
    main(sys.argv[1:])
