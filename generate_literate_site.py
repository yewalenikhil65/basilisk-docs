#!/usr/bin/env python3
"""
generate_literate_site.py — Extract literate documentation from Basilisk .h files
and produce a standalone HTML site that cross-links into the Doxygen API reference.

Basilisk .h files use /** ... */ comment blocks for prose (with LaTeX math)
and everything outside is C code.

Usage:
    python3 generate_literate_site.py --src ./basilisk/src --doxygen-html ./output/html --out ./output/literate
"""

import argparse
import os
import re
import html as html_mod
from pathlib import Path

DOXYGEN_REL = "../html"

MODULES = {
    "Navier–Stokes": [
        "navier-stokes/centered.h", "navier-stokes/mac.h",
        "navier-stokes/stream.h", "navier-stokes/swirl.h",
    ],
    "Saint-Venant / Shallow Water": [
        "saint-venant.h", "saint-venant-implicit.h",
        "multilayer.h", "green-naghdi.h",
    ],
    "Multilayer": [
        "layered/hydro.h", "layered/nh.h", "layered/remap.h",
        "layered/perfs.h",
    ],
    "Compressible": [
        "compressible.h", "all-mach.h",
        "compressible/two-phase.h", "compressible/thermal.h",
    ],
    "Advection & VOF": [
        "advection.h", "vof.h", "fractions.h", "tracer.h",
        "bcg.h", "contact.h", "no-coalescence.h",
    ],
    "Interfacial Forces": [
        "iforce.h", "tension.h", "reduced.h", "integral.h",
        "curvature.h", "heights.h",
    ],
    "Two-Phase": [
        "two-phase.h", "two-phase-generic.h",
        "two-phase-clsvof.h", "two-phase-levelset.h",
        "momentum.h",
    ],
    "Elliptic Solvers": [
        "poisson.h", "diffusion.h", "viscosity.h",
        "viscosity-embed.h", "solve.h",
    ],
    "Electrohydrodynamics": [
        "ehd/implicit.h", "ehd/pnp.h", "ehd/stress.h",
    ],
    "Viscoelasticity": [
        "log-conform.h", "fene-p.h",
    ],
    "Grid System": [
        "grid/quadtree.h", "grid/octree.h", "grid/multigrid.h",
        "grid/tree-common.h", "grid/tree-mpi.h",
        "grid/cartesian-common.h", "grid/events.h",
        "grid/boundaries.h", "grid/multigrid-mpi.h",
    ],
    "Core": [
        "common.h", "run.h", "timestep.h",
        "predictor-corrector.h",
    ],
    "Coordinates & Metrics": [
        "axi.h", "spherical.h", "spherisym.h", "radial.h",
    ],
    "Input / Output": [
        "output.h", "input.h", "vtk.h", "view.h", "draw.h",
    ],
    "Utilities": [
        "utils.h", "tag.h", "lambda2.h", "harmonic.h",
        "distance.h", "redistance.h", "elevation.h",
        "terrain.h", "gauges.h", "maxruntime.h", "perfs.h",
    ],
    "Other": [
        "hele-shaw.h", "conservation.h", "henry.h",
        "runge-kutta.h", "hessenberg.h", "okada.h",
        "discharge.h", "embed.h", "embed-tree.h",
    ],
}

CSS = """\
:root { --bg: #fafafa; --fg: #222; --accent: #1a5276; --code-bg: #f4f4f4;
        --sidebar-bg: #263238; --sidebar-fg: #cfd8dc; --link: #1565c0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
       color: var(--fg); background: var(--bg); display: flex; min-height: 100vh; }
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
.sidebar { width: 280px; min-width: 280px; background: var(--sidebar-bg);
           color: var(--sidebar-fg); padding: 1rem; overflow-y: auto;
           position: sticky; top: 0; height: 100vh; font-size: 0.85rem; }
.sidebar h2 { color: #fff; font-size: 1.1rem; margin-bottom: 1rem; }
.sidebar h3 { color: #90caf9; font-size: 0.8rem; text-transform: uppercase;
              margin: 1rem 0 0.3rem; letter-spacing: 0.05em; }
.sidebar a { color: var(--sidebar-fg); display: block; padding: 2px 0; }
.sidebar a:hover { color: #fff; }
.sidebar .doxy-link { margin-top: 1.5rem; padding: 0.5rem;
                      background: #37474f; border-radius: 4px; text-align: center; }
.sidebar .doxy-link a { color: #4fc3f7; font-weight: bold; }
.content { flex: 1; max-width: 900px; padding: 2rem 3rem; line-height: 1.7; }
.content h1 { font-size: 1.8rem; color: var(--accent); border-bottom: 2px solid var(--accent);
              padding-bottom: 0.3rem; margin-bottom: 1rem; }
.content h2 { font-size: 1.3rem; margin-top: 1.5rem; color: #333; }
.content h3 { font-size: 1.1rem; margin-top: 1rem; }
.content p { margin: 0.5rem 0; }
.content ul, .content ol { margin: 0.5rem 0 0.5rem 1.5rem; }
.prose { margin: 1rem 0; }
pre { background: var(--code-bg); padding: 1rem; border-radius: 4px;
      overflow-x: auto; font-size: 0.85rem; line-height: 1.5;
      margin: 0.5rem 0; border-left: 3px solid var(--accent); }
code { font-family: "SF Mono", "Fira Code", Consolas, monospace; }
p code { background: var(--code-bg); padding: 1px 4px; border-radius: 3px; font-size: 0.9em; }
.doxy-ref { background: #e3f2fd; padding: 1px 5px; border-radius: 3px;
            font-family: monospace; font-size: 0.9em; }
.breadcrumb { font-size: 0.85rem; color: #666; margin-bottom: 1rem; }
.module-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
               gap: 1rem; margin-top: 1rem; }
.module-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 1rem; }
.module-card h3 { color: var(--accent); margin-bottom: 0.5rem; font-size: 1rem; }
.module-card ul { list-style: none; padding: 0; }
.module-card li { padding: 2px 0; font-size: 0.85rem; }
.mjx-container { overflow-x: auto; overflow-y: hidden; }
"""

MATHJAX = """\
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script>hljs.highlightAll();</script>
<script>
MathJax = {
  tex: {
    inlineMath: [['$', '$']],
    displayMath: [['$$', '$$']],
    processEscapes: false
  },
  options: {
    skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
  }
};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js" async></script>
"""


def parse_basilisk_h(text):
    """
    Parse a Basilisk .h file into (type, content) blocks.

    Basilisk uses /** ... */ for prose (markdown + LaTeX).
    Everything else is C code.
    """
    blocks = []
    # Match /** ... */ comment blocks
    # Split text into alternating code/prose segments
    parts = re.split(r'(/\*\*.*?\*/)', text, flags=re.DOTALL)

    for part in parts:
        if not part.strip():
            continue
        if part.startswith('/**') and part.endswith('*/'):
            # Strip the comment delimiters
            inner = part[3:-2].strip()
            if inner:
                blocks.append(('prose', inner))
        else:
            # Code — skip if only whitespace
            if part.strip():
                blocks.append(('code', part))

    return blocks


def prose_to_html(text):
    """
    Convert Basilisk prose (markdown with LaTeX) to HTML.
    Preserves $$...$$ and $...$ verbatim for MathJax to process.
    """
    # Split on $$...$$ blocks first to protect them
    parts = re.split(r'(\$\$.*?\$\$)', text, flags=re.DOTALL)
    out = []
    for part in parts:
        if part.startswith('$$') and part.endswith('$$'):
            # Display math — output as-is in a div for MathJax
            out.append(f'\n<div class="math-display">{part}</div>\n')
        else:
            out.append(render_markdown(part))
    return ''.join(out)


def render_markdown(text):
    """Render markdown prose to HTML, preserving $...$ for MathJax."""
    lines = text.split('\n')
    out = []
    in_list = False
    para_lines = []

    def flush_para():
        if para_lines:
            content = ' '.join(para_lines)
            content = inline_format(content)
            out.append(f'<p>{content}</p>')
            para_lines.clear()

    for line in lines:
        stripped = line.strip()

        if not stripped:
            flush_para()
            if in_list:
                out.append('</ul>')
                in_list = False
            continue

        # Headers
        m = re.match(r'^(#{1,4})\s+(.*)', stripped)
        if m:
            flush_para()
            level = len(m.group(1))
            out.append(f'<h{level}>{inline_format(m.group(2))}</h{level}>')
            continue

        # List items
        if stripped.startswith(('* ', '- ')):
            flush_para()
            if not in_list:
                out.append('<ul>')
                in_list = True
            out.append(f'<li>{inline_format(stripped[2:])}</li>')
            continue

        if in_list:
            out.append('</ul>')
            in_list = False

        # Regular paragraph line — accumulate
        para_lines.append(stripped)

    flush_para()
    if in_list:
        out.append('</ul>')
    return '\n'.join(out)


# ── Cross-reference tables (populated by main before page generation) ──
LITERATE_FILES = {}   # "poisson.h" → "poisson.html", "navier-stokes/centered.h" → "navier-stokes_centered.html"
LITERATE_PAGES = set()  # set of literate .html filenames that actually get generated
KNOWN_SYMBOLS = {}    # "mgstats" → doxygen URL, "prediction" → doxygen URL

# Key structs, types, and functions in Basilisk worth linking
_BASILISK_SYMBOLS = [
    # Core types
    'Grid', 'scalar', 'vector', 'tensor', 'coord', '_Attributes', 'timer',
    'mgstats', 'Point',
    # Key functions
    'init_grid', 'run', 'origin', 'size', 'boundary', 'restriction',
    'prolongation', 'refine', 'adapt_wavelet', 'output_ppm', 'output_gfs',
    'dump', 'restore', 'statsf', 'normf', 'interpolate',
    'fractions', 'curvature', 'heights',
    'prediction', 'correction', 'projection',
    'advection', 'tracer_fluxes',
    'poisson', 'mg_solve', 'residual', 'relax',
    'timestep', 'dtnext',
    'vof_advection',
    'display',
]


def build_crossref_tables(modules, src_dir):
    """Build lookup tables for cross-referencing."""
    global LITERATE_FILES, KNOWN_SYMBOLS

    # All literate file mappings
    for group, files in modules.items():
        for f in files:
            basename = os.path.basename(f)
            literate_href = f.replace('/', '_').replace('.h', '.html')
            LITERATE_FILES[basename] = literate_href
            LITERATE_FILES[f] = literate_href
            LITERATE_PAGES.add(literate_href)

    # Also scan src for all .h files not in modules
    for root, dirs, fnames in os.walk(src_dir):
        for fn in fnames:
            if fn.endswith('.h'):
                rel = os.path.relpath(os.path.join(root, fn), src_dir)
                literate_href = rel.replace('/', '_').replace('.h', '.html')
                if fn not in LITERATE_FILES:
                    LITERATE_FILES[fn] = literate_href
                if rel not in LITERATE_FILES:
                    LITERATE_FILES[rel] = literate_href

    # Symbol → Doxygen links
    for sym in _BASILISK_SYMBOLS:
        # Doxygen generates struct pages as struct_NAME.html, globals as searchable
        # For structs: structNAME.html; for functions: linked via source browser
        # We'll link to the search for simplicity and accuracy
        KNOWN_SYMBOLS[sym] = f'{DOXYGEN_REL}/search.html?query={sym}'


def crosslink_prose(text):
    """Add cross-links for .h file references and known symbols in prose text.
    Called AFTER inline_format, operates on HTML."""

    # Link bare file references like poisson.h, bcg.h, navier-stokes/centered.h
    def link_file_ref(m):
        pre = m.group(1)
        fname = m.group(2)
        href = LITERATE_FILES.get(fname)
        if href and href in LITERATE_PAGES:
            return f'{pre}<a href="{href}">{fname}</a>'
        # Fall back to basilisk.fr for files without literate pages
        return f'{pre}<a href="{BASILISK_URL}/{fname}">{fname}</a>'

    # Match word-boundary .h references (but not inside already-linked text)
    text = re.sub(r'(^|[\s(>])([a-zA-Z][\w/\-]*\.h)\b(?![^<]*</a>)', link_file_ref, text)

    # Link known symbols when they appear in <code>...</code> tags
    def link_symbol(m):
        sym = m.group(1)
        if sym in KNOWN_SYMBOLS:
            return f'<code><a class="doxy-ref" href="{KNOWN_SYMBOLS[sym]}">{sym}</a></code>'
        return m.group(0)

    text = re.sub(r'<code>(\w+)(?:\(\))?</code>', link_symbol, text)

    return text


def inline_format(text):
    """Apply inline markdown formatting, preserving $...$ for MathJax."""
    # Inline code `...` (do first to protect from other transforms)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Links [text](url)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    # Bold **...**
    text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
    # Cross-link file refs and symbols
    text = crosslink_prose(text)
    return text


def code_to_html(code):
    """Render code block with cross-links to both literate and Doxygen pages."""
    escaped = html_mod.escape(code.strip())
    if not escaped:
        return ''

    # Link #include "file.h" → literate page (primary) + Doxygen (secondary)
    def include_link(m):
        filename = m.group(1)
        doxy_name = file_to_doxygen_name(filename)
        doxy_exists = doxy_name in _DOXYGEN_FILES_SET
        lit_href = LITERATE_FILES.get(filename)
        lit_exists = lit_href and lit_href in LITERATE_PAGES

        if lit_exists and doxy_exists:
            return (f'#include &quot;<a href="{lit_href}">{html_mod.escape(filename)}</a>&quot; '
                    f'<small>[<a class="doxy-ref" href="{DOXYGEN_REL}/{doxy_name}">api</a>]</small>')
        elif lit_exists:
            return f'#include &quot;<a href="{lit_href}">{html_mod.escape(filename)}</a>&quot;'
        elif doxy_exists:
            return f'#include &quot;<a class="doxy-ref" href="{DOXYGEN_REL}/{doxy_name}">{html_mod.escape(filename)}</a>&quot;'
        else:
            return f'#include &quot;<a href="{BASILISK_URL}/{filename}">{html_mod.escape(filename)}</a>&quot;'

    escaped = re.sub(r'#include &quot;([^&]+)&quot;', include_link, escaped)
    return f'<pre><code class="language-c">{escaped}</code></pre>'


def file_to_doxygen_name(filepath):
    """Convert filepath to Doxygen's HTML filename using the actual output."""
    basename = os.path.basename(filepath)
    simple = basename.replace('.', '_8') + '.html'
    # Check if simple name exists; if not, try with directory prefix
    if _DOXYGEN_FILES_SET and simple not in _DOXYGEN_FILES_SET:
        # Doxygen uses dir_2basename format for disambiguation
        prefixed = filepath.replace('/', '_2').replace('.', '_8') + '.html'
        if prefixed in _DOXYGEN_FILES_SET:
            return prefixed
    return simple

_DOXYGEN_FILE_MAP = {}
_DOXYGEN_FILES_SET = set()

def build_doxygen_file_map(doxygen_html_dir):
    """Scan Doxygen output to build the set of existing HTML files."""
    global _DOXYGEN_FILES_SET
    if not os.path.isdir(doxygen_html_dir):
        return
    _DOXYGEN_FILES_SET = set(os.listdir(doxygen_html_dir))


def generate_sidebar(modules, current_file=None):
    parts = ['<div class="sidebar">',
             '<h2>Basilisk CFD</h2>',
             '<div><a href="index.html">← Index</a></div>',
             '<div><a href="matrix.html" style="color:#ffcc80;">⊞ Compatibility Matrix</a></div>',
             f'<div class="doxy-link"><a href="{DOXYGEN_REL}/index.html">API Reference (Doxygen)</a></div>']
    for group, files in modules.items():
        parts.append(f'<h3>{html_mod.escape(group)}</h3>')
        for f in files:
            name = os.path.basename(f)
            href = f.replace('/', '_').replace('.h', '.html')
            active = ' style="color:#fff;font-weight:bold"' if f == current_file else ''
            parts.append(f'<a href="{href}"{active}>{html_mod.escape(name)}</a>')
    parts.append('</div>')
    return '\n'.join(parts)


# ── Test case / example / dependency data (populated by scan_source) ──
FILE_TESTS = {}     # "navier-stokes/centered.h" → ["lid", "poiseuille", ...]
FILE_EXAMPLES = {}  # "navier-stokes/centered.h" → ["karman", "bubble", ...]
FILE_DEPS = {}      # "navier-stokes/centered.h" → ["run.h", "timestep.h", ...]
BASILISK_URL = "http://basilisk.fr/src"


def scan_source(src_dir, modules):
    """Scan test/ and examples/ to find which tests/examples use which headers."""
    all_headers = set()
    for group, files in modules.items():
        all_headers.update(files)

    # Scan test cases
    test_dir = os.path.join(src_dir, 'test')
    if os.path.isdir(test_dir):
        for fn in os.listdir(test_dir):
            if not fn.endswith('.c'):
                continue
            testname = fn[:-2]
            fpath = os.path.join(test_dir, fn)
            try:
                with open(fpath, 'r', errors='replace') as f:
                    content = f.read()
            except:
                continue
            for hdr in all_headers:
                if f'"{hdr}"' in content:
                    FILE_TESTS.setdefault(hdr, []).append(testname)

    # Scan examples
    ex_dir = os.path.join(src_dir, 'examples')
    if os.path.isdir(ex_dir):
        for fn in os.listdir(ex_dir):
            if not fn.endswith('.c'):
                continue
            exname = fn[:-2]
            fpath = os.path.join(ex_dir, fn)
            try:
                with open(fpath, 'r', errors='replace') as f:
                    content = f.read()
            except:
                continue
            for hdr in all_headers:
                if f'"{hdr}"' in content:
                    FILE_EXAMPLES.setdefault(hdr, []).append(exname)

    # Scan direct #include dependencies
    for hdr in all_headers:
        hpath = os.path.join(src_dir, hdr)
        if not os.path.isfile(hpath):
            continue
        try:
            with open(hpath, 'r', errors='replace') as f:
                content = f.read()
        except:
            continue
        deps = re.findall(r'#include\s+"([^"]+)"', content)
        if deps:
            FILE_DEPS[hdr] = deps

    # Sort
    for k in FILE_TESTS:
        FILE_TESTS[k].sort()
    for k in FILE_EXAMPLES:
        FILE_EXAMPLES[k].sort()


def render_tests_examples(filepath):
    """Render test case and example links for a file."""
    parts = []
    tests = FILE_TESTS.get(filepath, [])
    examples = FILE_EXAMPLES.get(filepath, [])
    deps = FILE_DEPS.get(filepath, [])

    if not tests and not examples and not deps:
        return ''

    if deps:
        dep_links = []
        for d in deps:
            href = LITERATE_FILES.get(d)
            if href and href in LITERATE_PAGES:
                dep_links.append(f'<a href="{href}">{d}</a>')
            else:
                dep_links.append(f'<a href="{BASILISK_URL}/{d}">{d}</a>')
        parts.append(f'<p><strong>Requires:</strong> {" · ".join(dep_links)}</p>')

    if tests:
        test_links = [f'<a href="{BASILISK_URL}/test/{t}.c">{t}</a>' for t in tests]
        parts.append(f'<p><strong>Test cases ({len(tests)}):</strong> {", ".join(test_links)}</p>')

    if examples:
        ex_links = [f'<a href="{BASILISK_URL}/examples/{e}.c">{e}</a>' for e in examples]
        parts.append(f'<p><strong>Examples ({len(examples)}):</strong> {", ".join(ex_links)}</p>')

    return f'<div style="background:#f0f7ff;border:1px solid #bbdefb;border-radius:6px;padding:12px;margin:1rem 0;">{"".join(parts)}</div>'


def generate_matrix_page(modules, src_dir):
    """Generate a solver/module compatibility matrix page."""
    sidebar = generate_sidebar(modules)

    # Build the matrix: which modules are used together in test cases
    # A module pair is "compatible" if at least one test uses both
    all_headers = []
    for group, files in modules.items():
        all_headers.extend(files)

    # Scan all test+example files for co-occurrence
    cooccur = {}  # (h1, h2) → count
    test_dir = os.path.join(src_dir, 'test')
    ex_dir = os.path.join(src_dir, 'examples')

    for d in [test_dir, ex_dir]:
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if not fn.endswith('.c'):
                continue
            fpath = os.path.join(d, fn)
            try:
                with open(fpath, 'r', errors='replace') as f:
                    content = f.read()
            except:
                continue
            used = [h for h in all_headers if f'"{h}"' in content]
            for i, h1 in enumerate(used):
                for h2 in used[i+1:]:
                    pair = tuple(sorted([h1, h2]))
                    cooccur[pair] = cooccur.get(pair, 0) + 1

    # Pick the key solvers for the matrix (not all 86 headers)
    key_solvers = [
        "navier-stokes/centered.h", "navier-stokes/mac.h", "navier-stokes/stream.h",
        "saint-venant.h", "layered/hydro.h", "all-mach.h", "compressible.h",
        "two-phase.h", "vof.h", "tension.h", "advection.h",
        "poisson.h", "diffusion.h", "log-conform.h",
        "axi.h", "embed.h",
    ]
    key_solvers = [h for h in key_solvers if h in all_headers]

    short = lambda h: os.path.basename(h).replace('.h', '')

    # Build HTML table
    header_cells = ''.join(f'<th style="writing-mode:vertical-lr;transform:rotate(180deg);padding:4px;font-size:0.75rem;">{short(h)}</th>' for h in key_solvers)
    rows = []
    for h1 in key_solvers:
        cells = []
        for h2 in key_solvers:
            if h1 == h2:
                cells.append('<td style="background:#1a5276;color:#fff;text-align:center;">—</td>')
            else:
                pair = tuple(sorted([h1, h2]))
                count = cooccur.get(pair, 0)
                if count > 5:
                    cells.append(f'<td style="background:#2e7d32;color:#fff;text-align:center;" title="{count} test/examples">{count}</td>')
                elif count > 0:
                    cells.append(f'<td style="background:#c8e6c9;text-align:center;" title="{count} test/examples">{count}</td>')
                else:
                    cells.append('<td style="background:#fafafa;text-align:center;color:#ccc;">·</td>')
        rows.append(f'<tr><td style="font-size:0.8rem;white-space:nowrap;padding-right:8px;"><a href="{LITERATE_FILES.get(h1, "#")}">{short(h1)}</a></td>{"".join(cells)}</tr>')

    table = f"""<table style="border-collapse:collapse;font-size:0.85rem;">
<tr><th></th>{header_cells}</tr>
{''.join(rows)}
</table>"""

    legend = """<p style="font-size:0.8rem;margin-top:0.5rem;">
<span style="background:#2e7d32;color:#fff;padding:2px 6px;">N</span> = used together in N test cases/examples (dark green = 6+)
<span style="background:#c8e6c9;padding:2px 6px;">N</span> = 1–5
<span style="color:#ccc;">·</span> = not seen together
</p>"""

    # Also build a "what works with what" quick reference
    combos = []
    for (h1, h2), count in sorted(cooccur.items(), key=lambda x: -x[1])[:30]:
        s1, s2 = short(h1), short(h2)
        combos.append(f'<tr><td><a href="{LITERATE_FILES.get(h1, "#")}">{s1}</a></td>'
                       f'<td><a href="{LITERATE_FILES.get(h2, "#")}">{s2}</a></td>'
                       f'<td>{count}</td></tr>')

    top_table = f"""<table style="border-collapse:collapse;font-size:0.85rem;margin-top:1rem;">
<tr><th style="text-align:left;padding-right:1rem;">Module A</th><th style="text-align:left;padding-right:1rem;">Module B</th><th>Used together</th></tr>
{''.join(combos)}
</table>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Module Compatibility Matrix — Basilisk CFD</title>
<style>{CSS}</style>
{MATHJAX}
</head>
<body>
{sidebar}
<div class="content" style="max-width:1100px;">
<div class="breadcrumb"><a href="index.html">Index</a> / Compatibility Matrix</div>
<h1>Module Compatibility Matrix</h1>
<p>This matrix shows which Basilisk modules are used together in test cases and examples.
A number means that many test/example files include both modules — a strong signal they work together.</p>
{table}
{legend}
<h2>Top Module Combinations</h2>
<p>Most frequently co-used module pairs across all tests and examples:</p>
{top_table}
</div>
</body>
</html>"""


def generate_file_page(filepath, src_dir, modules):
    full_path = os.path.join(src_dir, filepath)
    if not os.path.isfile(full_path):
        return None

    with open(full_path, 'r', errors='replace') as f:
        text = f.read()

    blocks = parse_basilisk_h(text)
    sidebar = generate_sidebar(modules, filepath)
    basename = os.path.basename(filepath)
    doxy_file = file_to_doxygen_name(filepath)

    body_parts = [
        f'<div class="breadcrumb"><a href="index.html">Index</a> / {html_mod.escape(filepath)}</div>',
        f'<h1>{html_mod.escape(basename)}</h1>',
        f'<p>📄 <a class="doxy-ref" href="{DOXYGEN_REL}/{doxy_file}">View in API Reference (Doxygen)</a> · ',
        f'<a href="http://basilisk.fr/src/{filepath}">View on basilisk.fr</a></p>',
        render_tests_examples(filepath),
    ]

    for btype, content in blocks:
        if btype == 'prose':
            body_parts.append(f'<div class="prose">{prose_to_html(content)}</div>')
        else:
            body_parts.append(code_to_html(content))

    content_html = '\n'.join(body_parts)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html_mod.escape(basename)} — Basilisk CFD Documentation</title>
<style>{CSS}</style>
{MATHJAX}
</head>
<body>
{sidebar}
<div class="content">
{content_html}
</div>
</body>
</html>"""


def generate_index(modules, src_dir):
    sidebar = generate_sidebar(modules)
    cards = []
    for group, files in modules.items():
        items = []
        for f in files:
            full = os.path.join(src_dir, f)
            href = f.replace('/', '_').replace('.h', '.html')
            name = os.path.basename(f)
            if os.path.isfile(full):
                items.append(f'<li><a href="{href}">{html_mod.escape(name)}</a></li>')
            else:
                items.append(f'<li><span style="color:#999">{html_mod.escape(name)}</span></li>')
        cards.append(f'<div class="module-card"><h3>{html_mod.escape(group)}</h3><ul>{"".join(items)}</ul></div>')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Basilisk CFD — Literate Documentation</title>
<style>{CSS}</style>
{MATHJAX}
</head>
<body>
{sidebar}
<div class="content">
<h1>Basilisk CFD — Literate Documentation</h1>
<p>This site presents Basilisk's source files as literate documents — prose and code
side by side, as the authors intended. Every file links to the
<a href="{DOXYGEN_REL}/index.html">Doxygen API Reference</a> for struct hierarchies,
call graphs, include dependency diagrams, and cross-referenced source.</p>
<div class="module-grid">
{''.join(cards)}
</div>
</div>
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--src', default='./basilisk/src')
    parser.add_argument('--doxygen-html', default='./output/html')
    parser.add_argument('--out', default='./output/literate')
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    # Build cross-reference tables before generating pages
    build_crossref_tables(MODULES, args.src)
    build_doxygen_file_map(args.doxygen_html)
    scan_source(args.src, MODULES)
    print(f"Cross-refs: {len(LITERATE_FILES)} files, {len(KNOWN_SYMBOLS)} symbols")
    print(f"Test links: {sum(len(v) for v in FILE_TESTS.values())} across {len(FILE_TESTS)} headers")
    print(f"Example links: {sum(len(v) for v in FILE_EXAMPLES.values())} across {len(FILE_EXAMPLES)} headers")

    with open(os.path.join(args.out, 'index.html'), 'w') as f:
        f.write(generate_index(MODULES, args.src))

    with open(os.path.join(args.out, 'matrix.html'), 'w') as f:
        f.write(generate_matrix_page(MODULES, args.src))
    print("Generated matrix.html")
    print("Generated index.html")

    count = 0
    for group, files in MODULES.items():
        for filepath in files:
            page = generate_file_page(filepath, args.src, MODULES)
            if page:
                out_name = filepath.replace('/', '_').replace('.h', '.html')
                with open(os.path.join(args.out, out_name), 'w') as f:
                    f.write(page)
                count += 1
                print(f"  {filepath}")

    print(f"\nGenerated {count} literate pages → {args.out}/")


if __name__ == '__main__':
    main()
