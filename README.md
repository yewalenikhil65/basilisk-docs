# Basilisk CFD Documentation Generator

API reference and literate documentation for [Basilisk](http://basilisk.fr), the adaptive Cartesian mesh PDE framework. Built from Basilisk's source code using Doxygen + custom tooling.

## 🔗 Live Documentation

- **[Literate Documentation](https://yewalenikhil65.github.io/basilisk-docs/literate/)** — prose + code + equations, start here
- **[API Reference (Doxygen)](https://yewalenikhil65.github.io/basilisk-docs/html/)** — struct hierarchies, dependency graphs, cross-referenced source
- **[Compatibility Matrix](https://yewalenikhil65.github.io/basilisk-docs/literate/matrix.html)** — which modules work together

## What this provides (that basilisk.fr doesn't)

- **Doxygen API Reference** — struct hierarchies, `#include` dependency graphs, collaboration diagrams, cross-referenced source browser, full-text search
- **Literate Documentation** — Basilisk's prose + code + rendered LaTeX equations, with cross-links to the API reference
- **Module Compatibility Matrix** — which solvers/modules are used together, based on test case analysis
- **Test & Example Links** — each module page lists its test cases and examples with direct links

## Quick Start

```bash
# Prerequisites (macOS)
brew install doxygen graphviz python3

# Build (downloads Basilisk source automatically on first run)
./build_docs.sh

# Open
open output/literate/index.html   # start here
open output/html/index.html       # API reference
```

Build takes ~15 seconds. Output is in `output/`.

## Project Structure

```
├── build_docs.sh              # One-command build
├── Doxyfile                   # Doxygen configuration
├── basilisk_filter.py         # Basilisk C → standard C preprocessor
├── generate_literate_site.py  # Literate site generator
├── mathjax_config.js          # MathJax config for Doxygen
├── header.html / footer.html  # Doxygen HTML template (adds literate backlinks)
├── doxygen-extra/
│   ├── mainpage.md            # Doxygen landing page
│   └── groups.dox             # Module groupings
└── output/                    # Generated (not committed)
    ├── html/                  # Doxygen API reference (825 pages, 496 SVGs)
    └── literate/              # Literate docs (88 pages)
```

## How it works

Basilisk C extends standard C with `foreach()`, `event`, `face vector`, `$...$` LaTeX, etc. The `basilisk_filter.py` script transforms these into valid C + Doxygen annotations so Doxygen can parse the source. The literate site generator parses `/** ... */` comment blocks and renders them with MathJax.

### Cross-referencing

All links are relative — both sites work when deployed side by side:

| Direction | How |
|-----------|-----|
| Literate → Doxygen | `[api]` links on `#include` lines, header link to API page |
| Doxygen → Literate | Footer banner: "View literate documentation for this file" |
| Literate → Literate | File references in prose and `#include` link to sibling pages |
| Literate → basilisk.fr | Files without local pages fall back to basilisk.fr |
| Doxygen internal | Source cross-refs, referenced-by, include graphs (all automatic) |

## Deploying to GitHub Pages

```bash
# After building
cp -r output docs
git add docs
git commit -m "Update documentation"
git push
# Enable GitHub Pages from docs/ folder in repo settings
```

## Updating

Re-run `./build_docs.sh` — it re-downloads the latest Basilisk tarball and regenerates everything.

## Contributing

- Add modules to the `MODULES` dict in `generate_literate_site.py`
- Add symbols to `_BASILISK_SYMBOLS` for Doxygen cross-linking
- Improve `basilisk_filter.py` for better Basilisk C → C conversion
- Enable `CALL_GRAPH = YES` / `CALLER_GRAPH = YES` in Doxyfile for function-level call graphs (adds ~10 min to build)

## License

The documentation generator scripts are GPL v2+ licensed, matching [Basilisk's license](http://basilisk.fr/src/COPYING).
