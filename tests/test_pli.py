"""
Tests for the PL/I lexer.

Covers the settled parts (comments, strings, bit/hex constants, numbers,
the NOT operator), basic structural sanity (no Error tokens on the
sample file), and spot checks on the DCL-attribute/statement-keyword/BIF
vocabulary sourced from IBM's current Enterprise PL/I for z/OS 6.2 docs
(see pli.py's module docstring for the specific page each list is drawn
from -- not exhaustively re-tested here, but a representative sample
from each of the three sourced lists).

Run with: pytest tests/test_pli.py
(requires the dev extra: pip install -e .[dev])
"""

import pathlib

import pytest
from pygments.token import (
    Comment,
    Error,
    Keyword,
    Name,
    Number,
    Operator,
    String,
    Whitespace,
)

from pygments_extensions.lexers.pli import PLILexer

SAMPLES_DIR = pathlib.Path(__file__).parent.parent / "samples" / "pli"


@pytest.fixture
def lexer():
    return PLILexer()


def _tokens_no_whitespace(lexer, text):
    return [
        (tok, val)
        for tok, val in lexer.get_tokens(text)
        if tok is not Whitespace and val.strip() != ""
    ]


def test_comment(lexer):
    toks = _tokens_no_whitespace(lexer, "/* a comment */")
    assert any(t is Comment.Multiline for t, v in toks)


def test_character_string_with_escaped_quote(lexer):
    toks = _tokens_no_whitespace(lexer, "'O''Brien'")
    assert all(t is String for t, v in toks)
    joined = "".join(v for t, v in toks)
    assert joined == "'O''Brien'"


def test_bit_string_constant(lexer):
    toks = _tokens_no_whitespace(lexer, "'10110100'B")
    assert (Number.Bin, "'10110100'B") in toks


def test_hex_string_constant(lexer):
    toks = _tokens_no_whitespace(lexer, "'1F'X")
    assert (Number.Hex, "'1F'X") in toks


def test_decimal_and_float_numbers(lexer):
    toks = _tokens_no_whitespace(lexer, "3.14")
    assert (Number.Float, "3.14") in toks
    toks = _tokens_no_whitespace(lexer, "42")
    assert (Number.Integer, "42") in toks
    toks = _tokens_no_whitespace(lexer, "1.5E10")
    assert (Number.Float, "1.5E10") in toks


def test_not_operator_matches_unicode_not_sign(lexer):
    # Settled per the module docstring: U+00AC must match unconditionally.
    toks = _tokens_no_whitespace(lexer, "¬FLAG")
    assert (Operator, "¬") in toks


def test_not_operator_matches_caret_alternate(lexer):
    toks = _tokens_no_whitespace(lexer, "^FLAG")
    assert (Operator, "^") in toks


def test_negated_comparison_operators_not_split(lexer):
    # ¬= must not tokenize as NOT("¬") followed by "=" separately.
    toks = _tokens_no_whitespace(lexer, "A ¬= B")
    assert (Operator, "¬=") in toks
    assert (Operator, "¬") not in toks


def test_bif_from_sourced_list(lexer):
    # SUBSTR: confirmed on IBM's alphabetic BIF page (see module
    # docstring for the URL).
    toks = _tokens_no_whitespace(lexer, "SUBSTR(x, 1, 4)")
    assert (Name.Builtin, "SUBSTR") in toks


def test_attribute_from_sourced_list(lexer):
    # VARYING: confirmed on IBM's "Data attributes" category index.
    toks = _tokens_no_whitespace(lexer, "DCL x CHAR(80) VARYING;")
    assert (Keyword.Type, "VARYING") in toks
    assert (Keyword.Type, "CHAR") not in toks  # "CHAR" isn't the listed
    # spelling -- IBM's list has "CHARACTER"; abbreviations aren't
    # separately confirmed, so this isn't expected to match yet.


def test_statement_keyword_from_sourced_list(lexer):
    # ALLOCATE: confirmed on IBM's "Statements and directives" index.
    toks = _tokens_no_whitespace(lexer, "ALLOCATE x;")
    assert (Keyword.Reserved, "ALLOCATE") in toks


def test_and_or_not_are_symbols_not_keywords(lexer):
    # Real correction from an earlier draft: PL/I's logical AND/OR/NOT
    # are the symbols &, |, ¬ -- not word-form keywords like "and"/"or"/
    # "not". Confirm the lexer doesn't (re-)introduce word-keyword
    # tokenization for these.
    toks = _tokens_no_whitespace(lexer, "a & b | ¬c")
    assert (Keyword.Reserved, "and") not in toks
    assert (Keyword.Reserved, "or") not in toks
    assert (Operator, "&") in toks
    assert (Operator, "|") in toks
    assert (Operator, "¬") in toks


def test_sample_file_lexes_without_error(lexer):
    sample_files = list(SAMPLES_DIR.glob("*.pli"))
    assert sample_files, "expected at least one sample file"
    for path in sample_files:
        text = path.read_text(encoding="utf-8")
        toks = list(lexer.get_tokens(text))
        error_toks = [(t, v) for t, v in toks if t is Error]
        assert not error_toks, f"Error tokens in {path.name}: {error_toks}"
