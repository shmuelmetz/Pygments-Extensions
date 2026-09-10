"""
Tests for the NetRexx Pipelines lexer.

Run with: pytest tests/test_netrexx_pipelines.py
(requires the dev extra: pip install -e .[dev])

NetRexx Pipelines is a separate language from NetRexx proper -- a pipe
specification (`.njp`) is its own syntax, compiled to NetRexx by its
own compiler (the HTML/CSS relationship J. Leslie Turriff drew on the
rexxla-members thread this lexer answered). See
`netrexx_pipelines.py`'s module docstring for scope and sourcing.

`test_sample_files_lex_without_error` below is the same corpus check
OORexxLexer/PLILexer/NetRexxLexer all have.
"""

import pathlib

import pytest
from pygments.token import Comment, Error, Name, Number, Operator, String

from pygments_extensions.lexers.netrexx_pipelines import NetRexxPipelinesLexer

SAMPLES_DIR = pathlib.Path(__file__).parent.parent / "samples" / "netrexx-pipelines"


@pytest.fixture
def lexer():
    return NetRexxPipelinesLexer()


def _tokens(lexer, text):
    return [(t, v) for t, v in lexer.get_tokens(text) if v.strip()]


def test_minimal_pipe_spec(lexer):
    # The baseline shape from the Pipelines Guide's own firstsample.njp.
    toks = _tokens(lexer, "pipe (hello) literal hello world | console\n")
    assert (Name.Builtin.Pseudo, "pipe") in toks
    assert (Name.Builtin, "literal") in toks
    assert (Operator, "|") in toks
    assert (Name.Builtin, "console") in toks


def test_addpipe_is_recognized(lexer):
    toks = _tokens(lexer, "addpipe (x) literal a | console\n")
    assert (Name.Builtin.Pseudo, "addpipe") in toks


def test_label_and_fanin_connector(lexer):
    # o: ... | ... ? -- labels mark a fan-in point a later '?' connects
    # back to (all_tests1.njp, aggrc_tests1.njp).
    toks = _tokens(lexer, "pipe (p)\n o: faninany |\n    sort |\n    cons ?\n")
    assert (Name.Label, "o") in toks
    assert (Name.Label, "?") in toks


def test_stage_abbreviation_still_reads_as_stage(lexer):
    # Stages resolve by minimum unambiguous abbreviation; a documented
    # alias from stages.db is Name.Builtin, an unknown identifier plain.
    toks = _tokens(lexer, "pipe (p) literal x | cons\n")
    assert (Name.Builtin, "cons") in toks
    toks = _tokens(lexer, "pipe (p) literal x | zzznotastage\n")
    assert (Name, "zzznotastage") in toks


def test_delimiter_quoted_literal(lexer):
    # The option's own first character is its closing delimiter, same
    # free-delimiter convention as classic Rexx PARSE.
    toks = _tokens(lexer, "pipe (p) literal x | locate /abc/ | console\n")
    assert (String, "/abc/") in toks
    toks = _tokens(lexer, "pipe (p) literal x | locate ~abc~ | console\n")
    assert (String, "~abc~") in toks


def test_column_range_star(lexer):
    toks = _tokens(lexer, "pipe (p) literal x | specs 2-* 1 | console\n")
    assert (Number, "*") in toks


def test_both_comment_forms(lexer):
    toks = _tokens(lexer, "-- a line comment\npipe (p) literal x | console\n")
    assert any(t is Comment.Single for t, _ in toks)
    toks = _tokens(lexer, "/* block\n   comment */\npipe (p) literal x | console\n")
    assert any(t is Comment.Multiline for t, _ in toks)


def test_box_drawing_inside_block_comment_is_not_operators(lexer):
    # abbrev_tests1.njp has a railroad-diagram comment full of | - +;
    # none of it may leak out as pipeline operators. The only real
    # pipeline separator here is the one on the last line.
    src = (
        "/*\n  >>--STAGE--+---|---+--><\n          '-arg-'\n*/\n"
        "pipe (p) literal x | console\n"
    )
    toks = list(lexer.get_tokens(src))
    assert [v for t, v in toks if t is Operator and v == "|"] == ["|"]


def test_sample_files_lex_without_error(lexer):
    # Real-world corpus check, matching the other lexers' own. Covers
    # samples/netrexx-pipelines/real-world/from-netrexx-project/ -- see
    # that directory's README.md for provenance and what the 232-file
    # smoke test behind it covered.
    sample_files = list(SAMPLES_DIR.rglob("*.njp"))
    assert sample_files, "expected at least one sample file"
    for path in sample_files:
        text = path.read_text(encoding="utf-8")
        toks = list(lexer.get_tokens(text))
        error_toks = [(t, v) for t, v in toks if t is Error]
        assert not error_toks, f"Error tokens in {path}: {error_toks}"
