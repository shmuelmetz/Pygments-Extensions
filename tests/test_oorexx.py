"""
Tests for the ooRexx lexer.

Run with: pytest tests/test_oorexx.py
(requires the dev extra: pip install -e .[dev])
"""

import pathlib

import pytest
from pygments.token import (
    Comment,
    Keyword,
    Name,
    Number,
    Operator,
    String,
    Text,
    Whitespace,
)

from pygments_extensions.lexers.oorexx import OORexxLexer

SAMPLES_DIR = pathlib.Path(__file__).parent.parent / "samples" / "oorexx"


@pytest.fixture
def lexer():
    return OORexxLexer()


def _tokens_no_whitespace(lexer, text):
    return [
        (tok, val)
        for tok, val in lexer.get_tokens(text)
        if tok is not Whitespace and val.strip() != ""
    ]


def test_directive_class_and_method(lexer):
    fragment = "::CLASS Point\n::METHOD init\n"
    toks = _tokens_no_whitespace(lexer, fragment)
    assert (Keyword.Namespace, "::") in toks
    assert (Keyword.Declaration, "class") in [
        (t, v.lower()) for t, v in toks if t is Keyword.Declaration
    ]
    assert (Keyword.Declaration, "method") in [
        (t, v.lower()) for t, v in toks if t is Keyword.Declaration
    ]


def test_message_send_single_tilde(lexer):
    toks = _tokens_no_whitespace(lexer, "point~toString")
    assert (Operator, "~") in toks
    assert (Name.Function, "toString") in toks


def test_message_send_double_tilde_cascade(lexer):
    toks = _tokens_no_whitespace(lexer, "obj~~foo~~bar")
    ops = [v for t, v in toks if t is Operator]
    assert ops.count("~~") == 2


def test_bracket_message_send(lexer):
    toks = _tokens_no_whitespace(lexer, "mystem[foo] = 'bar'")
    assert (Operator, "[") in toks
    assert (Operator, "]") in toks


def test_dot_class_reference(lexer):
    toks = _tokens_no_whitespace(lexer, ".array~new")
    assert (Name.Class, ".array") in toks
    # Confirm it's a single token, not split into Operator(".") + Text("array").
    assert (Operator, ".") not in toks


def test_classic_rexx_constructs_still_work(lexer):
    # ooRexx is upwardly compatible with classic Rexx -- do/end, if/then/
    # else, call, and comments must still tokenize sanely.
    fragment = "/* comment */\nif a = b then do\n  call foo\nend\n"
    toks = _tokens_no_whitespace(lexer, fragment)
    assert any(t is Comment.Multiline for t, v in toks)
    assert (Keyword.Reserved, "if") in [
        (t, v.lower()) for t, v in toks if t is Keyword.Reserved
    ]
    assert (Keyword.Reserved, "do") in [
        (t, v.lower()) for t, v in toks if t is Keyword.Reserved
    ]


def test_strings_and_numbers(lexer):
    toks = _tokens_no_whitespace(lexer, "x = 'hello' 3.14")
    assert any(t is String for t, v in toks)
    assert any(t is Number for t, v in toks)


def test_analyse_text_prefers_oorexx_for_directive(lexer):
    text = "::CLASS Foo\n::METHOD bar\n"
    assert lexer.analyse_text(text) >= 0.9


def test_analyse_text_low_for_plain_classic_rexx(lexer):
    # No ::directives, no message sends -- should not claim confidence
    # over a file that is plausibly plain classic Rexx.
    text = "/* rexx */\nsay 'hello world'\nexit\n"
    assert lexer.analyse_text(text) == 0.0


def test_analyse_text_header_comment_wins_outright(lexer):
    text = "/* ooRexx */\nsay 'hello'\n"
    assert lexer.analyse_text(text) == 1.0


def test_sample_files_lex_without_error(lexer):
    sample_files = list(SAMPLES_DIR.glob("*.rex"))
    assert sample_files, "expected at least one sample file"
    for path in sample_files:
        text = path.read_text(encoding="utf-8")
        toks = list(lexer.get_tokens(text))
        # get_tokens() should never raise; also make sure nothing fell
        # through as a raw Error token, which would indicate a character
        # the lexer's rules don't account for.
        from pygments.token import Error

        error_toks = [(t, v) for t, v in toks if t is Error]
        assert not error_toks, f"Error tokens in {path.name}: {error_toks}"
