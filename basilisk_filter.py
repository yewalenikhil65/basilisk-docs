#!/usr/bin/env python3
"""
Basilisk C → Standard C filter for Doxygen.

Transforms Basilisk-specific syntax into parseable C while:
- Converting LaTeX math ($...$, $$...$$) to Doxygen math (\f$...\f$, \f[...\f])
- Converting Basilisk iterators, events, type qualifiers to valid C

Usage: basilisk_filter.py <filename>
"""

import sys
import re
import os


def convert_latex(text):
    """Convert $$...$$ and $...$ to Doxygen \f[...\f] and \f$...\f$ format.
    Handles multiline $$...$$ blocks."""

    # First: multiline $$...$$ → \f[...\f]
    text = re.sub(r'\$\$(.*?)\$\$', r'\\f[\1\\f]', text, flags=re.DOTALL)

    # Then: inline $...$ → \f$...\f$ (can span lines)
    def replace_inline(m):
        content = m.group(1)
        if not content.strip() or content.startswith('(') or content.startswith('{'):
            return m.group(0)
        return r'\f$' + content + r'\f$'

    text = re.sub(r'(?<!\$)\$(?!\$)(.*?)(?<!\$)\$(?!\$)', replace_inline, text, flags=re.DOTALL)

    return text


def filter_line(line):
    """Transform a single line of Basilisk C into valid C."""

    # ── Event declarations → annotated functions ──
    m = re.match(r'^(\s*)event\s+(\w+)\s*\(([^)]*)\)\s*(\{?)\s*$', line)
    if m:
        indent, name, args, brace = m.groups()
        return f'{indent}/** @brief Event: {name} ({args}) */\n{indent}void event_{name} (void) {brace}'

    # ── foreach family → for loops ──
    foreach_map = {
        r'foreach\s*\(\)':          'for (int _i = 0; _i < _N; _i++) /* foreach */',
        r'foreach_face\s*\([^)]*\)':'for (int _i = 0; _i < _N; _i++) /* foreach_face */',
        r'foreach_vertex\s*\([^)]*\)':'for (int _i = 0; _i < _N; _i++) /* foreach_vertex */',
        r'foreach_dimension\s*\(\)':'for (int _d = 0; _d < dimension; _d++)',
        r'foreach_child\s*\(\)':    'for (int _c = 0; _c < 4; _c++) /* foreach_child */',
        r'foreach_leaf\s*\(\)':     'for (int _i = 0; _i < _N; _i++) /* foreach_leaf */',
        r'foreach_cell\s*\(\)':     'for (int _i = 0; _i < _N; _i++) /* foreach_cell */',
        r'foreach_fine_to_coarse\s*\(\)': 'for (int _i = 0; _i < _N; _i++)',
        r'foreach_neighbor\s*\(([^)]*)\)': r'for (int _n = 0; _n < \1; _n++)',
        r'foreach_level\s*\(([^)]*)\)': r'for (int _l = 0; _l < \1; _l++)',
        r'foreach_coarse_level\s*\(([^)]*)\)': r'for (int _l = 0; _l < \1; _l++)',
        r'foreach_boundary\s*\(([^)]*)\)': r'for (int _b = 0; _b < 1; _b++) /* boundary \1 */',
        r'foreach_cache\s*\(([^)]*)\)': r'for (int _i = 0; _i < 1; _i++) /* cache \1 */',
        r'foreach_level_or_leaf\s*\(([^)]*)\)': r'for (int _i = 0; _i < \1; _i++)',
        r'foreach_blockf\s*\([^)]*\)': '/* foreach_blockf */',
        r'foreach_block\s*\(\)': '/* foreach_block */',
    }
    for pat, repl in foreach_map.items():
        line = re.sub(r'\b' + pat, repl, line)

    # ── for (type s in list) → standard for ──
    line = re.sub(
        r'\bfor\s*\(\s*(scalar|vector|tensor)\s+(\w+)\s+in\s+([^)]+)\)',
        r'for (int _\2 = 0; _\2 < 1; _\2++) /* \1 in \3 */',
        line
    )

    # ── Type qualifiers ──
    line = re.sub(r'\(const\)\s+face\s+vector\b', 'const vector', line)
    line = re.sub(r'\(const\)\s+scalar\b', 'const scalar', line)
    line = re.sub(r'\(const\)\s+vector\b', 'const vector', line)
    line = re.sub(r'\bface\s+vector\b', 'vector', line)
    line = re.sub(r'\bvertex\s+scalar\b', 'scalar', line)

    # ── macro keyword → static inline ──
    line = re.sub(r'^(\s*)macro\s+([\w\s\*]+?)\s+(\w+)\s*\(', r'\1static inline \2 \3 (', line)

    # ── dimensional() → comment ──
    line = re.sub(r'\bdimensional\s*\(([^)]+)\)', r'/* dim: \1 */', line)

    # ── new scalar/vector → zero init ──
    line = re.sub(r'=\s*new\s+(scalar|vector|tensor)\b', r'= {0} /* new \1 */', line)

    # ── Boundary condition shorthand ──
    line = re.sub(
        r'^(\s*)(\w+)\[(right|left|top|bottom|front|back)\]\s*=\s*(neumann|dirichlet)\s*\(([^)]*)\)\s*;',
        r'\1/* BC: \2[\3] = \4(\5) */',
        line
    )

    # ── qrealloc ──
    line = re.sub(
        r'\bqrealloc\s*\((\w+),\s*([^,]+),\s*(\w+)\)',
        r'\1 = (\3 *)realloc(\1, (\2)*sizeof(\3))',
        line
    )

    # ── trash({...}) ──
    line = re.sub(r'\btrash\s*\(\{([^}]*)\}\)', r'/* trash: \1 */', line)

    return line


def filter_file(text, filepath):
    """Filter an entire file."""
    basename = os.path.basename(filepath)

    # Don't filter .md or .dox files — they're already Doxygen-native
    if filepath.endswith(('.md', '.dox')):
        return text

    header = f'/** @file {basename}\n */\n'

    # Convert LaTeX on the full text first (handles multiline $$...$$)
    text = convert_latex(text)

    # Then line-by-line transforms
    lines = text.split('\n')
    out_lines = [filter_line(l) for l in lines]
    return header + '\n'.join(out_lines)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(1)
    filepath = sys.argv[1]
    with open(filepath, 'r', errors='replace') as f:
        text = f.read()
    sys.stdout.write(filter_file(text, filepath))
