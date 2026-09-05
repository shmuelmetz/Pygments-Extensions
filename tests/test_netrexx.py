"""
Tests for the NetRexx lexer.

Run with: pytest tests/test_netrexx.py
(requires the dev extra: pip install -e .[dev])

Every fragment here is taken verbatim (or near-verbatim) from the
official NetRexx Tutorial (netrexx.org/Tutorial/nr_6.html and
nr_11.html) -- see netrexx.py's module docstring for the citation.
This is a first-pass smoke-test suite covering only what's been
verified against those two pages; it is NOT the real-world-corpus
validation this project's README holds up as the readiness bar for
OORexxLexer/PLILexer.
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

from pygments_extensions.lexers.netrexx import NetRexxLexer


@pytest.fixture
def lexer():
    return NetRexxLexer()


def _tokens_no_whitespace(lexer, text):
    return [
        (tok, val)
        for tok, val in lexer.get_tokens(text)
        if tok is not Whitespace and val.strip() != ""
    ]


def test_block_comment():
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "/* a comment */\n")
    assert all(t in (Comment.Multiline,) for t, v in toks)


def test_block_comment_nests():
    # "Comments can be nested" -- NetRexx Tutorial, Language Basics.
    lexer = NetRexxLexer()
    text = "/* outer /* inner */ still outer */\nx = 1\n"
    toks = _tokens_no_whitespace(lexer, text)
    # The whole thing up to the final "*/" must be one comment run;
    # "x = 1" must appear afterward as real code, not swallowed.
    assert (Number, "1") in toks
    assert (Operator, "=") in toks


def test_line_comment():
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "x = 1 -- trailing comment\n")
    comment_vals = [v for t, v in toks if t is Comment.Single]
    assert any("trailing comment" in v for v in comment_vals)


def test_string_double_quote_doubling():
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, '"she said ""hi"""')
    assert all(t is String for t, v in toks)


def test_string_single_quote_doubling():
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "'it''s here'")
    assert all(t is String for t, v in toks)


def test_hex_escape_in_string():
    lexer = NetRexxLexer()
    # NRL Table 1 / Tutorial: '\x0D\x0A' represents CR LF.
    toks = _tokens_no_whitespace(lexer, r"'\x0D\x0A'")
    assert (String.Escape, "\\x0D") in toks
    assert (String.Escape, "\\x0A") in toks


def test_all_nine_escape_forms():
    # NRL Table 1 (p18), every form: \t \n \r \f \" \' \\ \- \0 \xhh \uhhhh
    # (that's ten sequences for nine *forms*, since \- and \0 are two
    # spellings of the same null character).
    lexer = NetRexxLexer()
    text = r"'\t\n\r\f\"\'\\\-\0\x6df'"
    toks = _tokens_no_whitespace(lexer, text)
    escapes = [v for t, v in toks if t is String.Escape]
    for expected in (
        r"\t", r"\n", r"\r", r"\f", r'\"', r"\'", r"\\",
        r"\-", r"\0", r"\x6d",
    ):
        assert expected in escapes, f"missing escape {expected!r} in {escapes}"
    # The trailing "f" after \x6d is plain string content, not part of
    # the escape.
    assert (String, "f") in toks


def test_numeric_symbol_exponent_requires_sign():
    # NRL Sec 6.3: the sign after E/e is part of the symbol and is
    # required -- 17.3E-12, 3e+12, 0.03E+9 are the NRL's own examples.
    lexer = NetRexxLexer()
    for text in ("17.3E-12", "3e+12", "0.03E+9"):
        toks = _tokens_no_whitespace(lexer, text)
        assert toks == [(Number, text)], f"{text!r} -> {toks}"


def test_hex_numeric_symbol():
    # NRL Sec 6.6: "2x81" == 129, "4xF081" == -3967. These are a single
    # numeric-symbol token, not a number followed by a stray symbol.
    lexer = NetRexxLexer()
    for text in ("2x81", "4xF081", "0x08"):
        toks = _tokens_no_whitespace(lexer, text)
        assert toks == [(Number, text)], f"{text!r} -> {toks}"


def test_binary_numeric_symbol():
    # NRL Sec 6.6: "1b0" == 0, "4b1000" == -8.
    lexer = NetRexxLexer()
    for text in ("1b0", "4b1000", "8B1000"):
        toks = _tokens_no_whitespace(lexer, text)
        assert toks == [(Number, text)], f"{text!r} -> {toks}"


def test_symbol_charset_excludes_ooRexx_extras():
    # NRL Sec 6.3: NetRexx symbols are letters/digits/_/$/euro only --
    # unlike classic Rexx/ooRexx, "@ # ! ?" are NOT symbol characters.
    # "a@b" must therefore NOT lex as one symbol token.
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "a@b")
    assert (Text, "a@b") not in toks
    assert (Text, "a") in toks
    assert (Text, "b") in toks


def test_class_header_simple():
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "class vector3d public\n")
    assert (Keyword.Declaration, "class") in toks
    assert (Name.Class, "vector3d") in toks
    assert (Keyword.Declaration, "public") in toks


def test_class_header_extends():
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(
        lexer, "class vectorLo public extends vector3d\n"
    )
    assert (Keyword.Declaration, "extends") in toks
    assert (Name.Class, "vector3d") in toks


def test_properties_section():
    lexer = NetRexxLexer()
    text = "properties public\n  xc    -- x component\n"
    toks = _tokens_no_whitespace(lexer, text)
    assert (Keyword.Declaration, "properties") in toks
    comment_vals = [v for t, v in toks if t is Comment.Single]
    assert any("x component" in v for v in comment_vals)


def test_method_header_simple():
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "method mag() public\n")
    assert (Keyword.Declaration, "method") in toks
    assert (Name.Function, "mag") in toks


def test_method_header_with_typed_params_and_returns():
    lexer = NetRexxLexer()
    text = "method add(v1=xvector, v2=xvector) public static returns xvector\n"
    toks = _tokens_no_whitespace(lexer, text)
    assert (Keyword.Declaration, "method") in toks
    assert (Name.Function, "add") in toks
    assert (Keyword.Declaration, "static") in toks
    assert (Keyword.Declaration, "returns") in toks
    # v1=xvector -- inline type annotation.
    assert (Name.Class, "xvector") in toks


def test_constructor_with_typed_params():
    lexer = NetRexxLexer()
    text = "method vector3d(x=Rexx, y=Rexx, z=Rexx) public\n"
    toks = _tokens_no_whitespace(lexer, text)
    assert (Name.Function, "vector3d") in toks
    assert (Name.Class, "Rexx") in toks


def test_main_entry_point_array_type():
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(
        lexer, "method main(arguments=String[]) public static\n"
    )
    assert (Name.Function, "main") in toks
    assert (Name.Class, "String") in toks


def test_dot_method_call_not_tilde():
    # NetRexx uses "." for method/property access (Java-style), never
    # ooRexx's "~"/"~~" message-send syntax. Confirmed via netrexx.org:
    # "n = n.abs()", "sn = s.right(2,'0')".
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "n = n.abs()\n")
    assert (Operator, ".") in toks
    assert not any(v in ("~", "~~") for t, v in toks if t is Operator)


def test_no_crash_on_full_class_snippet():
    # A fuller snippet combining several of the above constructs, per
    # the Tutorial's own vector3d example -- just checking this doesn't
    # crash or produce Error tokens, not asserting every token.
    text = (
        "class vector3d public\n"
        "properties public\n"
        "  xc    -- x component\n"
        "  yc    -- y component\n"
        "  zc    -- z component\n"
        "method vector3d(x=Rexx, y=Rexx, z=Rexx) public\n"
        "  this.xc = x\n"
        "  this.yc = y\n"
        "  this.zc = z\n"
        "method mag() public\n"
        "  return (xc*xc + yc*yc + zc*zc)\n"
    )
    lexer = NetRexxLexer()
    toks = list(lexer.get_tokens(text))
    error_toks = [v for t, v in toks if "Error" in str(t)]
    assert error_toks == []
