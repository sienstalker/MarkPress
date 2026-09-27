"""Core site-generation logic for MarkPress.

A site is built from a folder of Markdown files. Each file may start with a
small front-matter block:

    ---
    title: My first post
    date: 2026-09-25
    draft: false
    ---

Every file becomes one HTML page, and an index page lists them newest first.
"""
from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape

PACKAGE_DIR = Path(__file__).parent
TEMPLATE_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"

DEFAULT_SITE_TITLE = "MarkPress"
RESERVED_SLUGS = {"index", "static"}
MARKDOWN_EXTENSIONS = ["fenced_code", "tables", "toc"]

FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.DOTALL)
NON_SLUG_CHARS_RE = re.compile(r"[^a-z0-9]+")
LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
MARKUP_CHARS_RE = re.compile(r"[*_`>#]")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class Page:
    """One rendered Markdown page."""

    title: str
    slug: str
    html: str
    date: date | None = None
    summary: str = ""
    draft: bool = False
    meta: dict = field(default_factory=dict)

    @property
    def url(self) -> str:
        return f"{self.slug}.html"


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Split a document into (metadata, body). Missing front matter is fine."""
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text

    meta = {}
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Invalid front matter line (expected 'key: value'): {line!r}")
        key, value = line.split(":", 1)
        meta[key.strip().lower()] = value.strip().strip("\"'")
    return meta, text[match.end():]


def slugify(text: str) -> str:
    """Turn 'Hello, World!' into 'hello-world'."""
    slug = NON_SLUG_CHARS_RE.sub("-", text.lower()).strip("-")
    if not slug:
        raise ValueError(f"Cannot build a URL slug from {text!r}")
    return slug


def parse_date(value: str | None) -> date | None:
    """Parse an ISO date (YYYY-MM-DD). Empty values mean 'no date'."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Invalid date {value!r}: use the YYYY-MM-DD format") from None


def parse_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in {"true", "yes", "1"}


def render_markdown(body: str) -> str:
    return markdown.markdown(body, extensions=MARKDOWN_EXTENSIONS)


def make_summary(body: str, max_len: int = 160) -> str:
    """Plain-text summary from the first prose paragraph of the body."""
    for block in body.split("\n\n"):
        block = block.strip()
        if not block or block.startswith(("#", "```", "|", "<")):
            continue
        text = LINK_RE.sub(r"\1", block)
        text = MARKUP_CHARS_RE.sub("", text)
        text = WHITESPACE_RE.sub(" ", text).strip()
        if len(text) <= max_len:
            return text
        return text[:max_len].rsplit(" ", 1)[0].rstrip(",.;:") + "…"
    return ""


def load_page(path: Path) -> Page:
    """Read one Markdown file and turn it into a Page."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    try:
        meta, body = parse_front_matter(text)
        return Page(
            title=meta.get("title") or path.stem.replace("-", " ").replace("_", " ").title(),
            slug=slugify(meta.get("slug") or path.stem),
            html=render_markdown(body),
            date=parse_date(meta.get("date")),
            summary=meta.get("summary") or make_summary(body),
            draft=parse_bool(meta.get("draft")),
            meta=meta,
        )
    except ValueError as exc:
        raise ValueError(f"{path.name}: {exc}") from None


def _check_slugs(pages: list[Page]) -> None:
    seen: dict[str, str] = {}
    for page in pages:
        if page.slug in RESERVED_SLUGS:
            raise ValueError(f"Page {page.title!r} uses the reserved slug {page.slug!r}")
        if page.slug in seen:
            raise ValueError(
                f"Pages {seen[page.slug]!r} and {page.title!r} both use the slug {page.slug!r}"
            )
        seen[page.slug] = page.title


def _check_output_dir(src_dir: Path, out_dir: Path) -> None:
    """The output folder is wiped on each build, so never let it hold the sources."""
    src, out = src_dir.resolve(), out_dir.resolve()
    if out == src or out in src.parents:
        raise ValueError(f"Output folder {out_dir} would delete the source folder {src_dir}")


def build_site(
    src_dir: str | Path,
    out_dir: str | Path,
    site_title: str = DEFAULT_SITE_TITLE,
    include_drafts: bool = False,
    build_info: str | None = None,
) -> list[Page]:
    """Build the whole site and return the pages that were published."""
    src_dir, out_dir = Path(src_dir), Path(out_dir)
    if not src_dir.is_dir():
        raise FileNotFoundError(f"Source folder not found: {src_dir}")
    _check_output_dir(src_dir, out_dir)

    pages = [load_page(path) for path in sorted(src_dir.glob("*.md"))]
    if not include_drafts:
        pages = [page for page in pages if not page.draft]
    _check_slugs(pages)
    # Newest first; undated pages go last. sort() is stable, so ties keep file order.
    pages.sort(key=lambda page: page.date or date.min, reverse=True)

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html"]),
    )
    context = {"site_title": site_title, "build_info": build_info}

    page_template = env.get_template("page.html")
    for page in pages:
        html = page_template.render(page=page, **context)
        (out_dir / page.url).write_text(html, encoding="utf-8")

    index_html = env.get_template("index.html").render(pages=pages, **context)
    (out_dir / "index.html").write_text(index_html, encoding="utf-8")

    shutil.copytree(STATIC_DIR, out_dir / "static")
    return pages
