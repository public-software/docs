"""Every repository as a small relief on an 8×8 unit floor, composed to read from above.

One description per repository, three projections (see paradigms.py) and the Blender
build (blender/build.py). The camera looks down at 78°, so each object is a flat
pictogram with real thickness: a base at one height, details raised a step, and every
part touching so the voxel fuse makes one continuous piece. Primitives:

  B(x, y, w, d, h, z=0)   box: plan origin (x, y), plan size w×d, height h, resting at elevation z
  C(x, y, r, h, z=0)      cylinder (drawn as an octagonal prism): centre, radius, height, elevation
  T(points, h, z=0)       triangular slab: three plan points, thickness h, elevation z
  W(x, y, w, d, h, z=0)   wedge: a gable over the plan rectangle, eaves at z, ridge along x at z+h

Plan axes: x runs right, y runs toward the viewer. Heights are in the same units.
"""

from metaphors import METAPHORS


def B(x, y, w, d, h, z=0.0):
    return {"t": "box", "pts": [(x, y), (x + w, y), (x + w, y + d), (x, y + d)], "h": h, "z": z}


def C(x, y, r, h, z=0.0):
    import math
    pts = [(x + r * math.cos(math.radians(a)), y + r * math.sin(math.radians(a))) for a in range(22, 382, 45)]
    return {"t": "cyl", "pts": pts, "h": h, "z": z}


def W(x, y, w, d, h, z=0.0):
    """Wedge: a gable roof over the plan rectangle, eaves at z, ridge along x at z+h."""
    return {"t": "wedge", "pts": [(x, y), (x + w, y), (x + w, y + d), (x, y + d)], "h": h, "z": z}


def T(points, h, z=0.0):
    pts = list(points)
    area = sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]))
    if area < 0:
        pts.reverse()   # same winding as boxes, so face normals point outward
    return {"t": "tri", "pts": pts, "h": h, "z": z}


H = 1.0      # base relief height
UP = 0.7     # a raised detail sits this much higher

ORG_OBJECT = [B(0, 0, 8, 8, 1.1), B(1, 1, 6, 6, 1.1, 1.1), B(2, 2, 4, 4, 1.1, 2.2), B(3, 3, 2, 2, 1.1, 3.3), B(3.5, 3.5, 1, 1, 1.1, 4.4)]

OBJECTS = {
    # spine
    "catalog": [C(1, 1.2, 0.7, H), B(2.6, 0.5, 5, 1.4, H), C(1, 4, 0.7, H), B(2.6, 3.3, 5, 1.4, H), C(1, 6.8, 0.7, H), B(2.6, 6.1, 5, 1.4, H)],
    "interfaces": [B(0, 2, 3, 4, H), B(5, 2, 3, 4, H), B(2.8, 3.4, 2.4, 1.2, H)],
    "suite": [B(1, 3.2, 6, 4.8, H), B(2, 0.8, 1, 2.6, H), B(5, 0.8, 1, 2.6, H), B(2, 0.2, 4, 1, H), C(4, 5.6, 0.8, UP, H)],
    "rfcs": [B(0, 0, 8, 5, H), T([(1, 4.8), (3.4, 4.8), (1, 7.6)], H)],
    "docs": [B(0.2, 1, 3.6, 6.5, H), B(4.2, 1, 3.6, 6.5, H), B(3.6, 1, 0.8, 6.5, H + UP)],
    "pub": [B(0, 0, 2, 2, H), B(1.6, 1.8, 2, 2, H), B(3.2, 3.6, 2, 2, H), B(1.6, 5.4, 2, 2, H), B(0, 7.2, 2, 0.8, H), B(4.5, 6.4, 3.5, 1.6, H)],
    "templates": [B(1, 1, 6, 6, H), C(4, 4, 1.4, UP, H)],
    # platform
    "platform": [B(0, 0, 8, 8, H), B(0.5, 0.5, 1.6, 1.6, UP, H), B(5.9, 0.5, 1.6, 1.6, UP, H), B(0.5, 5.9, 1.6, 1.6, UP, H), B(5.9, 5.9, 1.6, 1.6, UP, H)],
    "design-system": [B(0, 0, 2.2, 2.2, H), B(2.9, 0, 2.2, 2.2, H), B(5.8, 0, 2.2, 2.2, H), B(0, 4, 8, 0.9, H), B(0, 6.4, 5, 0.9, H)],
    "ui": [B(0, 0, 8, 8, H), B(0, 0, 8, 1.6, UP, H), B(0, 1.6, 2.2, 6.4, UP, H)],
    "doc-model": [B(2.9, 2.9, 2.2, 2.2, H + UP), B(3.4, 0, 1.2, 2.9, H), B(3.4, 5.1, 1.2, 2.9, H), B(0, 3.4, 2.9, 1.2, H), B(5.1, 3.4, 2.9, 1.2, H), B(3.2, 0, 1.6, 1.6, H), B(3.2, 6.4, 1.6, 1.6, H), B(0, 3.2, 1.6, 1.6, H), B(6.4, 3.2, 1.6, 1.6, H)],
    "plugin-runtime": [B(1, 3, 6, 3.2, H), B(2.2, 0.8, 1, 2.4, H), B(4.8, 0.8, 1, 2.4, H), B(3.5, 6, 1, 2, H)],
    "identity": [C(4, 2, 1.6, H), B(3.3, 3.2, 1.4, 1.4, H), B(0.6, 4.4, 6.8, 3.2, H)],
    "pkg": [B(1, 1, 6, 6, H), B(3.7, 1, 0.6, 6, UP, H), B(1, 3.7, 6, 0.6, UP, H)],
    "observe": [C(4, 4, 3.7, H), C(4, 4, 1.4, UP, H)],
    # system
    "compiler": [B(0, 3, 4.8, 2, H), T([(4.6, 1), (8, 4), (4.6, 7)], H)],
    "linker": [B(0, 0, 2, 2, H), B(3, 0, 2, 2, H), B(6, 0, 2, 2, H), T([(0, 2), (8, 2), (4, 5.4)], H), B(3, 5, 2, 2.8, H)],
    "devtools": [C(4, 4.4, 2.4, H), C(4, 1.5, 1.1, H), B(0.4, 2.4, 1.8, 0.8, H), B(5.8, 2.4, 1.8, 0.8, H), B(0.4, 5.6, 1.8, 0.8, H), B(5.8, 5.6, 1.8, 0.8, H)],
    "firmware": [B(1.5, 1.5, 5, 5, H), B(2.5, 0, 0.8, 1.6, H), B(4.7, 0, 0.8, 1.6, H), B(2.5, 6.4, 0.8, 1.6, H), B(4.7, 6.4, 0.8, 1.6, H), B(0, 2.5, 1.6, 0.8, H), B(0, 4.7, 1.6, 0.8, H), B(6.4, 2.5, 1.6, 0.8, H), B(6.4, 4.7, 1.6, 0.8, H), B(3.2, 3.2, 1.6, 1.6, UP, H)],
    "hdl": [B(0, 1.6, 1.6, 0.9, H), B(1.6, 1.6, 0.9, 4.8, H), B(1.6, 5.5, 1.6, 0.9, H), B(3.2, 1.6, 0.9, 4.8, H), B(3.2, 1.6, 1.6, 0.9, H), B(4.8, 1.6, 0.9, 4.8, H), B(4.8, 5.5, 1.6, 0.9, H), B(6.4, 1.6, 0.9, 4.8, H), B(6.4, 1.6, 1.6, 0.9, H)],
    "eda": [B(0, 0, 8, 8, H), B(1, 1, 2, 2, UP, H), B(5, 1, 2, 2, UP, H), B(1, 5, 2, 2, UP, H), B(5, 5, 2, 2, UP, H), B(3, 1.7, 2, 0.6, UP, H), B(3.7, 1.7, 0.6, 4.6, UP, H)],
    "silicon": [C(4, 4, 3.8, H), B(2, 2, 1.6, 1.6, UP, H), B(4.4, 2, 1.6, 1.6, UP, H), B(2, 4.4, 1.6, 1.6, UP, H), B(4.4, 4.4, 1.6, 1.6, UP, H)],
    "kernel": [B(2.5, 2.5, 3, 3, H + UP), B(0, 0, 1.6, 1.6, H), B(6.4, 0, 1.6, 1.6, H), B(0, 6.4, 1.6, 1.6, H), B(6.4, 6.4, 1.6, 1.6, H)],
    "drivers": [C(4, 4, 2.8, H), B(3.4, 0.3, 1.2, 1.4, H), B(3.4, 6.3, 1.2, 1.4, H), B(0.3, 3.4, 1.4, 1.2, H), B(6.3, 3.4, 1.4, 1.2, H), C(4, 4, 0.9, UP, H)],
    "base": [B(0, 0, 3.8, 2, H), B(4.2, 0, 3.8, 2, H), B(0, 3, 1.8, 2, H), B(2.2, 3, 3.6, 2, H), B(6.2, 3, 1.8, 2, H), B(0, 6, 3.8, 2, H), B(4.2, 6, 3.8, 2, H)],
    "virt": [B(0, 0, 8, 8, H), B(2.4, 2.4, 3.2, 3.2, UP, H)],
    "net": [C(4, 4, 1.4, H), B(3.2, 0, 1.6, 1.6, H), B(3.2, 6.4, 1.6, 1.6, H), B(0, 3.2, 1.6, 1.6, H), B(6.4, 3.2, 1.6, 1.6, H), B(3.6, 1.4, 0.8, 2, H), B(3.6, 4.6, 0.8, 2, H), B(1.4, 3.6, 2, 0.8, H), B(4.6, 3.6, 2, 0.8, H)],
    "sdr": [B(3.6, 2.2, 0.8, 5.4, H), T([(3.2, 2.8), (4.8, 2.8), (0.6, 0)], H), T([(3.2, 2.8), (4.8, 2.8), (7.4, 0)], H), B(2, 7.4, 4, 0.6, H)],
    "store": [C(4, 4, 3.6, H), C(4, 4, 2.4, UP, H), C(4, 4, 1.2, UP, H + UP)],
    "cloud": [C(2.2, 3.4, 1.7, H), C(4.4, 2.6, 2.1, H), C(6.2, 3.6, 1.5, H), B(1, 3.6, 6, 1.6, H), B(0.5, 6.2, 1.6, 1.6, H), B(3.2, 6.2, 1.6, 1.6, H), B(5.9, 6.2, 1.6, 1.6, H)],
    "forge": [B(1, 0, 1.2, 8, H), B(2.2, 3.2, 1.2, 1.2, H), B(3.4, 2.2, 1.2, 1.2, H), B(4.6, 1.2, 1.2, 1.2, H), B(5.8, 0.2, 1.4, 1.4, H + UP)],
    "security": [B(1, 0, 6, 4, H), T([(1, 3.8), (7, 3.8), (4, 7.6)], H), C(4, 3, 1, UP, H)],
    "comms": [B(0, 1, 8, 6, H), T([(0.6, 1), (7.4, 1), (4, 4.4)], UP, H)],
    "graphics": [T([(4, 0), (8, 7.2), (0, 7.2)], H), B(3.4, 3.6, 1.2, 1.2, UP, H)],
    "media": [T([(1, 0), (7.8, 4), (1, 8)], H)],
    "js": [T([(5.6, 0), (1.4, 4.6), (4.6, 4.6)], H), T([(3.8, 3.4), (6.6, 3.4), (2.4, 8)], H)],
    "desktop": [B(0.5, 0, 7, 5, H), B(1.1, 0.6, 5.8, 3.6, UP, H), B(3.5, 5, 1, 1.4, H), B(2, 6.4, 4, 0.9, H)],
    "mobile": [B(2, 0, 4, 8, H), B(2.5, 0.8, 3, 5.6, UP, H), C(4, 7.2, 0.45, UP, H)],
    "web": [B(0, 0, 8, 8, H), B(0, 0, 8, 1.6, UP, H), C(0.9, 0.8, 0.45, UP, H + UP), B(1, 2.6, 6, 4.6, UP, H)],
    "ai": [B(3.5, 0, 1, 8, H), B(0, 3.5, 8, 1, H), B(2.7, 2.7, 2.6, 2.6, H + UP)],
    # domain
    "office": [B(0, 0, 8, 8, H), B(0, 2.55, 8, 0.35, UP, H), B(0, 5.1, 8, 0.35, UP, H), B(2.55, 0, 0.35, 8, UP, H), B(5.1, 0, 0.35, 8, UP, H)],
    "workspace": [B(0, 0, 2.2, 2, H), B(0, 2.6, 2.2, 2, H), B(0, 5.2, 2.2, 2, H), B(2.9, 0, 2.2, 2, H), B(2.9, 2.6, 2.2, 2, H), B(5.8, 0, 2.2, 2, H)],
    "home": [T([(0, 3.2), (8, 3.2), (4, 0)], H), B(1, 3.2, 6, 4.8, H), B(3.4, 5.4, 1.2, 2.6, UP, H), B(5.6, 1.2, 0.9, 2.2, H)],
    "imaging": [B(0, 0, 8, 8, H), T([(0.6, 7.2), (4, 3), (7.4, 7.2)], UP, H), C(1.9, 1.9, 0.9, UP, H)],
    "video": [B(0, 2.2, 8, 5.8, H), B(0, 0.4, 8, 1.6, H + UP), B(1, 0.4, 1.4, 1.6, UP, H + UP), B(4, 0.4, 1.4, 1.6, UP, H + UP)],
    "audio": [C(2.5, 6.2, 1.6, H), B(3.4, 0, 0.8, 6.5, H), B(3.4, 0, 3.4, 1.1, H)],
    "3d": [T([(4, 0.2), (7.4, 2.2), (4, 4.2)], H + 2 * UP), T([(4, 0.2), (0.6, 2.2), (4, 4.2)], H + 2 * UP), T([(0.6, 2.2), (4, 4.2), (4, 8)], H), T([(0.6, 2.2), (4, 8), (0.6, 6)], H), T([(4, 4.2), (7.4, 2.2), (7.4, 6)], H + UP), T([(4, 4.2), (7.4, 6), (4, 8)], H + UP)],
    "cad": [T([(3.5, 0), (4.5, 0), (0.6, 8)], H), T([(3.5, 0), (4.5, 0), (7.4, 8)], H), C(4, 0.8, 0.9, UP, H)],
    "engineering": [B(0, 0, 8, 8, H), B(1, 1, 4.2, 0.6, UP, H), B(4.6, 1, 0.6, 4, UP, H), B(4.6, 4.4, 2.8, 0.6, UP, H), C(1.3, 1.3, 0.7, UP, H), C(7.1, 4.7, 0.7, UP, H), B(1, 5, 2.6, 2.6, UP, H)],
    "science": [B(2.6, 0, 2.8, 0.8, H), B(3.3, 0.6, 1.4, 2.4, H), T([(4, 2.2), (7.6, 8), (0.4, 8)], H)],
    "business": [B(0.5, 5, 1.8, 2.5, H), B(3.1, 3, 1.8, 4.5, H), B(5.7, 0.5, 1.8, 7, H), B(0, 7.4, 8, 0.6, H)],
    "finance": [C(4, 4, 3.5, H), C(4, 4, 2.4, UP, H), B(3.4, 2.4, 1.2, 3.2, UP, H + UP)],
    "health": [B(3, 0, 2, 8, H), B(0, 3, 8, 2, H)],
    "civic": [T([(0, 2.6), (8, 2.6), (4, 0)], H), B(0.6, 2.4, 6.8, 0.9, H), B(1.0, 3.2, 1.2, 3.6, H), B(3.4, 3.2, 1.2, 3.6, H), B(5.8, 3.2, 1.2, 3.6, H), B(0, 6.8, 8, 1.2, H)],
    "games": [B(0, 2, 8, 4, H), C(6.1, 3.3, 0.55, UP, H), C(6.9, 4.5, 0.55, UP, H), B(1, 3.7, 2, 0.6, UP, H), B(1.7, 3, 0.6, 2, UP, H)],
    # standards
    "specs": [C(4, 3, 3, H), B(2.4, 5.4, 1.3, 2.6, H), B(4.3, 5.4, 1.3, 2.6, H), C(4, 3, 1.1, UP, H)],
    "content": [B(0, 1.5, 8, 6.5, H), B(0, 0, 3, 1.5, H), B(1, 2.5, 6, 4.6, UP, H)],
}

assert set(OBJECTS) == set(METAPHORS), set(OBJECTS) ^ set(METAPHORS)
