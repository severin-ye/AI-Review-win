# 把 docs/handover 的两份手册 md → 带样式的 HTML（供 Electron printToPDF）
import re
from pathlib import Path
from markdown_it import MarkdownIt

CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; font-size: 11pt;
       line-height: 1.75; color: #1f2937; max-width: 170mm; margin: 0 auto; }
h1 { font-size: 20pt; color: #1e3a8a; border-bottom: 3px solid #4f46e5; padding-bottom: 8px; }
h2 { font-size: 14pt; color: #1e3a8a; margin-top: 1.6em; border-left: 5px solid #4f46e5; padding-left: 10px; }
h3 { font-size: 12pt; color: #374151; margin-top: 1.3em; }
code { background: #f1f5f9; padding: 1px 5px; border-radius: 4px; font-family: Consolas, monospace; font-size: 9.5pt; }
pre { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; overflow-x: auto; }
pre code { background: none; padding: 0; }
blockquote { border-left: 4px solid #f59e0b; background: #fffbeb; margin: 0; padding: 8px 14px; border-radius: 0 6px 6px 0; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 10pt; }
th, td { border: 1px solid #cbd5e1; padding: 7px 10px; text-align: left; }
th { background: #eef2ff; }
tr:nth-child(even) { background: #f8fafc; }
hr { border: none; border-top: 1px solid #e2e8f0; margin: 24px 0; }
strong { color: #111827; }
a { color: #4f46e5; text-decoration: none; }
"""

md = MarkdownIt("commonmark", {"html": True, "breaks": False}).enable("table")

for name in ["老板使用手册", "员工使用手册"]:
    src = Path(f"docs/handover/{name}.md")
    html_body = md.render(src.read_text(encoding="utf-8"))
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8">
<title>{name}</title><style>{CSS}</style></head>
<body>{html_body}</body></html>"""
    out = Path(f"docs/handover/.{name}.html")
    out.write_text(html, encoding="utf-8")
    print("HTML:", out, len(html), "bytes")
