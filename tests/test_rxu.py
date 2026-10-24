"""
Tests for the RXU (TUTOR) lexer.

Run with: pytest tests/test_rxu.py
(requires the dev extra: pip install -e .[dev])
"""

import pathlib

import pytest
from pygments.lexers import get_lexer_by_name, get_lexer_for_filename
from pygments.token import Error, Keyword, Name, String, Text, Whitespace

from pygments_extensions.lexers.oorexx import OORexxLexer
from pygments_extensions.lexers.rxu import RxuLexer

SAMPLES_DIR = pathlib.Path(__file__).parent.parent / "samples" / "rxu"


@pytest.fixture
def lexer():
    return RxuLexer()


def _tokens_no_whitespace(lexer, text):
    return [
        (tok, val)
        for tok, val in lexer.get_tokens(text)
        if tok is not Whitespace and val.strip() != ""
    ]


@pytest.mark.parametrize("suffix", ["Y", "P", "G", "T", "y", "t"])
def test_text_string_suffixes(lexer, suffix):
    toks = _tokens_no_whitespace(lexer, 'x = "Ñandú"' + suffix)
    assert (String, '"Ñandú"') in toks
    assert (String.Affix, suffix) in toks


@pytest.mark.parametrize(
    "literal, body, suffix",
    [
        ('"E9"U', '"E9"', "U"),
        ('"U+1F514"U', '"U+1F514"', "U"),
        ('"(Man)(Bell)"U', '"(Man)(Bell)"', "U"),
        ("'41 E9 1F514'u", "'41 E9 1F514'", "u"),
        ('"61"X', '"61"', "X"),
        ('"0110 0001"B', '"0110 0001"', "B"),
    ],
)
def test_code_string_suffixes(lexer, literal, body, suffix):
    toks = _tokens_no_whitespace(lexer, "x = " + literal)
    assert (String.Other, body) in toks
    assert (String.Affix, suffix) in toks


@pytest.mark.parametrize(
    "literal",
    [
        '"0041"U', '"U+0041"U', '"41 E9 1F514"U', '"10FFFF"U',
        '"(LATIN CAPITAL LETTER A)"U', '"(Latin capital letter A)"U',
        '"(LatincapitalletterA)"U', '"(End of line)"U',
        '"(<control-000A>)"U', '"(Man)(Bell)"U', '"41 (Bell) E9"U', '""U',
    ],
)
def test_valid_u_strings(lexer, literal):
    # Examples from the TUTOR page "New types of strings"
    toks = _tokens_no_whitespace(lexer, "x = " + literal)
    assert Error not in [t for t, _ in toks]
    assert (String.Other, literal[:-1]) in toks


@pytest.mark.parametrize(
    "literal",
    [
        '"D800"U',              # surrogate
        '"DFFF"U',              # surrogate
        '"110000"U',            # beyond U+10FFFF
        '"XYZ"U',               # not hex
        '"U+"U',                # prefix without digits
        '"(No such name)"U',    # unknown name
        '"(<control-D800>)"U',  # label for a surrogate
        '"41 )"U',              # stray parenthesis
    ],
)
def test_invalid_u_strings_are_errors(lexer, literal):
    toks = _tokens_no_whitespace(lexer, "x = " + literal)
    assert (Error, literal[:-1]) in toks
    assert (String.Affix, "U") in toks


def test_doubled_quote_inside_suffixed_string(lexer):
    toks = _tokens_no_whitespace(lexer, 'x = "say ""hi"""T')
    assert (String, '"say ""hi"""') in toks
    assert (String.Affix, "T") in toks


def test_suffix_letter_starting_a_symbol_is_abuttal(lexer):
    # "abc"Yes is "abc" abutted to the variable Yes, not a Y string
    toks = _tokens_no_whitespace(lexer, 'x = "abc"Yes')
    assert String.Affix not in [t for t, _ in toks]
    assert (Text, "Yes") in toks


def test_unsuffixed_string_unchanged(lexer):
    toks = _tokens_no_whitespace(lexer, 'x = "plain"')
    assert String.Affix not in [t for t, _ in toks]
    assert "".join(v for t, v in toks if t in String) == '"plain"'


@pytest.mark.parametrize(
    "name",
    ["Bytes", "Codepoints", "Graphemes", "Text", "C2U", "U2C", "N2P",
     "P2N", "StringType", "Unicode", "UTF8", "Encode", "Decode"],
)
def test_tutor_builtins(lexer, name):
    toks = _tokens_no_whitespace(lexer, "say " + name + "(x)")
    assert (Name.Builtin, name) in toks


def test_ooRexx_builtins_still_recognized(lexer):
    toks = _tokens_no_whitespace(lexer, "say Translate(Strip(x))")
    assert (Name.Builtin, "Translate") in toks
    assert (Name.Builtin, "Strip") in toks


def test_text_without_parenthesis_is_not_a_builtin(lexer):
    toks = _tokens_no_whitespace(lexer, "text = 1")
    assert (Name.Builtin, "text") not in toks


@pytest.mark.parametrize("value", ["BYTES", "CODEPOINTS", "GRAPHEMES", "TEXT", "NONE"])
def test_options_defaultstring(lexer, value):
    toks = _tokens_no_whitespace(lexer, "Options DefaultString " + value)
    assert (Keyword.Type, "DefaultString") in toks
    assert (Keyword.Constant, value) in toks


@pytest.mark.parametrize("value", ["PROMOTE", "DEMOTE", "LEFT", "RIGHT", "NONE"])
def test_options_coercions(lexer, value):
    toks = _tokens_no_whitespace(lexer, "options coercions " + value)
    assert (Keyword.Type, "coercions") in toks
    assert (Keyword.Constant, value) in toks


def test_ooRexx_lexer_unaffected():
    # The extensions belong to RxuLexer only
    toks = _tokens_no_whitespace(OORexxLexer(), 'x = "abc"Y')
    assert String.Affix not in [t for t, _ in toks]


def test_registered_by_alias_and_filename():
    assert isinstance(get_lexer_by_name("rxu"), RxuLexer)
    assert isinstance(get_lexer_by_name("tutor"), RxuLexer)
    assert isinstance(get_lexer_for_filename("prog.rxu"), RxuLexer)


def test_analyse_text():
    assert RxuLexer.analyse_text("Options DefaultString TEXT\nsay 1\n") == 1.0
    assert RxuLexer.analyse_text('say "(Bell)"U\n') == 0.5
    assert RxuLexer.analyse_text('say "abc"Y\n') == 0.0
    assert RxuLexer.analyse_text("::class Foo\n") == 0.0


def test_sample_files_lex_without_error(lexer):
    samples = sorted(SAMPLES_DIR.glob("*.rxu"))
    assert samples
    for path in samples:
        text = path.read_text(encoding="utf-8")
        assert Error not in [t for t, _ in lexer.get_tokens(text)], path.name
