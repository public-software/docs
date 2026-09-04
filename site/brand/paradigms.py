#!/usr/bin/env python3
"""Round 4 of the logo workshop: one object per repository, three projections.

  solid     isometric, three tones from the ring hue — the objects Blender will build
  contour   plan view, elevation as tone — a relief map
  sheets    plan view, translucent planes offset by height — layers

No container. The organization's object (the stepped ledger) is drawn in every
paradigm. Run to write brand/out/paradigms/.
"""
from __future__ import annotations

import json
import math
import tomllib
from pathlib import Path

from metaphors import METAPHORS
from objects import OBJECTS, ORG_OBJECT

KIT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).parent / "out" / "paradigms"
PAPER = "#F2F3F1"
INK = "#14181F"
RING_COLORS = {"spine": "#1F4E8C", "platform": "#157A72", "system": "#3D4F66", "domain": "#6B2D5C", "standards": "#8A6A1F"}
ORG = {"name": "public-software", "ring": "spine", "layers": ["all"]}


# ---------------------------------------------------------------- colour

def hex_rgb(h: str) -> tuple[float, float, float]:
    return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


def rgb_hex(r: float, g: float, b: float) -> str:
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(v * 255))) for v in (r, g, b))


def mix(a: str, b: str, t: float) -> str:
    ra, ga, ba = hex_rgb(a)
    rb, gb, bb = hex_rgb(b)
    return rgb_hex(ra + (rb - ra) * t, ga + (gb - ga) * t, ba + (bb - ba) * t)


def tones(color: str, on: str) -> dict[str, str]:
    """top / left / right face tones for the solid paradigm; a 5-step scale for contour."""
    if on == "ink":
        base = mix(color, "#FFFFFF", 0.25)
        return {"top": mix(base, "#FFFFFF", 0.45), "left": base, "right": mix(base, INK, 0.35)}
    return {"top": mix(color, "#FFFFFF", 0.42), "left": color, "right": mix(color, "#000000", 0.32)}


def scale(color: str, on: str, n: int = 6) -> list[str]:
    lo = mix(color, INK, 0.45) if on == "ink" else mix(color, PAPER, 0.62)
    hi = mix(color, "#FFFFFF", 0.55) if on == "ink" else color
    return [mix(lo, hi, i / (n - 1)) for i in range(n)]


def wrap(body: str, on: str) -> str:
    back = {"paper": PAPER, "ink": INK}[on]
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64"><rect width="64" height="64" fill="{back}"/>{body}</svg>'


def spec_for(repo: dict) -> list[dict]:
    return ORG_OBJECT if repo["name"] == ORG["name"] else OBJECTS[repo["name"]]


# ---------------------------------------------------------------- solid (isometric)

U = 3.6                      # screen units per floor unit
COS30, SIN30 = math.cos(math.radians(30)), 0.5


def iso(x: float, y: float, z: float) -> tuple[float, float]:
    return (x - y) * COS30 * U, (x + y) * SIN30 * U - z * U


def poly(points, fill: str) -> str:
    return f'<polygon points="{" ".join(f"{x:.2f},{y:.2f}" for x, y in points)}" fill="{fill}"/>'


def wedge_faces(prim: dict, tone: dict[str, str]) -> list[tuple[float, str]]:
    """A gable roof: two slopes and the front gable, painted like the prisms."""
    (x0, y0), (x1, _), (_, y1), _ = prim["pts"]
    z0, z1 = prim["z"], prim["z"] + prim["h"]
    ym = (y0 + y1) / 2
    faces = []
    # back slope (faces -y): hidden from the viewer at +y; front slope (faces +y): lit like a left face but flatter
    front = [iso(x0, y1, z0), iso(x1, y1, z0), iso(x1, ym, z1), iso(x0, ym, z1)]
    faces.append(((x0 + x1) / 2 + (ym + y1) / 2 + z0 + 0.02, poly(front, mix(tone["left"], tone["top"], 0.5))))
    gable = [iso(x1, y0, z0), iso(x1, y1, z0), iso(x1, ym, z1)]   # the +x gable faces the viewer's right
    faces.append((x1 + ym + z0 + 0.01, poly(gable, tone["right"])))
    return faces


def prism_faces(prim: dict, tone: dict[str, str]) -> list[tuple[float, str]]:
    """Visible faces of one prism as (depth, svg) so they can be painted far to near."""
    if prim["t"] == "wedge":
        return wedge_faces(prim, tone)
    pts = prim["pts"]
    z0, z1 = prim["z"], prim["z"] + prim["h"]
    faces = []
    n = len(pts)
    for i in range(n):
        (ax, ay), (bx, by) = pts[i], pts[(i + 1) % n]
        # outward normal of this plan edge (polygon is counter-clockwise in plan: x right, y down)
        nx, ny = (by - ay), -(bx - ax)
        if nx + ny <= 1e-9:
            continue  # faces the viewer only when its normal has a component toward +x/+y
        length = math.hypot(nx, ny)
        t = (nx / length - ny / length + 1) / 2   # 0 → faces left (+y), 1 → faces right (+x)
        fill = mix(tone["left"], tone["right"], t)
        quad = [iso(ax, ay, z0), iso(bx, by, z0), iso(bx, by, z1), iso(ax, ay, z1)]
        depth = (ax + bx) / 2 + (ay + by) / 2 + z0
        faces.append((depth, poly(quad, fill)))
    top = [iso(x, y, z1) for x, y in pts]
    cx = sum(p[0] for p in pts) / n
    cy = sum(p[1] for p in pts) / n
    faces.append((cx + cy + z1 + 0.01, poly(top, tone["top"])))
    return faces


def solid_mark(repo: dict, on: str = "paper") -> str:
    color = RING_COLORS[repo["ring"]]
    tone = tones(color, on)
    prims = spec_for(repo)
    faces = []
    for prim in sorted(prims, key=lambda p: (sum(x for x, _ in p["pts"]) + sum(y for _, y in p["pts"])) / len(p["pts"]) + p["z"]):
        faces += prism_faces(prim, tone)
    faces.sort(key=lambda f: f[0])
    # centre the drawing: bounding box of every projected vertex
    xs, ys = [], []
    for prim in prims:
        for x, y in prim["pts"]:
            for z in (prim["z"], prim["z"] + prim["h"]):
                px, py = iso(x, y, z)
                xs.append(px); ys.append(py)
    dx = 32 - (min(xs) + max(xs)) / 2
    dy = 32 - (min(ys) + max(ys)) / 2
    body = f'<g transform="translate({dx:.2f} {dy:.2f})">{"".join(svg for _, svg in faces)}</g>'
    return wrap(body, on)


# ---------------------------------------------------------------- contour (plan, elevation as tone)

PLAN_U = 6.4   # 8 floor units → 51.2 px
PLAN_O = (64 - 8 * PLAN_U) / 2


def plan(x: float, y: float) -> tuple[float, float]:
    return PLAN_O + x * PLAN_U, PLAN_O + y * PLAN_U


def contour_mark(repo: dict, on: str = "paper") -> str:
    color = RING_COLORS[repo["ring"]]
    steps = scale(color, on)
    prims = spec_for(repo)
    zmax = max(p["z"] + p["h"] for p in prims)
    body = ""
    for prim in sorted(prims, key=lambda p: p["z"] + p["h"]):
        top = prim["z"] + prim["h"]
        fill = steps[min(len(steps) - 1, int(round(top / zmax * (len(steps) - 1))))] if zmax > 0 else steps[-1]
        body += poly([plan(x, y) for x, y in prim["pts"]], fill)
    return wrap(body, on)


# ---------------------------------------------------------------- sheets (plan, translucent, parallax by height)

def sheets_mark(repo: dict, on: str = "paper") -> str:
    color = RING_COLORS[repo["ring"]]
    c = mix(color, "#FFFFFF", 0.3) if on == "ink" else color
    prims = spec_for(repo)
    body = ""
    for prim in sorted(prims, key=lambda p: p["z"]):
        shift = prim["z"] * 0.42
        pts = [plan(x + shift, y - shift) for x, y in prim["pts"]]
        body += f'<polygon points="{" ".join(f"{x:.2f},{y:.2f}" for x, y in pts)}" fill="{c}" fill-opacity="0.5"/>'
    return wrap(body, on)


PARADIGMS = {
    "solid": (solid_mark, "Isometric. Every object stands on its floor, lit from the left: top light, left face the ring hue, right face shadow. This is what the Blender round builds."),
    "contour": (contour_mark, "Plan view. Elevation becomes tone: the higher a part rises, the stronger its colour. A relief map of the same object."),
    "sheets": (sheets_mark, "Plan view. Every part is a translucent sheet shifted by its height; where sheets overlap the colour deepens. The same object as layers."),
}


# ---------------------------------------------------------------- output

def catalog() -> list[dict]:
    """Every repository but .github, from the vendored catalog (canonical home: the catalog repository)."""
    with (KIT / "config" / "catalog.toml").open("rb") as f:
        return [x for x in tomllib.load(f)["repo"] if x["name"] != ".github"]


HTML_HEAD = """<title>Public Software Objects</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;700;800&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
:root { --page:#FAFAF8; --ink:#14181F; --muted:#5B6472; --line:#D9DCD8; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --page:#0F141B; --ink:#EEF0EC; --muted:#9AA3AE; --line:#2A323D; } }
:root[data-theme="dark"] { --page:#0F141B; --ink:#EEF0EC; --muted:#9AA3AE; --line:#2A323D; }
body { background:var(--page); color:var(--ink); font-family:"Public Sans", system-ui, sans-serif; margin:0; }
main { max-width:1180px; margin:0 auto; padding:48px 32px 96px; }
h1 { font-size:34px; font-weight:800; letter-spacing:-0.8px; margin:0 0 8px; text-wrap:balance; }
h2 { font-size:26px; font-weight:800; letter-spacing:-0.5px; margin:0 0 6px; }
h3 { font-family:"JetBrains Mono", Menlo, monospace; font-size:13px; font-weight:600; letter-spacing:0.6px; text-transform:uppercase; margin:32px 0 12px; display:flex; align-items:center; gap:10px; }
h3 i { width:12px; height:12px; border-radius:3px; display:inline-block; }
.lede, .sub { color:var(--muted); font-size:16px; max-width:66ch; margin:0 0 20px; line-height:1.5; }
.paradigm { border-top:1px solid var(--line); padding:40px 0 16px; }
.hero { display:grid; grid-template-columns: 220px 220px 1fr; gap:24px; align-items:center; margin:8px 0 8px; }
.hero svg { width:220px; height:220px; border-radius:6px; }
.ramp { display:flex; gap:22px; align-items:flex-end; flex-wrap:wrap; }
.k { font-family:"JetBrains Mono", Menlo, monospace; font-size:12px; letter-spacing:0.6px; text-transform:uppercase; color:var(--muted); margin:18px 0 8px; }
.repos { display:grid; grid-template-columns:repeat(auto-fill, minmax(150px, 1fr)); gap:16px 14px; }
.repo .pair { display:grid; grid-template-columns:1fr 1fr; gap:4px; } .repo svg { width:100%; height:auto; border-radius:4px; }
.repo .n { font-family:"JetBrains Mono", Menlo, monospace; font-size:12px; font-weight:600; margin-top:8px; }
.repo .w { font-size:12.5px; color:var(--muted); line-height:1.4; margin-top:3px; }
</style>
"""


def strip(svg: str) -> str:
    return svg[svg.index(">") + 1:-6]


def write_html(repos: list[dict]) -> str:
    by_ring: dict[str, list[dict]] = {}
    for x in repos:
        by_ring.setdefault(x["ring"], []).append(x)
    blocks = []
    for pname, (fn, blurb) in PARADIGMS.items():
        org_p, org_i = fn(ORG, "paper"), fn(ORG, "ink")
        ramp = "".join(f'<svg width="{s}" height="{s}" viewBox="0 0 64 64">{strip(org_p)}</svg>' for s in (16, 24, 32, 48, 96))
        rings = ""
        for ring in ["spine", "platform", "system", "domain", "standards"]:
            cells = "".join(
                f'<div class="repo"><div class="pair">{fn(x, "paper")}{fn(x, "ink")}</div><div class="n">{x["name"]}</div><div class="w">{METAPHORS[x["name"]]["why"]}</div></div>'
                for x in by_ring[ring]
            )
            rings += f'<h3><i style="background:{RING_COLORS[ring]}"></i>{ring}</h3><div class="repos">{cells}</div>'
        blocks.append(f"""
<section class="paradigm" id="{pname}">
  <h2>{pname}</h2>
  <p class="sub">{blurb}</p>
  <div class="hero">{org_p}{org_i}<div class="ramp">{ramp}</div></div>
  {rings}
</section>""")
    return HTML_HEAD + f"""
<main>
  <h1>Fifty-eight objects, three ways of looking</h1>
  <p class="lede">No badge, no container. Each repository is described once as a small object on an eight-unit floor, built from boxes, cylinders and slabs that mean what the repo is. The organization is the ledger: a stepped stack of five slabs. Every paradigm below is a different projection of the same objects, so a choice here is a choice of how the whole identity is seen, on paper and on ink, with the ring as its colour.</p>
  {''.join(blocks)}
</main>
"""


def write_sheet(repos: list[dict], fn) -> str:
    items = [ORG] + repos
    cols, cell, pad = 8, 100, 14
    rows = -(-len(items) // cols)
    w, h = pad + cols * (cell + pad), pad + rows * (cell + 34)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" font-family="JetBrains Mono, Menlo, monospace">', f'<rect width="{w}" height="{h}" fill="#FFFFFF"/>']
    for i, repo in enumerate(items):
        x, y = pad + (i % cols) * (cell + pad), pad + (i // cols) * (cell + 34)
        parts.append(fn(repo).replace('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">', f'<svg x="{x}" y="{y}" width="{cell}" height="{cell}" viewBox="0 0 64 64">'))
        parts.append(f'<text x="{x + cell / 2}" y="{y + cell + 20}" font-size="11" text-anchor="middle" fill="#5B6472">{repo["name"]}</text>')
    parts.append("</svg>")
    return "".join(parts)


def write_all() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    repos = catalog()
    for pname, (fn, _) in PARADIGMS.items():
        (OUT / pname).mkdir(exist_ok=True)
        for repo in [ORG] + repos:
            for on in ("paper", "ink"):
                (OUT / pname / f"{repo['name']}-{on}.svg").write_text(fn(repo, on) + "\n")
        (OUT / f"sheet-{pname}.svg").write_text(write_sheet(repos, fn) + "\n")
    (OUT / "paradigms.html").write_text(write_html(repos))
    print(f"wrote {len(repos) + 1} objects × {len(PARADIGMS)} paradigms to {OUT}")


if __name__ == "__main__":
    write_all()
