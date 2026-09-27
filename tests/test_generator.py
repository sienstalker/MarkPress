from datetime import date
from pathlib import Path

import pytest

from markpress.cli import build_info_from_env, main
from markpress.generator import (
    build_site,
    load_page,
    make_summary,
    parse_bool,
    parse_date,
    parse_front_matter,
    slugify,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def write(folder: Path, name: str, text: str) -> Path:
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


# --- front matter -----------------------------------------------------------

def test_front_matter_is_parsed_and_removed():
    meta, body = parse_front_matter("---\ntitle: Hello\ndate: 2026-01-02\n---\nBody text")
    assert meta == {"title": "Hello", "date": "2026-01-02"}
    assert body == "Body text"


def test_missing_front_matter_returns_whole_text():
    meta, body = parse_front_matter("# Just a heading")
    assert meta == {}
    assert body == "# Just a heading"


def test_front_matter_strips_quotes_and_lowercases_keys():
    meta, _ = parse_front_matter('---\nTitle: "Quoted: yes"\n---\n')
    assert meta == {"title": "Quoted: yes"}


def test_invalid_front_matter_line_raises():
    with pytest.raises(ValueError, match="Invalid front matter"):
        parse_front_matter("---\nthis line has no colon\n---\nBody")


# --- small helpers ----------------------------------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        ("Hello, World!", "hello-world"),
        ("  Spaces   everywhere ", "spaces-everywhere"),
        ("CI/CD with Jenkins", "ci-cd-with-jenkins"),
        ("already-a-slug", "already-a-slug"),
    ],
)
def test_slugify(text, expected):
    assert slugify(text) == expected


def test_slugify_rejects_empty_result():
    with pytest.raises(ValueError):
        slugify("!!!")


def test_parse_date():
    assert parse_date("2026-09-25") == date(2026, 9, 25)
    assert parse_date("") is None
    assert parse_date(None) is None


def test_parse_date_rejects_bad_format():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        parse_date("25/09/2026")


@pytest.mark.parametrize("value, expected", [("true", True), ("Yes", True), ("false", False),
                                             (None, False), ("", False)])
def test_parse_bool(value, expected):
    assert parse_bool(value) is expected


def test_summary_skips_headings_and_strips_markup():
    body = "# Title\n\nA **bold** move with a [link](https://example.com)."
    assert make_summary(body) == "A bold move with a link."


def test_summary_is_truncated_at_a_word_boundary():
    summary = make_summary("word " * 100, max_len=20)
    assert summary.endswith("…")
    assert len(summary) <= 21
    assert "wor…" not in summary


# --- pages ------------------------------------------------------------------

def test_page_without_title_uses_file_name(tmp_path):
    page = load_page(write(tmp_path, "my-first_post.md", "Hello"))
    assert page.title == "My First Post"
    assert page.slug == "my-first-post"
    assert page.url == "my-first-post.html"


def test_load_page_error_names_the_file(tmp_path):
    path = write(tmp_path, "broken.md", "---\ndate: yesterday\n---\n")
    with pytest.raises(ValueError, match="broken.md"):
        load_page(path)


def test_markdown_is_rendered(tmp_path):
    page = load_page(write(tmp_path, "p.md", "## Heading\n\n| a | b |\n|---|---|\n| 1 | 2 |"))
    assert "<h2" in page.html
    assert "<table>" in page.html


# --- building the site ------------------------------------------------------

@pytest.fixture
def site(tmp_path):
    src = tmp_path / "content"
    src.mkdir()
    write(src, "old.md", "---\ntitle: Old post\ndate: 2026-01-01\n---\nOld body")
    write(src, "new.md", "---\ntitle: New post\ndate: 2026-06-01\n---\nNew body")
    write(src, "draft.md", "---\ntitle: Secret\ndraft: true\n---\nNot yet")
    return src, tmp_path / "public"


def test_build_creates_pages_index_and_static(site):
    src, out = site
    pages = build_site(src, out)
    assert [p.slug for p in pages] == ["new", "old"]
    assert (out / "index.html").is_file()
    assert (out / "new.html").is_file()
    assert (out / "static" / "style.css").is_file()


def test_index_lists_newest_first(site):
    src, out = site
    build_site(src, out)
    index = (out / "index.html").read_text(encoding="utf-8")
    assert index.index("New post") < index.index("Old post")


def test_drafts_are_skipped_unless_requested(site):
    src, out = site
    build_site(src, out)
    assert not (out / "draft.html").exists()

    build_site(src, out, include_drafts=True)
    assert (out / "draft.html").exists()


def test_rebuild_removes_stale_pages(site):
    src, out = site
    build_site(src, out)
    (src / "old.md").unlink()
    build_site(src, out)
    assert not (out / "old.html").exists()


def test_build_info_appears_in_footer(site):
    src, out = site
    build_site(src, out, build_info="Build #42")
    assert "Build #42" in (out / "index.html").read_text(encoding="utf-8")
    assert "Build #42" in (out / "new.html").read_text(encoding="utf-8")


def test_titles_are_html_escaped(tmp_path):
    src = tmp_path / "content"
    src.mkdir()
    write(src, "x.md", "---\ntitle: <script>alert(1)</script>\n---\nHi")
    build_site(src, tmp_path / "public")
    index = (tmp_path / "public" / "index.html").read_text(encoding="utf-8")
    assert "<script>" not in index
    assert "&lt;script&gt;" in index


def test_duplicate_slugs_fail_the_build(tmp_path):
    src = tmp_path / "content"
    src.mkdir()
    write(src, "a.md", "---\nslug: same\n---\nA")
    write(src, "b.md", "---\nslug: same\n---\nB")
    with pytest.raises(ValueError, match="both use the slug"):
        build_site(src, tmp_path / "public")


def test_reserved_slug_fails_the_build(tmp_path):
    src = tmp_path / "content"
    src.mkdir()
    write(src, "index.md", "Clashes with the generated index")
    with pytest.raises(ValueError, match="reserved"):
        build_site(src, tmp_path / "public")


def test_missing_source_folder_fails(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_site(tmp_path / "nope", tmp_path / "public")


@pytest.mark.parametrize("out_name", [".", "content"])
def test_output_folder_may_not_hold_the_sources(tmp_path, out_name):
    src = tmp_path / "content"
    src.mkdir()
    write(src, "a.md", "A")
    with pytest.raises(ValueError, match="would delete"):
        build_site(src, tmp_path / out_name)
    assert (src / "a.md").exists()


def test_empty_site_still_builds_an_index(tmp_path):
    src = tmp_path / "content"
    src.mkdir()
    assert build_site(src, tmp_path / "public") == []
    assert "No pages yet" in (tmp_path / "public" / "index.html").read_text(encoding="utf-8")


def test_real_content_folder_builds(tmp_path):
    """The pages shipped in content/ must always build cleanly."""
    pages = build_site(REPO_ROOT / "content", tmp_path / "public")
    assert pages
    assert all(not p.draft for p in pages)


# --- command line -----------------------------------------------------------

def test_build_info_from_env():
    assert build_info_from_env({}) is None
    assert build_info_from_env({"BUILD_NUMBER": "7"}) == "Build #7"
    env = {"BUILD_NUMBER": "7", "GIT_COMMIT": "abcdef1234567"}
    assert build_info_from_env(env) == "Build #7 (commit abcdef1)"


def test_cli_success(site, capsys):
    src, out = site
    assert main(["--src", str(src), "--out", str(out)]) == 0
    assert "Built 2 page(s)" in capsys.readouterr().out


def test_cli_reports_errors(tmp_path, capsys):
    assert main(["--src", str(tmp_path / "missing"), "--out", str(tmp_path / "out")]) == 1
    assert "error:" in capsys.readouterr().err
