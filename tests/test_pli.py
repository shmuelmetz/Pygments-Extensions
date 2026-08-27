"""
Tests for the PL/I lexer.

Scope note: these tests cover the parts of the lexer that are settled
(comments, strings, bit/hex constants, numbers, the NOT operator) plus
basic structural sanity (no Error tokens on the sample file). They do
NOT assert on the full DCL-attribute/keyword/BIF vocabulary, since that
list is still a draft pending cross-check against the formal PL/I
standards -- see pli.py's module docstring.

Run with: pytest tests/test_pli.py
(requires the dev extra: pip install -e .[dev])
"""

import pathlib

import pytest
from pygments.token import (
    Comment,
    Error,
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


def test_sample_file_lexes_without_error(lexer):
    sample_files = list(SAMPLES_DIR.glob("*.pli"))
    assert sample_files, "expected at least one sample file"
    for path in sample_files:
        text = path.read_text(encoding="utf-8")
        toks = list(lexer.get_tokens(text))
        error_toks = [(t, v) for t, v in toks if t is Error]
        assert not error_toks, f"Error tokens in {path.name}: {error_toks}"
