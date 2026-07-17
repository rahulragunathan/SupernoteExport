"""Generate the SupernoteExport architecture diagram (.drawio).

Run from the repo root:
    python docs/architecture/build_architecture.py
    python ~/.claude/skills/drawio/scripts/validate.py \
        docs/architecture/supernote-export-architecture.drawio
    python ~/.claude/skills/drawio/scripts/render_png.py \
        docs/architecture/supernote-export-architecture.drawio

Conventions (see the `drawio` skill's SKILL.md): arrow colour matches its source
box; edges emitted after boxes so labels layer on top; multi-line edge labels use
<div> (survives a draw.io Desktop round-trip, unlike \\n); dark-mode contrast via
light-dark().

Reserved routing corridors:
  y=225  lane — pipeline.py → discover.py
  y=360  lane — naming.py → convert.py
  y=520  lane — convert.py → writer.py (the PDF path, skirting transcribe.py)
  x=450  channel — convert.py → supernotelib
  x=850  channel — transcribe.py → mlx-vlm

There is no legend: the diagram has no future-state shapes, and colour plus
labels carry the rest (the skill's "keep the legend lean" rule).
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- Palette. Light value + dark-mode contrast variant where one is needed. ---
COLOR_INPUT_BLUE = "#0078d4"  # Source .note files
COLOR_INPUT_BLUE_DARK = "#4da3ff"
COLOR_CLI_GREEN = "#34a853"  # User-facing entrypoint (reads in both themes)
COLOR_ORCH_PURPLE = "#5b3fbf"  # Orchestrator
COLOR_ORCH_PURPLE_DARK = "#b59dff"
COLOR_PLAN_GOLD = "#bf8f00"  # Pure planning layers (discover, naming)
COLOR_PLAN_GOLD_DARK = "#ffd966"
COLOR_CONVERT_ORANGE = "#d04a02"  # Conversion (reads in both themes)
COLOR_VLM_VIOLET = "#9c27b0"  # Transcription / VLM
COLOR_VLM_VIOLET_DARK = "#d18cff"
COLOR_WRITER_TEAL = "#008272"  # Output composition (reads in both themes)
COLOR_VAULT_NAVY = "#003c71"  # Written output artifacts
COLOR_VAULT_NAVY_DARK = "#7fb3e6"
COLOR_EXTERNAL_SLATE = "#37474f"  # Third-party libraries / local disk
COLOR_EXTERNAL_SLATE_DARK = "#b0bec5"

W, H = 1620, 790

mxfile = ET.Element("mxfile", host="app.diagrams.net", type="device", version="24.0.0")
diagram = ET.SubElement(
    mxfile, "diagram", name="SupernoteExport Architecture", id="supernote-export"
)
graph = ET.SubElement(
    diagram,
    "mxGraphModel",
    dx="1422",
    dy="757",
    grid="0",
    gridSize="10",
    guides="1",
    tooltips="1",
    connect="1",
    arrows="1",
    fold="1",
    page="1",
    pageScale="1",
    pageWidth=str(W),
    pageHeight=str(H),
    math="0",
    shadow="0",
)
root = ET.SubElement(graph, "root")
ET.SubElement(root, "mxCell", id="0")
ET.SubElement(root, "mxCell", id="1", parent="0")
_next = [2]


def cell_id():
    cid = str(_next[0])
    _next[0] += 1
    return cid


def ld(light, dark=None):
    return f"light-dark({light},{dark})" if dark else light


def container(
    x,
    y,
    w,
    h,
    title,
    stroke,
    fill="#ffffff",
    fontColor=None,
    fontSize=14,
    fill_dark=None,
    stroke_dark=None,
    fontColor_dark=None,
):
    cid = cell_id()
    style = (
        f"rounded=0;whiteSpace=wrap;html=1;"
        f"fillColor={ld(fill, fill_dark)};strokeColor={ld(stroke, stroke_dark)};"
        f"strokeWidth=2;dashed=1;verticalAlign=top;align=left;"
        f"fontColor={ld(fontColor or stroke, fontColor_dark or stroke_dark)};"
        f"fontSize={fontSize};fontStyle=1;spacingTop=8;spacingLeft=12;"
    )
    c = ET.SubElement(root, "mxCell", id=cid, value=title, style=style, vertex="1", parent="1")
    ET.SubElement(
        c, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h), **{"as": "geometry"}
    )
    return cid


def box(
    x,
    y,
    w,
    h,
    text,
    fill,
    stroke=None,
    fontColor="#ffffff",
    fontSize=12,
    bold=True,
    valign="middle",
    halign="center",
    dashed=False,
    fill_dark=None,
    stroke_dark=None,
    fontColor_dark=None,
):
    cid = cell_id()
    style = (
        f"rounded=1;whiteSpace=wrap;html=1;"
        f"fillColor={ld(fill, fill_dark)};"
        f"strokeColor={ld(stroke or fill, stroke_dark or fill_dark)};strokeWidth=1;"
        f"{'dashed=1;' if dashed else ''}"
        f"fontColor={ld(fontColor, fontColor_dark)};fontSize={fontSize};"
        f"fontStyle={1 if bold else 0};arcSize=10;verticalAlign={valign};align={halign};"
    )
    c = ET.SubElement(
        root,
        "mxCell",
        id=cid,
        value=text.replace("\n", "<br>"),
        style=style,
        vertex="1",
        parent="1",
    )
    ET.SubElement(
        c, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h), **{"as": "geometry"}
    )
    return cid


def edge(
    src,
    dst,
    color=COLOR_ORCH_PURPLE,
    width=2,
    style="solid",
    label=None,
    waypoints=None,
    exitX=None,
    exitY=None,
    entryX=None,
    entryY=None,
    label_x=None,
    label_y=None,
    color_dark=None,
    jump=False,
    bidirectional=False,
    end_arrow=True,
    label_color_dark=None,
):
    cid = cell_id()
    dash = (
        "dashed=1;"
        if style == "dashed"
        else ("dashed=1;dashPattern=1 4;" if style == "dotted" else "")
    )
    exit_str = f"exitX={exitX};exitY={exitY};exitDx=0;exitDy=0;" if exitX is not None else ""
    entry_str = (
        f"entryX={entryX};entryY={entryY};entryDx=0;entryDy=0;" if entryX is not None else ""
    )
    strokeC = ld(color, color_dark)
    style_str = (
        f"edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=0;jettySize=auto;html=1;"
        f"{exit_str}{entry_str}strokeColor={strokeC};strokeWidth={width};"
        f"{dash}{'jumpStyle=gap;' if jump else ''}"
        f"{'startArrow=classic;startFill=1;' if bidirectional else ''}"
        f"{'endArrow=classic;endFill=1;' if end_arrow else 'endArrow=none;'}"
        f"startSize=2;endSize=2;fontSize=10;fontColor={strokeC};labelBackgroundColor=#ffffff;"
    )
    value = label or ""
    dark_label = label_color_dark or color_dark
    if label and dark_label:
        value = f'<font color="light-dark(#000000,{dark_label})">{label}</font>'
    c = ET.SubElement(
        root,
        "mxCell",
        id=cid,
        value=value,
        style=style_str,
        edge="1",
        parent="1",
        source=src,
        target=dst,
    )
    geom = ET.SubElement(c, "mxGeometry", relative="1", **{"as": "geometry"})
    if waypoints:
        arr = ET.SubElement(geom, "Array", **{"as": "points"})
        for x, y in waypoints:
            ET.SubElement(arr, "mxPoint", x=str(x), y=str(y))
    if label and (label_x is not None or label_y is not None):
        ET.SubElement(geom, "mxPoint", x=str(label_x or 0), y=str(label_y or 0), **{"as": "offset"})
    return cid


def sub(text, size=10):
    return f"<span style='font-style:italic;font-weight:normal;font-size:{size}px'>{text}</span>"


def desc(text, size=10):
    return f"<span style='font-weight:normal;font-size:{size}px'>{text}</span>"


# --------------------------------------------------------------------------
# Title
# --------------------------------------------------------------------------
box(
    40,
    20,
    W - 80,
    46,
    "SupernoteExport — <span style='font-weight:normal'>.note → archival PDF + "
    "locally-transcribed Markdown (fully offline)</span>",
    fill="#1f3864",
    fontSize=17,
)

# --------------------------------------------------------------------------
# Zones (emitted before boxes so boxes layer on top)
# --------------------------------------------------------------------------
container(
    40,
    92,
    280,
    500,
    "Input",
    stroke=COLOR_INPUT_BLUE,
    fill="#eaf3fb",
    fontColor="#1f3864",
    fill_dark="#12242e",
    stroke_dark=COLOR_INPUT_BLUE_DARK,
    fontColor_dark=COLOR_INPUT_BLUE_DARK,
)
container(
    360,
    92,
    920,
    500,
    "supernote_export  —  local CLI, runs entirely on-device",
    stroke=COLOR_ORCH_PURPLE,
    fill="#f6f4fd",
    fill_dark="#1c1a26",
    stroke_dark=COLOR_ORCH_PURPLE_DARK,
    fontColor_dark=COLOR_ORCH_PURPLE_DARK,
)
container(
    1320,
    92,
    260,
    500,
    "Output — one pair per note",
    stroke=COLOR_VAULT_NAVY,
    fill="#eef3f8",
    fill_dark="#101b26",
    stroke_dark=COLOR_VAULT_NAVY_DARK,
    fontColor_dark=COLOR_VAULT_NAVY_DARK,
)

# --------------------------------------------------------------------------
# Boxes
# --------------------------------------------------------------------------
drive = box(
    70,
    280,
    220,
    180,
    "<b>.note files</b><br>"
    + sub("Supernote notebooks")
    + "<br><br>"
    + desc(
        "--input takes any path: a single file, or a folder searched "
        "recursively. Read-only; the subfolder tree is mirrored on output."
    ),
    fill=COLOR_INPUT_BLUE,
    fill_dark=COLOR_INPUT_BLUE_DARK,
    fontColor_dark="#08131a",
    bold=False,
)

cli = box(
    390,
    130,
    240,
    70,
    "<b>cli.py / __main__.py</b><br>" + sub("argparse entrypoint"),
    fill=COLOR_CLI_GREEN,
    bold=False,
)
pipe = box(
    730,
    130,
    240,
    70,
    "<b>pipeline.py — run()</b><br>" + sub("Orchestrator → Summary"),
    fill=COLOR_ORCH_PURPLE,
    fill_dark=COLOR_ORCH_PURPLE_DARK,
    fontColor_dark="#16122b",
    bold=False,
)

disc = box(
    390,
    250,
    240,
    80,
    "<b>1. discover.py</b><br>"
    + sub("Resolve --input")
    + "<br>"
    + desc("File or folder → sorted (note, subdir)"),
    fill=COLOR_PLAN_GOLD,
    fill_dark=COLOR_PLAN_GOLD_DARK,
    fontColor_dark="#241a00",
    bold=False,
)
name = box(
    730,
    250,
    240,
    80,
    "<b>2. naming.py</b><br>"
    + sub("Deterministic output names")
    + "<br>"
    + desc("Timestamp → date; -2/-3 on collision"),
    fill=COLOR_PLAN_GOLD,
    fill_dark=COLOR_PLAN_GOLD_DARK,
    fontColor_dark="#241a00",
    bold=False,
)

conv = box(
    390,
    390,
    240,
    90,
    "<b>3. convert.py</b><br>"
    + sub("supernotelib wrapper")
    + "<br>"
    + desc("note_to_pdf() · note_to_page_images()"),
    fill=COLOR_CONVERT_ORANGE,
    bold=False,
)
vlm = box(
    730,
    390,
    240,
    90,
    "<b>4. transcribe.py</b><br>"
    + sub("Transcriber protocol")
    + "<br>"
    + desc("MlxVlmTranscriber — MLX imported lazily"),
    fill=COLOR_VLM_VIOLET,
    fill_dark=COLOR_VLM_VIOLET_DARK,
    fontColor_dark="#2a0733",
    bold=False,
)
writer = box(
    1050,
    320,
    190,
    90,
    "<b>5. writer.py</b><br>"
    + sub("Compose + write")
    + "<br>"
    + desc("Transcription on top, embed at bottom"),
    fill=COLOR_WRITER_TEAL,
    bold=False,
)

pdf_out = box(
    1350,
    250,
    200,
    90,
    "<b>&lt;name&gt;.pdf</b><br>"
    + sub("Archival — source of truth")
    + "<br>"
    + desc("Full resolution"),
    fill=COLOR_VAULT_NAVY,
    fill_dark=COLOR_VAULT_NAVY_DARK,
    fontColor_dark="#04121c",
    bold=False,
)
md_out = box(
    1350,
    420,
    200,
    90,
    "<b>&lt;name&gt;.md</b><br>"
    + sub("Transcription + ![[embed]]")
    + "<br>"
    + desc("Obsidian note"),
    fill=COLOR_VAULT_NAVY,
    fill_dark=COLOR_VAULT_NAVY_DARK,
    fontColor_dark="#04121c",
    bold=False,
)

# External dependencies. Deliberately NOT wrapped in a dashed zone: every arrow
# would have to enter through the container's title band (TEXT_OVERLAP).
snlib = box(
    390,
    650,
    240,
    70,
    "<b>supernotelib</b><br>" + sub("third-party") + "<br>" + desc("PdfConverter · ImageConverter"),
    fill=COLOR_EXTERNAL_SLATE,
    fill_dark=COLOR_EXTERNAL_SLATE_DARK,
    fontColor_dark="#11181c",
    bold=False,
)
mlx = box(
    730,
    650,
    240,
    70,
    "<b>mlx-vlm</b><br>"
    + sub("third-party · Apple Silicon")
    + "<br>"
    + desc("Qwen3-VL by default"),
    fill=COLOR_EXTERNAL_SLATE,
    fill_dark=COLOR_EXTERNAL_SLATE_DARK,
    fontColor_dark="#11181c",
    bold=False,
)
weights = box(
    1080,
    650,
    300,
    70,
    "<b>Model weights — $HF_HOME</b><br>"
    + sub("local disk · default ~/Local-Models")
    + "<br>"
    + desc("Downloaded once on first run, then cached"),
    fill=COLOR_EXTERNAL_SLATE,
    fill_dark=COLOR_EXTERNAL_SLATE_DARK,
    fontColor_dark="#11181c",
    bold=False,
)

# --------------------------------------------------------------------------
# Edges (after boxes, so labels render on top)
# --------------------------------------------------------------------------
# Drive is read twice: once to enumerate notes, once per note to load bytes.
edge(
    drive,
    disc,
    color=COLOR_INPUT_BLUE,
    color_dark=COLOR_INPUT_BLUE_DARK,
    label="Scan<div>for .note</div>",
    exitX=1,
    exitY=0.25,
    entryX=0,
    entryY=0.5,
    label_x=0,
    label_y=-16,
)
edge(
    drive,
    conv,
    color=COLOR_INPUT_BLUE,
    color_dark=COLOR_INPUT_BLUE_DARK,
    label="Load<div>note bytes</div>",
    exitX=1,
    exitY=0.75,
    entryX=0,
    entryY=0.5,
    label_x=0,
    label_y=-16,
)

edge(
    cli,
    pipe,
    color=COLOR_CLI_GREEN,
    label="Parse args<div>call run()</div>",
    exitX=1,
    exitY=0.5,
    entryX=0,
    entryY=0.5,
)

# Lane y=225.
edge(
    pipe,
    disc,
    color=COLOR_ORCH_PURPLE,
    color_dark=COLOR_ORCH_PURPLE_DARK,
    label="Discover notes",
    exitX=0.5,
    exitY=1,
    entryX=0.5,
    entryY=0,
    waypoints=[(850, 225), (510, 225)],
    label_x=0,
    label_y=-12,
)

edge(
    disc,
    name,
    color=COLOR_PLAN_GOLD,
    color_dark=COLOR_PLAN_GOLD_DARK,
    label="Sorted<div>(note, subdir)</div>",
    exitX=1,
    exitY=0.5,
    entryX=0,
    entryY=0.5,
)

# Lane y=360.
edge(
    name,
    conv,
    color=COLOR_PLAN_GOLD,
    color_dark=COLOR_PLAN_GOLD_DARK,
    label="Planned (note, dir, name)",
    exitX=0.5,
    exitY=1,
    entryX=0.5,
    entryY=0,
    waypoints=[(850, 360), (510, 360)],
    label_x=0,
    label_y=-12,
)

# The two independent paths out of convert.py. The VLM never sees the PDF.
edge(
    conv,
    vlm,
    color=COLOR_CONVERT_ORANGE,
    label="Page PNGs<div>≤ --max-pixels</div>",
    exitX=1,
    exitY=0.5,
    entryX=0,
    entryY=0.5,
)
# Lane y=520 — the PDF path skirts transcribe.py entirely.
edge(
    conv,
    writer,
    color=COLOR_CONVERT_ORANGE,
    label="PDF bytes<div>(full resolution)</div>",
    exitX=0.75,
    exitY=1,
    entryX=0.5,
    entryY=1,
    waypoints=[(570, 520), (1145, 520)],
    jump=True,
    label_x=-70,
    label_y=0,
)
edge(
    vlm,
    writer,
    color=COLOR_VLM_VIOLET,
    color_dark=COLOR_VLM_VIOLET_DARK,
    label="Markdown<div>transcription</div>",
    exitX=1,
    exitY=0.5,
    entryX=0,
    entryY=0.5,
)

edge(
    writer,
    pdf_out,
    color=COLOR_WRITER_TEAL,
    label="Write",
    exitX=1,
    exitY=0.25,
    entryX=0,
    entryY=0.5,
)
edge(
    writer,
    md_out,
    color=COLOR_WRITER_TEAL,
    label="Write",
    exitX=1,
    exitY=0.75,
    entryX=0,
    entryY=0.5,
)

# Channel x=450 / x=800 down into the external row.
edge(
    conv,
    snlib,
    color=COLOR_CONVERT_ORANGE,
    label="Calls",
    exitX=0.25,
    exitY=1,
    entryX=0.25,
    entryY=0,
)
edge(
    vlm,
    mlx,
    color=COLOR_VLM_VIOLET,
    color_dark=COLOR_VLM_VIOLET_DARK,
    label="Calls",
    exitX=0.5,
    exitY=1,
    entryX=0.5,
    entryY=0,
)
edge(
    mlx,
    weights,
    color=COLOR_EXTERNAL_SLATE,
    color_dark=COLOR_EXTERNAL_SLATE_DARK,
    label="Loads / caches",
    exitX=1,
    exitY=0.5,
    entryX=0,
    entryY=0.5,
)

# --------------------------------------------------------------------------
# Write out
# --------------------------------------------------------------------------
xml_bytes = ET.tostring(mxfile, encoding="utf-8")
pretty = minidom.parseString(xml_bytes).toprettyxml(indent="  ")
out_path = "docs/architecture/supernote-export-architecture.drawio"
with open(out_path, "w") as f:
    f.write(pretty)
print(f"Wrote {out_path}")
print(f"Cells: {_next[0] - 2}")
