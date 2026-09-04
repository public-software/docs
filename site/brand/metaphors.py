"""The metaphor catalog: why each repository's mark looks the way it does.

Every entry gives the reasoning, then the same motif in two vocabularies:

  pills   five rows of a 5×5 grid. '#' lit cell, 'o' hollow cell, '.' empty.
          Horizontal runs render as bars, then vertical runs, then single cells as
          dots; hollow cells as rings.
  trace   strokes: polylines on a 5×5 point grid (x right, y down, 0..4);
          pads: solid terminals; vias: open terminals.

The organization itself is the identity element of each grammar: the whole ledger,
widening downward, and a bus with three widening branches.
"""

ORG_METAPHOR = {
    "why": "The organization is the whole ledger: every layer, widening from firmware to the suite.",
    "pills": ["#....", "##...", "###..", "####.", "#####"],
    "trace": {"strokes": [[(0, 0), (0, 4)], [(0, 1), (2, 1)], [(0, 2), (3, 2)], [(0, 3), (4, 3)]],
              "pads": [(2, 1), (3, 2), (4, 3)], "vias": [(0, 0)]},
}

METAPHORS = {
    # ---------------------------------------------------------------- spine
    "catalog": {
        "why": "A ledger of entries: bullet, line, bullet, line. The source of truth is a list.",
        "pills": ["#.###", ".....", "#.###", ".....", "#.###"],
        "trace": {"strokes": [[(1, 0), (4, 0)], [(1, 2), (4, 2)], [(1, 4), (4, 4)]], "pads": [(0, 0), (0, 2), (0, 4)], "vias": []},
    },
    "interfaces": {
        "why": "Two sides meeting on one contract: two blocks joined by a bridge.",
        "pills": [".....", "##.##", "#####", "##.##", "....."],
        "trace": {"strokes": [[(0, 0), (2, 2), (4, 2)], [(0, 4), (2, 2)]], "pads": [(0, 0), (0, 4)], "vias": [(4, 2)]},
    },
    "suite": {
        "why": "The lockfile: a padlock. Every crate pinned, the whole suite closed as one.",
        "pills": [".###.", "#...#", "#####", "##o##", "#####"],
        "trace": {"strokes": [[(1, 2), (1, 1), (2, 0), (3, 1), (3, 2)], [(0, 2), (4, 2), (4, 4), (0, 4), (0, 2)]], "pads": [], "vias": [(2, 3)]},
    },
    "rfcs": {
        "why": "A proposal is a conversation: a speech bubble with its tail.",
        "pills": ["#####", "#...#", "#####", ".#...", "#...."],
        "trace": {"strokes": [[(0, 0), (4, 0), (4, 2), (1, 2), (0, 3), (0, 0)]], "pads": [], "vias": [(2, 1)]},
    },
    "docs": {
        "why": "A page with a folded corner: the handbook.",
        "pills": ["####.", "#..##", "#...#", "#...#", "#####"],
        "trace": {"strokes": [[(0, 0), (3, 0), (4, 1), (4, 4), (0, 4), (0, 0)], [(1, 2), (3, 2)], [(1, 3), (3, 3)]], "pads": [], "vias": []},
    },
    "pub": {
        "why": "The CLI prompt: a chevron and a cursor.",
        "pills": ["#....", ".#...", "..#..", ".#...", "#..##"],
        "trace": {"strokes": [[(0, 0), (2, 2), (0, 4)], [(2, 4), (4, 4)]], "pads": [(4, 4)], "vias": []},
    },
    "templates": {
        "why": "A rubber stamp: the shape the CLI stamps every new repo from.",
        "pills": [".###.", ".###.", "..#..", "#####", "....."],
        "trace": {"strokes": [[(2, 0), (2, 2)], [(0, 2), (4, 2)], [(0, 4), (4, 4)]], "pads": [(2, 0)], "vias": []},
    },
    # ---------------------------------------------------------------- platform
    "platform": {
        "why": "A slab on pillars, with a second slab below: the foundation everything stands on.",
        "pills": ["#.#.#", "#.#.#", "#####", ".....", "#####"],
        "trace": {"strokes": [[(0, 2), (4, 2)], [(1, 2), (1, 4)], [(3, 2), (3, 4)]], "pads": [(2, 0)], "vias": []},
    },
    "design-system": {
        "why": "Tokens: colour swatches, a spacing rule, a type baseline.",
        "pills": ["##.##", "##.##", ".....", "##.##", "##.##"],
        "trace": {"strokes": [[(0, 2), (4, 2)], [(0, 4), (2, 4)]], "pads": [(0, 0), (2, 0), (4, 0)], "vias": [(4, 4)]},
    },
    "ui": {
        "why": "A window with a title bar and a sidebar: the app shell.",
        "pills": ["#####", "#.###", "#.###", "#.###", "#####"],
        "trace": {"strokes": [[(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)], [(0, 1), (4, 1)], [(1, 1), (1, 4)]], "pads": [], "vias": []},
    },
    "doc-model": {
        "why": "A document is a graph: four nodes bound to a centre.",
        "pills": ["o...o", ".#.#.", "..#..", ".#.#.", "o...o"],
        "trace": {"strokes": [[(2, 2), (0, 0)], [(2, 2), (4, 0)], [(2, 2), (0, 4)], [(2, 2), (4, 4)]], "pads": [(2, 2)], "vias": [(0, 0), (4, 0), (0, 4), (4, 4)]},
    },
    "plugin-runtime": {
        "why": "A plug: two prongs, a body, a cord. Components plug into the host.",
        "pills": [".#.#.", ".#.#.", "#####", ".###.", "..#.."],
        "trace": {"strokes": [[(1, 0), (1, 1)], [(3, 0), (3, 1)], [(0, 1), (4, 1), (4, 3), (0, 3), (0, 1)], [(2, 3), (2, 4)]], "pads": [(2, 4)], "vias": []},
    },
    "identity": {
        "why": "A person: a head and shoulders. Who you are, on every device.",
        "pills": ["..o..", ".....", ".###.", "#####", "#####"],
        "trace": {"strokes": [[(0, 4), (0, 3), (1, 2), (3, 2), (4, 3), (4, 4)]], "pads": [(2, 0)], "vias": []},
    },
    "pkg": {
        "why": "A box with a lid: the package, content-addressed and sealed.",
        "pills": [".###.", "#####", "#...#", "#...#", "#####"],
        "trace": {"strokes": [[(0, 1), (4, 1), (4, 4), (0, 4), (0, 1)], [(0, 1), (1, 0), (3, 0), (4, 1)], [(2, 1), (2, 4)]], "pads": [], "vias": []},
    },
    "observe": {
        "why": "An eye with a hollow pupil: metrics, traces, logs, watching.",
        "pills": [".....", ".###.", "#.o.#", ".###.", "....."],
        "trace": {"strokes": [[(0, 2), (2, 0), (4, 2)], [(0, 2), (2, 4), (4, 2)]], "pads": [(2, 2)], "vias": []},
    },
    # ---------------------------------------------------------------- system
    "compiler": {
        "why": "An arrow: source in, binary out.",
        "pills": ["..#..", "...#.", "#####", "...#.", "..#.."],
        "trace": {"strokes": [[(0, 2), (4, 2)], [(2, 0), (4, 2), (2, 4)]], "pads": [(0, 2)], "vias": []},
    },
    "linker": {
        "why": "Three objects converging into one: the link step.",
        "pills": ["#.#.#", ".#.#.", "..#..", "..#..", "..#.."],
        "trace": {"strokes": [[(0, 0), (2, 2)], [(2, 0), (2, 2)], [(4, 0), (2, 2)], [(2, 2), (2, 4)]], "pads": [(0, 0), (2, 0), (4, 0)], "vias": [(2, 4)]},
    },
    "devtools": {
        "why": "A bug, with legs. Debugger, fuzzer, profiler.",
        "pills": ["#.#.#", ".###.", "#####", ".###.", "#.#.#"],
        "trace": {"strokes": [[(1, 1), (3, 1), (3, 3), (1, 3), (1, 1)], [(0, 0), (1, 1)], [(4, 0), (3, 1)], [(0, 4), (1, 3)], [(4, 4), (3, 3)]], "pads": [], "vias": []},
    },
    "firmware": {
        "why": "A chip with its pins: the code that lives on the board.",
        "pills": [".#.#.", "#####", "#####", "#####", ".#.#."],
        "trace": {"strokes": [[(1, 1), (3, 1), (3, 3), (1, 3), (1, 1)], [(1, 0), (1, 1)], [(3, 0), (3, 1)], [(1, 3), (1, 4)], [(3, 3), (3, 4)]], "pads": [(2, 2)], "vias": []},
    },
    "hdl": {
        "why": "A clock signal: high, low, high, low, high.",
        "pills": ["#.#.#", "#.#.#", ".....", ".#.#.", ".#.#."],
        "trace": {"strokes": [[(0, 3), (0, 1), (1, 1), (1, 3), (2, 3), (2, 1), (3, 1), (3, 3), (4, 3)]], "pads": [(0, 3)], "vias": []},
    },
    "eda": {
        "why": "Cells on a die with a route running between them: place and route.",
        "pills": ["#.#.#", ".....", "#####", ".....", "#.#.#"],
        "trace": {"strokes": [[(0, 0), (0, 2), (2, 2), (2, 4)], [(4, 0), (4, 2), (3, 2)]], "pads": [(0, 0), (4, 0)], "vias": [(2, 4), (3, 2)]},
    },
    "silicon": {
        "why": "A wafer with a hollow at its heart: the crystal the chain starts from.",
        "pills": [".###.", "#####", "##o##", "#####", ".###."],
        "trace": {"strokes": [[(2, 0), (4, 2), (2, 4), (0, 2), (2, 0)], [(2, 1), (3, 2), (2, 3), (1, 2), (2, 1)]], "pads": [], "vias": []},
    },
    "kernel": {
        "why": "A core with four things orbiting it: the kernel and what it schedules.",
        "pills": ["#...#", ".###.", ".###.", ".###.", "#...#"],
        "trace": {"strokes": [[(1, 1), (3, 1), (3, 3), (1, 3), (1, 1)]], "pads": [(0, 0), (4, 0), (0, 4), (4, 4)], "vias": []},
    },
    "drivers": {
        "why": "A gear with a hollow centre: the parts that turn hardware.",
        "pills": [".#.#.", "#####", ".#o#.", "#####", ".#.#."],
        "trace": {"strokes": [[(1, 1), (3, 1), (3, 3), (1, 3), (1, 1)], [(2, 0), (2, 1)], [(2, 3), (2, 4)], [(0, 2), (1, 2)], [(3, 2), (4, 2)]], "pads": [], "vias": [(2, 2)]},
    },
    "base": {
        "why": "Courses of bricks: init, journal, utilities, the base system.",
        "pills": ["#####", ".....", "##.##", ".....", "#####"],
        "trace": {"strokes": [[(0, 0), (4, 0)], [(0, 2), (4, 2)], [(0, 4), (4, 4)], [(2, 0), (2, 2)], [(1, 2), (1, 4)], [(3, 2), (3, 4)]], "pads": [], "vias": []},
    },
    "virt": {
        "why": "A box inside a box: a machine inside a machine.",
        "pills": ["#####", "#...#", "#.#.#", "#...#", "#####"],
        "trace": {"strokes": [[(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)]], "pads": [(2, 2)], "vias": []},
    },
    "net": {
        "why": "A hub with four links: nodes reaching a centre.",
        "pills": ["#...#", ".#.#.", "..o..", ".#.#.", "#...#"],
        "trace": {"strokes": [[(2, 2), (0, 0)], [(2, 2), (4, 0)], [(2, 2), (0, 4)], [(2, 2), (4, 4)]], "pads": [(0, 0), (4, 0), (0, 4), (4, 4)], "vias": [(2, 2)]},
    },
    "sdr": {
        "why": "An antenna: a mast with a V at the top, catching radio.",
        "pills": ["#...#", ".#.#.", "..#..", "..#..", "..#.."],
        "trace": {"strokes": [[(2, 4), (2, 1)], [(0, 0), (2, 1), (4, 0)]], "pads": [(2, 4)], "vias": [(2, 1)]},
    },
    "store": {
        "why": "Three platters: the database stack.",
        "pills": ["#####", ".....", "#####", ".....", "#####"],
        "trace": {"strokes": [[(0, 0), (4, 0)], [(0, 0), (0, 4)], [(4, 0), (4, 4)], [(0, 4), (4, 4)], [(0, 2), (4, 2)]], "pads": [], "vias": []},
    },
    "cloud": {
        "why": "A cloud over three nodes: the control plane and what it runs.",
        "pills": [".###.", "#####", "#####", ".....", "#.#.#"],
        "trace": {"strokes": [[(0, 2), (1, 1), (2, 0), (3, 1), (4, 2)], [(0, 2), (4, 2)], [(2, 2), (2, 4)]], "pads": [(0, 4), (2, 4), (4, 4)], "vias": []},
    },
    "forge": {
        "why": "A branch merging into the trunk: the commit graph.",
        "pills": ["#...#", "#..#.", "#.#..", "##...", "#...."],
        "trace": {"strokes": [[(1, 0), (1, 4)], [(1, 3), (3, 1)]], "pads": [(1, 0), (3, 1)], "vias": [(1, 4)]},
    },
    "security": {
        "why": "A shield with a hollow at its centre: the secret it protects.",
        "pills": ["#####", "##o##", "#####", ".###.", "..#.."],
        "trace": {"strokes": [[(0, 0), (4, 0), (4, 2), (2, 4), (0, 2), (0, 0)]], "pads": [], "vias": [(2, 1)]},
    },
    "comms": {
        "why": "An envelope: mail, chat, calls, all messages.",
        "pills": ["#####", "##.##", "#.#.#", "#...#", "#####"],
        "trace": {"strokes": [[(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)], [(0, 0), (2, 2), (4, 0)]], "pads": [], "vias": []},
    },
    "graphics": {
        "why": "A triangle over three samples: the primitive and the pixels it becomes.",
        "pills": ["..#..", ".###.", "#####", ".....", "#.#.#"],
        "trace": {"strokes": [[(2, 0), (4, 3), (0, 3), (2, 0)]], "pads": [], "vias": [(2, 2)]},
    },
    "media": {
        "why": "Play.",
        "pills": ["#....", "###..", "#####", "###..", "#...."],
        "trace": {"strokes": [[(0, 0), (4, 2), (0, 4), (0, 0)]], "pads": [], "vias": []},
    },
    "js": {
        "why": "A lightning bolt: the JIT.",
        "pills": ["..##.", ".##..", "####.", "..##.", ".##.."],
        "trace": {"strokes": [[(3, 0), (1, 2), (3, 2), (1, 4)]], "pads": [(3, 0)], "vias": []},
    },
    "desktop": {
        "why": "A monitor on a stand.",
        "pills": ["#####", "#...#", "#####", "..#..", ".###."],
        "trace": {"strokes": [[(0, 0), (4, 0), (4, 3), (0, 3), (0, 0)], [(2, 3), (2, 4)], [(1, 4), (3, 4)]], "pads": [], "vias": []},
    },
    "mobile": {
        "why": "A phone with its button.",
        "pills": [".###.", ".#.#.", ".#.#.", ".#o#.", ".###."],
        "trace": {"strokes": [[(1, 0), (3, 0), (3, 4), (1, 4), (1, 0)]], "pads": [], "vias": [(2, 3)]},
    },
    "web": {
        "why": "A globe with a meridian: the browser and the map.",
        "pills": [".###.", "#.#.#", "#####", "#.#.#", ".###."],
        "trace": {"strokes": [[(2, 0), (4, 2), (2, 4), (0, 2), (2, 0)], [(0, 2), (4, 2)], [(2, 0), (2, 4)]], "pads": [], "vias": []},
    },
    "ai": {
        "why": "A spark with a hollow centre: inference.",
        "pills": ["..#..", ".###.", "##o##", ".###.", "..#.."],
        "trace": {"strokes": [[(2, 0), (2, 4)], [(0, 2), (4, 2)], [(1, 1), (3, 3)], [(3, 1), (1, 3)]], "pads": [], "vias": [(2, 2)]},
    },
    # ---------------------------------------------------------------- domain
    "office": {
        "why": "A sheet: the grid every document, table and slide is laid on.",
        "pills": ["#####", "#.#.#", "#####", "#.#.#", "#####"],
        "trace": {"strokes": [[(0, 0), (4, 0)], [(0, 2), (4, 2)], [(0, 4), (4, 4)], [(0, 0), (0, 4)], [(2, 0), (2, 4)], [(4, 0), (4, 4)]], "pads": [], "vias": []},
    },
    "workspace": {
        "why": "Three columns of cards: the board where work is organized.",
        "pills": ["#.#.#", "#.#.#", "#.#.#", "#.#..", "#...."],
        "trace": {"strokes": [[(0, 0), (0, 4)], [(2, 0), (2, 3)], [(4, 0), (4, 2)]], "pads": [(0, 0), (2, 0), (4, 0)], "vias": []},
    },
    "home": {
        "why": "A house with a door.",
        "pills": ["..#..", ".###.", "#####", "##.##", "##.##"],
        "trace": {"strokes": [[(0, 2), (2, 0), (4, 2)], [(0, 2), (0, 4), (4, 4), (4, 2)], [(2, 4), (2, 3)]], "pads": [], "vias": []},
    },
    "imaging": {
        "why": "A picture: a frame, a sun, a mountain.",
        "pills": ["#####", "#..o#", "#.#.#", "##.##", "#####"],
        "trace": {"strokes": [[(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)], [(0, 3), (1, 2), (2, 3), (3, 1), (4, 3)]], "pads": [], "vias": [(1, 1)]},
    },
    "video": {
        "why": "A clapperboard.",
        "pills": ["#.#.#", "#####", "#...#", "#...#", "#####"],
        "trace": {"strokes": [[(0, 1), (4, 1), (4, 4), (0, 4), (0, 1)], [(0, 1), (1, 0), (4, 0)], [(2, 0), (2, 1)]], "pads": [], "vias": []},
    },
    "audio": {
        "why": "A note.",
        "pills": ["...##", "...#.", "...#.", ".###.", ".###."],
        "trace": {"strokes": [[(3, 0), (3, 4)], [(3, 0), (4, 0), (4, 1)]], "pads": [(2, 4)], "vias": []},
    },
    "3d": {
        "why": "A cube seen from its corner.",
        "pills": ["..#..", ".#.#.", "#.o.#", ".#.#.", "..#.."],
        "trace": {"strokes": [[(2, 0), (4, 1), (4, 3), (2, 4), (0, 3), (0, 1), (2, 0)], [(2, 2), (2, 4)], [(2, 2), (0, 1)], [(2, 2), (4, 1)]], "pads": [], "vias": []},
    },
    "cad": {
        "why": "A divider: the drafting instrument.",
        "pills": ["..#..", ".#.#.", ".#.#.", "#...#", "#...#"],
        "trace": {"strokes": [[(0, 4), (2, 0), (4, 4)], [(1, 2), (3, 2)]], "pads": [], "vias": [(2, 0)]},
    },
    "engineering": {
        "why": "A trace across a board: PCB, SPICE, the physical world.",
        "pills": ["#....", "####.", "...#.", ".####", "....#"],
        "trace": {"strokes": [[(0, 0), (2, 0), (2, 2), (4, 2), (4, 4)]], "pads": [(0, 0)], "vias": [(4, 4)]},
    },
    "science": {
        "why": "A flask.",
        "pills": [".###.", "..#..", "..#..", ".###.", "#####"],
        "trace": {"strokes": [[(1, 0), (3, 0)], [(2, 0), (2, 1)], [(2, 1), (0, 4), (4, 4), (2, 1)]], "pads": [], "vias": []},
    },
    "business": {
        "why": "Bars rising: the chart on every dashboard.",
        "pills": ["....#", "....#", "..#.#", "#.#.#", "#.#.#"],
        "trace": {"strokes": [[(0, 4), (0, 2)], [(2, 4), (2, 1)], [(4, 4), (4, 0)], [(0, 4), (4, 4)]], "pads": [(0, 2), (2, 1), (4, 0)], "vias": []},
    },
    "finance": {
        "why": "A stack of coins.",
        "pills": [".###.", "#####", ".###.", "#####", ".###."],
        "trace": {"strokes": [[(1, 0), (3, 0), (4, 1), (4, 3), (3, 4), (1, 4), (0, 3), (0, 1), (1, 0)]], "pads": [(2, 2)], "vias": []},
    },
    "health": {
        "why": "A cross.",
        "pills": ["..#..", "..#..", "#####", "..#..", "..#.."],
        "trace": {"strokes": [[(2, 0), (2, 4)], [(0, 2), (4, 2)]], "pads": [], "vias": []},
    },
    "civic": {
        "why": "A building with columns: the institution.",
        "pills": ["#####", ".....", "#.#.#", "#.#.#", "#####"],
        "trace": {"strokes": [[(0, 1), (2, 0), (4, 1)], [(0, 1), (0, 4)], [(2, 1), (2, 4)], [(4, 1), (4, 4)], [(0, 4), (4, 4)]], "pads": [], "vias": []},
    },
    "games": {
        "why": "A gamepad with two buttons.",
        "pills": [".....", "#####", "#o#o#", "#####", "....."],
        "trace": {"strokes": [[(0, 1), (4, 1), (4, 3), (0, 3), (0, 1)]], "pads": [], "vias": [(1, 2), (3, 2)]},
    },
    # ---------------------------------------------------------------- standards
    "specs": {
        "why": "A seal with ribbons: conformance, certified.",
        "pills": [".###.", "##o##", ".###.", ".#.#.", ".#.#."],
        "trace": {"strokes": [[(1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (1, 3), (0, 2), (0, 1), (1, 0)], [(1, 3), (1, 4)], [(3, 3), (3, 4)]], "pads": [], "vias": [(2, 1)]},
    },
    "content": {
        "why": "A folder: the open data the suite depends on.",
        "pills": ["##...", "#####", "#...#", "#...#", "#####"],
        "trace": {"strokes": [[(0, 1), (0, 4), (4, 4), (4, 1), (2, 1), (1, 0), (0, 0), (0, 1)]], "pads": [], "vias": []},
    },
}
