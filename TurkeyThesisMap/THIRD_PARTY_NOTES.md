# Third-party design notes

TurkeyThesisMap does not bundle or import `tuikr` or `tuik-mcp`.

The online TÜİK workflow was implemented as a dependency-free Python client after reviewing these MIT-licensed projects:

- `emraher/tuikr`: TÜİK Veri Portalı, SDMX dataflow and file catalog workflow ideas.
- `orhoncan/tuik-mcp`: TÜİK SDMX REST workflow ideas: search dataflow, inspect metadata, then fetch filtered observations.

No R, MCP, `fastmcp`, `httpx`, `uv`, `pandas`, or `openpyxl` runtime dependency is required. TurkeyThesisMap does not ship hard-coded ready datasets for the online UI; users search and filter live TÜİK dataflows.
