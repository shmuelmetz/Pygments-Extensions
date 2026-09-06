"""
Tests for the NetRexx lexer.

Run with: pytest tests/test_netrexx.py
(requires the dev extra: pip install -e .[dev])

Most fragments here are taken verbatim (or near-verbatim) from the
official NetRexx Tutorial (netrexx.org/Tutorial/nr_6.html and
nr_11.html) or the NetRexx Language Reference (NRL) -- see netrexx.py's
module docstring for the full citation history. The
"Real-world validation" section below that point in this file adds
this project's own real-world-corpus validation pass (2026-09-06,
against the NetRexx project's own reference-implementation source
tree) -- see netrexx.py's module docstring for what that pass found
and fixed. `test_sample_files_lex_without_error` below is the same
kind of corpus check OORexxLexer/PLILexer both have.
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
    Text,
    Whitespace,
)

from pygments_extensions.lexers.netrexx import NetRexxLexer

SAMPLES_DIR = pathlib.Path(__file__).parent.parent / "samples" / "netrexx"


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
    # NRL Sec 6.3: NetRexx symbols are letters/digits/_/$/euro (plus
    # Unicode "extra letters"/"extra digits", see
    # test_unicode_extra_letters_and_digits below) -- unlike classic
    # Rexx/ooRexx, "# ! ?" are NOT symbol characters. "@" is excluded
    # too, but for a more specific reason since 2026-09-06: it's the
    # NRL Sec 4.1 annotation marker (see test_annotation_* below), not
    # a symbol character or a stray Error -- "a#b" stays the plain
    # negative case for the ooRexx-extras charset itself.
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "a#b")
    assert (Text, "a#b") not in toks
    assert (Text, "a") in toks
    assert (Text, "b") in toks


# --- Real-world validation, 2026-09-06 (see netrexx.py's module
# docstring "Real-world validation" section for the full corpus and
# the exact files each of these was drawn from) ---


def test_shebang_first_line():
    # NRL Sec 3.3.2 "Shebang" (5.10-BETA): "#!" as the true first line
    # is ignored by the translator. Real form, from the project's own
    # examples/rexxtry.nrx: "#!/usr/bin/env nr".
    lexer = NetRexxLexer()
    text = "#!/usr/bin/env nr\nsay 'hi'\n"
    toks = list(lexer.get_tokens(text))
    assert toks[0] == (Comment.Hashbang, "#!/usr/bin/env nr\n")
    assert (Keyword.Reserved, "say") in toks


def test_shebang_only_recognized_on_true_first_line():
    # A "#!" on any later line is NOT a shebang (NRL: "the first line
    # in a script") -- confirms the "\A" anchor, not "^", is doing the
    # work, since this lexer otherwise runs under re.MULTILINE.
    lexer = NetRexxLexer()
    text = "say 'hi'\n#!/usr/bin/env nr\n"
    toks = list(lexer.get_tokens(text))
    assert (Comment.Hashbang, "#!/usr/bin/env nr\n") not in toks


def test_annotation_bare():
    # NRL Sec 4.1: "@Override" etc. Real form, from
    # examples/new-3.06/annotations/AnnotateTest.nrx.
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(NetRexxLexer(), "@Override")
    assert toks == [(Name.Decorator, "@Override")]


def test_annotation_with_arguments_passed_through():
    # NRL Sec 4.1: "is passed through unchanged" -- the parenthesized
    # argument expression (here a plain string literal) isn't part of
    # the annotation's own token, it just falls through to the
    # existing operator/string rules. Real form (values changed),
    # from the same AnnotateTest.nrx: '@Author(name="Class Author")'.
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, '@Author(name="Class Author")')
    assert toks[0] == (Name.Decorator, "@Author")
    assert (Operator, "(") in toks
    assert (String, '"') in toks
    assert (String, "Class Author") in toks


def test_unicode_extra_letters_and_digits():
    # NRL Sec 3.3.3 (5.10-BETA): "Implementations may also allow other
    # alphabetic and numeric characters in symbols... known as extra
    # letters and extra digits." Real forms, from
    # src/org/netrexx/diag/DiagUTF8.nrx: a symbol containing an
    # Arabic-Indic digit character (not at the start, since NRL Sec
    # 3.3.3 draws the same letter-starts/digit-continues distinction
    # for extra characters as for the plain-ASCII case), and a numeric
    # literal written entirely in Arabic-Indic digits.
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "foo١")
    assert toks == [(Text, "foo١")]

    toks = _tokens_no_whitespace(lexer, "num=١١")
    assert (Number, "١١") in toks


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


def test_loop_control_keywords():
    # NRL Sec 25 "Loop instruction": to, by, for, while, until, forever,
    # over, label, protect are all real keywords.
    lexer = NetRexxLexer()
    text = "loop label pooks i=1 to 10 by 2 for 5 while j<3 until k>9\n"
    toks = _tokens_no_whitespace(lexer, text)
    for kw in ("loop", "label", "to", "by", "for", "while", "until"):
        assert (Keyword.Reserved, kw) in toks, f"missing keyword {kw!r}"


def test_do_catch_finally_keywords():
    # NRL Sec 19 "Do instruction".
    lexer = NetRexxLexer()
    text = "do\n  catch e = Exception\nfinally\nend\n"
    toks = _tokens_no_whitespace(lexer, text)
    assert (Keyword.Reserved, "catch") in toks
    assert (Keyword.Reserved, "finally") in toks


def test_numeric_instruction_keywords():
    # NRL Sec 28 "Numeric instruction".
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "numeric digits 20\n")
    assert (Keyword.Reserved, "numeric") in toks
    assert (Keyword.Reserved, "digits") in toks


def test_nop_import_package_keywords():
    lexer = NetRexxLexer()
    for text, kw in (
        ("nop\n", "nop"),
        ("import java.lang.String\n", "import"),
        ("package testpackage\n", "package"),
    ):
        toks = _tokens_no_whitespace(lexer, text)
        assert (Keyword.Reserved, kw) in toks


def test_class_visibility_and_modifier_keywords():
    # NRL Sec 18.1/18.2 -- shared/adapter/interface are real; confirms
    # the corrected _DECLARATION_KEYWORDS set.
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(
        lexer, "class Foo shared adapter\n"
    )
    assert (Keyword.Declaration, "shared") in toks
    assert (Keyword.Declaration, "adapter") in toks


def test_protected_is_not_a_keyword():
    # CORRECTION: "protected" is Java/ooRexx, not NetRexx -- confirmed
    # absent from NRL Sec 18.1/26.2/32.1's real visibility-word lists
    # (private/public/shared/inheritable).
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "method foo protected\n")
    assert (Keyword.Declaration, "protected") not in toks
    assert (Keyword.Reserved, "protected") not in toks


def test_call_and_arg_are_not_keywords():
    # CORRECTION: NetRexx has no classic-Rexx CALL instruction (NRL
    # Sec 9.1: a method invocation is itself the instruction). "arg" is
    # explicitly stated NOT to be a keyword (NRL Sec 31 footnote).
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "call = 1\narg = 2\n")
    assert (Keyword.Reserved, "call") not in toks
    assert (Keyword.Reserved, "arg") not in toks


def test_select_case_keyword():
    # NRL Sec 35.3 "Case phrase".
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "select case i+1\nend\n")
    assert (Keyword.Reserved, "case") in toks


def test_trace_sub_keywords():
    # NRL Sec 37 "Trace instruction".
    lexer = NetRexxLexer()
    for word in ("all", "methods", "off", "results", "var"):
        toks = _tokens_no_whitespace(lexer, f"trace {word}\n")
        assert (Keyword.Reserved, word) in toks, f"missing {word!r}"


def test_dependent_class_modifier():
    # NRL Sec 39.2 "Dependent classes".
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "class Foo.Dep dependent\n")
    assert (Keyword.Declaration, "dependent") in toks


def test_special_names_are_pseudo_not_reserved():
    # NRL Sec 40.1: special names are explicitly NOT reserved --
    # "they may be used as variable names instead, if desired."
    # CORRECTION: this/super were wrongly Keyword.Reserved in the
    # first pass; they belong here with the rest of the special names.
    lexer = NetRexxLexer()
    for word in ("ask", "asknoecho", "length", "this", "super",
                 "version", "parent", "source"):
        toks = _tokens_no_whitespace(lexer, f"{word}\n")
        assert (Keyword.Pseudo, word) in toks, f"{word!r} -> {toks}"
        assert (Keyword.Reserved, word) not in toks


def test_new_is_not_a_keyword():
    # CORRECTION: "new" was never verified and is now positively
    # contradicted -- every NRL constructor example (Sec 9.5, Sec 39)
    # uses ClassName(args), never a "new" operator.
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "x = new\n")
    assert (Keyword.Reserved, "new") not in toks
    assert (Keyword.Pseudo, "new") not in toks


def test_more_special_names_are_pseudo():
    # NRL Sec 40.1, continued: null, RC, sourceline are also
    # documented special names, not reserved words.
    lexer = NetRexxLexer()
    for word in ("null", "RC", "sourceline"):
        toks = _tokens_no_whitespace(lexer, f"{word}\n")
        assert (Keyword.Pseudo, word) in toks, f"{word!r} -> {toks}"


def test_builtin_method_calls():
    # NRL Sec 48, full list. A sample spanning the alphabet, not
    # exhaustive -- the full 48-entry list is in _BUILTIN_METHODS.
    lexer = NetRexxLexer()
    for method in ("abbrev", "datatype", "left", "strip", "x2d"):
        toks = _tokens_no_whitespace(lexer, f"n = s.{method}(1)\n")
        assert (Name.Builtin, method) in toks, f"{method!r} -> {toks}"


def test_length_stays_special_name_not_builtin():
    # "length" is deliberately excluded from _BUILTIN_METHODS -- NRL
    # Sec 40.1 documents it as a special name (array/string length),
    # already covered there; not duplicated into Name.Builtin too.
    lexer = NetRexxLexer()
    toks = _tokens_no_whitespace(lexer, "n = s.length\n")
    assert (Keyword.Pseudo, "length") in toks
    assert (Name.Builtin, "length") not in toks


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


def test_sample_files_lex_without_error(lexer):
    # Real-world corpus check, matching OORexxLexer's/PLILexer's own
    # (see tests/test_oorexx.py's test_sample_files_lex_without_error).
    # Covers samples/netrexx/real-world/from-netrexx-project/ -- see
    # that directory's README.md and this module's "Real-world
    # validation" section above for what this found and fixed.
    sample_files = list(SAMPLES_DIR.rglob("*.nrx"))
    assert sample_files, "expected at least one sample file"
    for path in sample_files:
        text = path.read_text(encoding="utf-8")
        toks = list(lexer.get_tokens(text))
        error_toks = [(t, v) for t, v in toks if t is Error]
        assert not error_toks, f"Error tokens in {path}: {error_toks}"
