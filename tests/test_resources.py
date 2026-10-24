"""
Consistency checks for the dialect registry in resources/.

Run with: pytest tests/test_resources.py
"""

import json
import pathlib
import re
from importlib.metadata import entry_points

import pytest

RESOURCES = pathlib.Path(__file__).parent.parent / "resources"
DIALECTS = sorted((RESOURCES / "dialects").glob("*.json"))
REQUIRED = {"dialect", "version", "product", "doc_keys", "lexer", "status"}


def _bib_keys():
    keys = set()
    for bib in (RESOURCES / "bib").glob("*.bib"):
        keys |= set(re.findall(r"^@\w+\{([^,\s]+),", bib.read_text(encoding="utf-8"), re.M))
    return keys


def _lexer_entry_points():
    return {ep.name: ep for ep in entry_points(group="pygments.lexers")}


@pytest.mark.parametrize("path", DIALECTS, ids=lambda p: p.stem)
def test_dialect_file_is_complete(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    assert REQUIRED <= data.keys(), REQUIRED - data.keys()
    assert data["status"] in ("implemented", "planned")
    assert data["doc_keys"], "every dialect cites at least one manual"


@pytest.mark.parametrize("path", DIALECTS, ids=lambda p: p.stem)
def test_doc_keys_exist(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = set(data["doc_keys"]) - _bib_keys()
    assert not missing, missing


@pytest.mark.parametrize("path", DIALECTS, ids=lambda p: p.stem)
def test_implemented_lexer_resolves(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["status"] != "implemented":
        assert "entry_point" not in data
        return
    ep = _lexer_entry_points()[data["entry_point"]]
    assert ep.load().__name__ == data["lexer"]


def test_every_entry_point_has_a_dialect():
    named = {json.loads(p.read_text(encoding="utf-8")).get("entry_point") for p in DIALECTS}
    ours = {n for n, ep in _lexer_entry_points().items()
            if ep.value.startswith("pygments_extensions.")}
    assert ours <= named, ours - named
