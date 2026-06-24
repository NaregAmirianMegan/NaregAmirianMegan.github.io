#!/usr/bin/env python3
"""Build static HTML blog pages for the NVFP4 kernel-development writeup.

Source: plain-text section files in /Users/naregmegan/Desktop/Projects/nvfp4/blog
Output: static HTML pages in this website directory (pure HTML/CSS, no JS).

The text files use a light, consistent markup that this script translates:
    --- Title ---     top-level section header   -> <h2>
    -- Title --       sub-section header          -> <h3>
    -> Title          topic header                -> <h3 class="topic">
    >> note           call-out note line          -> <p class="note">
    ```  ... ```      fenced code block           -> <pre class="code">
    `code`            inline code                 -> <code>
    ---               (alone) aside delimiter      -> <aside class="callout">
    indented lines    diagrams / aligned lists     -> <pre class="diagram">
    {..} / "k": ..    benchmark data lines         -> <pre class="data">
    [Foo Details]     glossary cross-reference     -> link to glossary page
    http(s)://...     auto-linked URL

Re-run this script whenever the source text changes:  python3 build_blog.py
"""

import html
import os
import re

SRC = "/Users/naregmegan/Desktop/Projects/nvfp4/blog"
OUT = os.path.dirname(os.path.abspath(__file__))
GITHUB = "https://github.com/NaregAmirianMegan/NVFP4_Kernels"
GLOSSARY_PAGE = "nvfp4_glossary.html"

# (source file, output file, short title, one-line summary for the index)
SECTIONS = [
    ("00_introduction.txt", "nvfp4_intro.html", "Introduction",
     "What this series covers, the GPU Mode x NVIDIA competition, and a primer on the NVFP4 data type and block scaling."),
    ("01_batched_gemv.txt", "nvfp4_batched_gemv.html", "Batched GEMV",
     "Iterative optimization of a batched matrix-vector kernel: kernel fusion, split-K, coalescing, and chasing the memory-bound wall."),
    ("02_gemm.txt", "nvfp4_gemm.html", "GEMM",
     "Using tcgen05 tensor-core instructions on Blackwell, scale-factor formatting, the 'core matrix' concept, and TMA data movement."),
    ("03_dual_gemm.txt", "nvfp4_dual_gemm.html", "Dual GEMM",
     "Fusing silu(A @ B1) * (A @ B2) into a single kernel that keeps both accumulators live in TMEM."),
    ("04_group_gemm.txt", "nvfp4_group_gemm.html", "Group GEMM",
     "Fusing a group of differently-shaped GEMMs into one launch with per-tile tensormap patching and careful scheduling."),
    ("05_glossary.txt", "nvfp4_glossary.html", "Glossary",
     "Standalone reference entries for the architectural and programming concepts used throughout the series."),
    ("06_kernel_dev_optimizations.txt", "nvfp4_kernel_dev.html", "Kernel Dev Notes",
     "Process and tooling lessons: branch hygiene, tracking performance data, reading Nsight Compute for tcgen05, and using LLMs."),
    ("07_PTX_lessons.txt", "nvfp4_ptx_lessons.html", "PTX & HW Lessons",
     "The hardest-won, least-documented lessons about PTX, CUDA, and Blackwell hardware, grouped by topic."),
]

# ---------------------------------------------------------------------------
# Inline formatting
# ---------------------------------------------------------------------------

URL_RE = re.compile(r"(https?://[^\s<>\)\]]+)")
XREF_RE = re.compile(r"\[([^\]]+?\s+Details)\]")
REFNUM_RE = re.compile(r"\[(\d+)\]")


def _format_text(text):
    """Escape a plain-text run and apply non-code inline styling."""
    out = html.escape(text)
    out = URL_RE.sub(
        r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', out)
    # [Something Details] -> subtle link to the glossary page
    out = XREF_RE.sub(
        rf'<a class="xref" href="{GLOSSARY_PAGE}">[\1]</a>', out)
    # bare reference markers like [1]
    out = REFNUM_RE.sub(r'<sup class="refnum">[\1]</sup>', out)
    return out


def inline(text):
    """Render inline markup, keeping `code spans` verbatim."""
    parts = re.split(r"(`[^`]+`)", text)
    rendered = []
    for part in parts:
        if len(part) >= 2 and part.startswith("`") and part.endswith("`"):
            rendered.append(f"<code>{html.escape(part[1:-1])}</code>")
        else:
            rendered.append(_format_text(part))
    return "".join(rendered)


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "section"


# ---------------------------------------------------------------------------
# Block-level parsing
# ---------------------------------------------------------------------------

MAIN_HDR = re.compile(r"^---\s*(.+?)\s*---$")
SUB_HDR = re.compile(r"^--\s*(.+?)\s*--$")
TOPIC_HDR = re.compile(r"^->\s+(.+)$")
RULE = re.compile(r"^-{3,}$")
NUM_ITEM = re.compile(r"^\d+[\).]\s")
SPEC_ITEM = re.compile(r"^\d+b\s+-")  # e.g. "1b - Sign"
UNDERSCORE_ONLY = re.compile(r"^_+$")
SMALL_WORDS = {"and", "the", "of", "a", "an", "to", "for",
               "in", "on", "with", "vs", "or", "as", "&"}


def is_bare_header(line, nxt):
    """Detect a standalone Title-Case header that uses no dash markers.

    Conservative on purpose: short, punctuation-free, all significant words
    capitalized, no digits, and followed by a blank line. This catches headers
    like 'Competition Background' without swallowing ordinary short sentences.
    """
    s = line.strip()
    if not (0 < len(s) <= 50) or s.endswith((".", ":", ";", "?", "!", ",")):
        return False
    if nxt is not None and nxt.strip() != "":
        return False
    words = s.split()
    if not (1 <= len(words) <= 6):
        return False
    for w in words:
        if w.lower() in SMALL_WORDS:
            continue
        if w[0].isalpha() and not w[0].isupper():
            return False
    return True


def is_data_line(stripped):
    return bool(re.match(r'^[\{"]', stripped)) or "-> Mean" in stripped


def is_indented(line):
    return line.startswith("  ") and line.strip() != ""


def is_marker(stripped):
    return (stripped.startswith("```") or MAIN_HDR.match(stripped)
            or SUB_HDR.match(stripped) or stripped.startswith("-> ")
            or stripped.startswith(">> ") or RULE.match(stripped))


def render_blocks(lines):
    """Translate a list of source lines into an HTML fragment."""
    out = []
    i, n = 0, len(lines)
    first_main_seen = False

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped == "" or UNDERSCORE_ONLY.match(stripped):
            i += 1
            continue

        # --- fenced code block ---
        if stripped.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # consume closing fence
            code = html.escape("\n".join(buf))
            out.append(f'<pre class="code"><code>{code}</code></pre>')
            continue

        # --- standalone --- delimiter: aside / callout ---
        if RULE.match(stripped):
            i += 1
            buf = []
            while i < n and not RULE.match(lines[i].strip()):
                buf.append(lines[i])
                i += 1
            i += 1  # consume closing ---
            inner = render_blocks(buf)
            out.append(f'<aside class="callout">{inner}</aside>')
            continue

        # --- headers ---
        m = MAIN_HDR.match(stripped)
        if m:
            i += 1
            if not first_main_seen:
                first_main_seen = True  # page <h1> already shows the title
                continue
            title = m.group(1)
            out.append(f'<h2 id="{slugify(title)}">{inline(title)}</h2>')
            continue

        m = SUB_HDR.match(stripped)
        if m:
            title = m.group(1)
            out.append(f'<h3 id="{slugify(title)}">{inline(title)}</h3>')
            i += 1
            continue

        m = TOPIC_HDR.match(stripped)
        if m:
            title = m.group(1)
            out.append(
                f'<h3 class="topic" id="{slugify(title)}">{inline(title)}</h3>')
            i += 1
            continue

        # --- call-out note (>>) : line plus any non-blank continuation ---
        if stripped.startswith(">> "):
            buf = [stripped[3:]]
            i += 1
            while i < n and lines[i].strip() != "" and not is_marker(lines[i].strip()):
                buf.append(lines[i].strip())
                i += 1
            out.append(f'<p class="note">{inline(" ".join(buf))}</p>')
            continue

        # --- indented diagram / aligned list ---
        if is_indented(line):
            buf = []
            while i < n:
                if is_indented(lines[i]):
                    buf.append(lines[i].rstrip())
                    i += 1
                elif lines[i].strip() == "" and i + 1 < n and is_indented(lines[i + 1]):
                    buf.append("")
                    i += 1
                else:
                    break
            code = html.escape("\n".join(buf))
            out.append(f'<pre class="diagram">{code}</pre>')
            continue

        # --- benchmark / shape data block ---
        if is_data_line(stripped):
            buf = []
            while i < n and lines[i].strip() != "" and is_data_line(lines[i].strip()):
                buf.append(lines[i].strip())
                i += 1
            code = html.escape("\n".join(buf))
            out.append(f'<pre class="data">{code}</pre>')
            continue

        # --- bare Title-Case header (files that use no dash markers) ---
        nxt = lines[i + 1] if i + 1 < n else None
        if is_bare_header(line, nxt):
            out.append(f'<h2 id="{slugify(stripped)}">{inline(stripped)}</h2>')
            i += 1
            continue

        # --- ordinary paragraph: join wrapped lines ---
        buf = []
        while i < n:
            s = lines[i].strip()
            if (s == "" or UNDERSCORE_ONLY.match(s) or is_marker(s)
                    or is_indented(lines[i]) or is_data_line(s)):
                break
            # keep numbered-list / spec items on their own visual line
            if buf and (NUM_ITEM.match(s) or SPEC_ITEM.match(s)):
                buf.append("" + s)  # sentinel -> <br> after escaping
            else:
                buf.append(s)
            i += 1
        paragraph = inline(" ".join(buf))
        paragraph = paragraph.replace(" ", "<br>").replace("", "<br>")
        out.append(f"<p>{paragraph}</p>")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Page templates
# ---------------------------------------------------------------------------

def site_header():
    return """    <header>
        <nav class="headernav">
            <a href="index.html" class="name">Nareg Amirian Megan</a>
            <a href="experience_education.html">Experience/Education</a>
            <a href="projects_research.html">Projects/Research</a>
            <a href="random.html">Random</a>
        </nav>
    </header>"""


def site_footer():
    return """        <div class="links">
            <a href="https://github.com/NaregAmirianMegan" target="_blank" rel="noopener noreferrer">
                <img src="media/github_logo.svg" alt="GitHub" width="28" height="28" />
            </a>
            <a href="https://linkedin.com/in/nareg-megan" target="_blank" rel="noopener noreferrer">
                <img src="media/linkedin_logo.svg" alt="LinkedIn" width="28" height="28" />
            </a>
            <a href="media/NaregAmirianMegan_Resume_2025.pdf" target="_blank" class="text-link"><b>Preview Resume</b></a>
        </div>
        <div class="contact">
            <p>Reach me at <span style="color: var(--accent);">naregmegan@gmail.com</span></p>
        </div>"""


def page(title, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} — Nareg Amirian Megan</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
{site_header()}

    <main>
{body}
    </main>
</body>
</html>
"""


def build_section(idx, src_file, out_file, title):
    with open(os.path.join(SRC, src_file), encoding="utf-8") as fh:
        raw = fh.read()
    lines = raw.split("\n")

    # Drop a leading title-only line (the <h1> already shows the section name).
    j = 0
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    if j < len(lines):
        first = lines[j].strip()
        looks_like_title = (
            MAIN_HDR.match(first)
            or (len(first) < 80 and not first.endswith((".", ":", "?", "!")))
        )
        if looks_like_title:
            lines = lines[j + 1:]

    article = render_blocks(lines)

    prev_link = ""
    if idx > 0:
        p = SECTIONS[idx - 1]
        prev_link = f'<a class="pgprev" href="{p[1]}">← {html.escape(p[2])}</a>'
    next_link = ""
    if idx < len(SECTIONS) - 1:
        nx = SECTIONS[idx + 1]
        next_link = f'<a class="pgnext" href="{nx[1]}">{html.escape(nx[2])} →</a>'

    body = f"""        <div class="blogbar">
            <a href="nvfp4_blog.html">← NVFP4 Kernels</a>
            <a href="{GITHUB}" target="_blank" rel="noopener noreferrer">View source on GitHub ↗</a>
        </div>
        <article class="post">
            <h1>{html.escape(title)}</h1>
            <p class="post-meta">NVFP4 Kernel Series · Section {idx} of {len(SECTIONS) - 1}</p>
{article}
        </article>
        <nav class="pager">
            {prev_link}
            {next_link}
        </nav>
{site_footer()}"""

    with open(os.path.join(OUT, out_file), "w", encoding="utf-8") as fh:
        fh.write(page(title, body))
    return out_file


def build_index():
    items = []
    for idx, (_src, out_file, title, summary) in enumerate(SECTIONS):
        items.append(f"""            <a class="toc-entry" href="{out_file}">
                <span class="toc-num">{idx:02d}</span>
                <span class="toc-body">
                    <span class="toc-title">{html.escape(title)}</span>
                    <span class="toc-desc">{html.escape(summary)}</span>
                </span>
            </a>""")
    toc = "\n".join(items)

    body = f"""        <article class="post">
            <h1>Diving Deeper into ML Kernel Design</h1>
            <p class="post-meta">NVFP4 on NVIDIA Blackwell · GPU Mode × NVIDIA Competition</p>
            <p>
                A detailed walkthrough of designing and optimizing machine-learning kernels for
                the NVIDIA Blackwell architecture around the new NVFP4 4-bit data type. It covers
                four kernel families — Batched GEMV, GEMM, Dual GEMM, and Group GEMM — from a
                naive baseline through aggressive optimization, plus a standalone glossary of the
                hardware and programming concepts involved and a distilled set of PTX / hardware
                lessons that the official docs tend to leave out.
            </p>
            <p>
                It is written both as a record of my own process and as a resource for anyone
                working close to the metal on Blackwell. If you spot something technically
                inaccurate, I'd genuinely like to hear about it —
                <span style="color: var(--accent);">naregmegan@gmail.com</span>.
            </p>
            <div class="blogbar standalone">
                <a href="{GITHUB}" target="_blank" rel="noopener noreferrer">View source on GitHub ↗</a>
            </div>
            <h2>Sections</h2>
            <div class="toc">
{toc}
            </div>
        </article>
{site_footer()}"""

    with open(os.path.join(OUT, "nvfp4_blog.html"), "w", encoding="utf-8") as fh:
        fh.write(page("NVFP4 Kernels", body))


def main():
    for idx, (src_file, out_file, title, _summary) in enumerate(SECTIONS):
        built = build_section(idx, src_file, out_file, title)
        print(f"built {built}")
    build_index()
    print("built nvfp4_blog.html")


if __name__ == "__main__":
    main()
