"""Keep the delivered architecture package navigable and aligned with the DB."""

from pathlib import Path
import re
import struct
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/001-guided-notes-buzzer"
DOCUMENTS = ("architecture.md", "spec.md", "plan.md", "lld.md", "data-model.md", "traceability.md")


def test_delivered_specifications_do_not_depend_on_external_presentation():
    external_reference = re.compile(r"\.pptx?\b|簡報|D-0[1-7]|兩組共同|另一小組|對方", re.I)
    artifacts = [*SPEC.rglob("*.md"), *(ROOT / "diagrams").glob("*.puml")]
    violations = [str(path.relative_to(ROOT)) for path in artifacts
                  if external_reference.search(path.read_text(encoding="utf-8"))]
    assert not violations, "External presentation dependencies in: " + ", ".join(violations)


def test_review_package_local_links_resolve():
    failures = []
    for source in [ROOT / "README.md", *(SPEC / name for name in DOCUMENTS)]:
        text = re.sub(r"```.*?```", "", source.read_text(encoding="utf-8"), flags=re.S)
        for target in re.findall(r"!?\[[^\[\]]*\]\(([^\s)]+)\)", text):
            if "://" in target or target.startswith("#"):
                continue
            path = source.parent / unquote(target.split("#", 1)[0])
            if not path.is_file():
                failures.append(f"{source.relative_to(ROOT)}: {target}")
    assert not failures, "Missing review artifacts: " + ", ".join(failures)


def test_current_scope_requires_google_sheets_without_optional_backlog():
    documents = [path.read_text(encoding="utf-8") for path in SPEC.rglob("*.md")]
    assert not any(re.search(r"\bcsv\b", text, re.I) for text in documents)
    spec = (SPEC / "spec.md").read_text(encoding="utf-8")
    assert "Google Sheets 同步與回填" in spec
    assert "## 8. 核心功能完成狀態" in spec
    section = spec.split("## 8. 核心功能完成狀態", 1)[1].split("## 9.", 1)[0]
    assert "人工驗收" in section
    assert not any(term in section for term in ("公平順位", "題組整批", "WebSocket", "個人帳號", "跨程序", "多場同時"))


def test_every_delivered_plantuml_source_has_a_rendered_png():
    sources = list((ROOT / "diagrams").glob("*.puml"))
    assert {"component", "class", "sequence"} <= {path.stem for path in sources}
    for source in sources:
        uml = source.read_text(encoding="utf-8")
        assert uml.strip().startswith("@startuml") and uml.strip().endswith("@enduml"), source.name
        png = source.with_suffix(".png").read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n" and png[12:16] == b"IHDR", source.name
        width, height = struct.unpack(">II", png[16:24])
        assert width > 100 and height > 100, source.name


def test_data_class_diagram_and_dictionary_cover_actual_tables(app):
    with app.extensions["store"].read() as db:
        actual = {row["name"] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'",
        )}
    diagram = (ROOT / "diagrams/class.puml").read_text(encoding="utf-8")
    dictionary = (SPEC / "data-model.md").read_text(encoding="utf-8")
    assert set(re.findall(r'class "([a-z_]+)｜', diagram)) == actual
    assert set(re.findall(r"^\| ([a-z_]+) \|", dictionary, re.M)) == actual
    for table, body in re.findall(r'class "([a-z_]+)｜[^\"]+" as \w+ \{([^}]+)\}', diagram):
        diagram_fields = set()
        for declaration in re.findall(r"^\s*(.+?)\s*:", body, re.M):
            if declaration in {"PK", "unique"}:
                continue
            diagram_fields.update(name.strip() for name in declaration.split("/"))
        with app.extensions["store"].read() as db:
            schema_fields = {row["name"] for row in db.execute(f'PRAGMA table_info("{table}")')}
        assert diagram_fields == schema_fields, table
