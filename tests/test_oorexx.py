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


def test_dot_environment_symbol_lookup(lexer):
    # A leading dot means "look this up in the environment directory",
    # not "this is a class" -- .true/.false/.nil live in the same
    # directory as .array and user-defined classes, so .array and
    # .MyClass must tokenize identically (both are the same syntactic
    # construct, a directory lookup).
    toks = _tokens_no_whitespace(lexer, ".array~new")
    assert (Name.Variable.Global, ".array") in toks
    # Confirm it's a single token, not split into Operator(".") + Text("array").
    assert (Operator, ".") not in toks

    toks = _tokens_no_whitespace(lexer, ".MyClass~new")
    assert (Name.Variable.Global, ".MyClass") in toks


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
    # Recursive glob: also covers samples/oorexx/real-world/, the
    # real-world-derived corpus gathered during the real-world
    # validation pass documented in the module docstring. Excludes
    # from-rexxla-classic-rexx/ deliberately -- those files are kept as
    # NEGATIVE cases for analyse_text() (see
    # test_real_world_classic_rexx_scores_zero below and the module
    # docstring), not as content this lexer is expected to tokenize
    # cleanly; one of them (MSGS.REX) is itself an interpreter's own
    # test fixture full of deliberately-invalid Rexx used to exercise
    # error handling, so Error tokens from OORexxLexer there are
    # expected, not a regression.
    from pygments.token import Error

    sample_files = [
        p
        for pattern in ("*.rex", "*.orx", "*.cls")
        for p in SAMPLES_DIR.rglob(pattern)
        if "from-rexxla-classic-rexx" not in p.parts
    ]
    assert sample_files, "expected at least one sample file"
    for path in sample_files:
        text = path.read_text(encoding="utf-8")
        toks = list(lexer.get_tokens(text))
        # get_tokens() should never raise; also make sure nothing fell
        # through as a raw Error token, which would indicate a character
        # the lexer's rules don't account for.
        error_toks = [(t, v) for t, v in toks if t is Error]
        assert not error_toks, f"Error tokens in {path}: {error_toks}"


def test_real_world_classic_rexx_scores_zero(lexer):
    # The classic-Rexx negative-test corpus (samples/oorexx/real-world/
    # from-rexxla-classic-rexx/, gathered specifically to validate the
    # disambiguation heuristic -- see the module docstring) must never
    # be claimed by this lexer: none of these files have any OO marker,
    # so analyse_text() must score exactly 0.0 on every one, leaving
    # classic RexxLexer as the lexer Pygments actually picks. This also
    # confirms get_tokens() itself never raises on these files, even
    # though (unlike the assertion above) it isn't required to avoid
    # Error tokens on their content.
    classic_dir = SAMPLES_DIR / "real-world" / "from-rexxla-classic-rexx"
    sample_files = list(classic_dir.glob("*"))
    assert sample_files, "expected at least one classic-Rexx sample file"
    for path in sample_files:
        text = path.read_text(encoding="utf-8")
        list(lexer.get_tokens(text))  # must not raise
        assert lexer.analyse_text(text) == 0.0, f"false positive on {path}"


# --- Regression tests for bugs found during real-world validation ---
# (see the module docstring's "Real-world validation" section for the
# corpus and sourcing behind each of these).


def test_line_comment_double_dash(lexer):
    # ooRexx Reference 5.0.0 Sec 1.10.3: "A line comment is started by
    # two subsequent minus signs (--) and ends at the end of a line."
    # Real-world form, drawn directly from the official project's own
    # samples/pipe.cls: "::method eof -- an instance method".
    fragment = "::method eof -- an instance method\n  say 1\n"
    toks = _tokens_no_whitespace(lexer, fragment)
    comment_vals = [v for t, v in toks if t is Comment.Single]
    assert comment_vals == ["-- an instance method"]
    # The comment text must not leak through as separate Operator/Text
    # tokens the way it did before this fix.
    assert (Operator, "-") not in toks


def test_shebang_line_is_hashbang_comment(lexer):
    # Standard Unix ooRexx shebang, used throughout the official
    # project's own samples/ -- must be recognized only at the very
    # start of the source (a "#" appearing later is an ordinary symbol
    # character, see test_extended_symbol_characters below).
    text = "#!/usr/bin/env rexx\nsay 'hi'\n"
    toks = list(lexer.get_tokens(text))
    assert (Comment.Hashbang, "#!/usr/bin/env rexx\n") in toks


def test_extended_symbol_characters(lexer):
    # IBM's TSO/E REXX Reference: a Rexx symbol may contain
    # "@ # $ ! ? _" in addition to letters and digits. Drawn from real
    # source: the official project's own samples/complex.cls sends a
    # "?" message (a real ooRexx idiom for conditional selection), and
    # "$"-prefixed variable names are a long-standing classic-Rexx
    # convention that ooRexx, as an upward-compatible superset, inherits.
    toks = _tokens_no_whitespace(lexer, "sign = (imaginary < 0)~?(-1, 1)")
    assert (Operator, "~") in toks
    assert (Name.Function, "?") in toks

    toks = _tokens_no_whitespace(lexer, "$count = $count + 1")
    text_vals = [v for t, v in toks if t is Text]
    assert "$count" in text_vals


def test_scoped_message_send(lexer):
    # ooRexx Reference 5.0.0 Sec 4.2.7, "Changing the Search Order for
    # Methods": a message name followed by a colon and a class symbol
    # (usually SUPER) changes the starting point of the method search.
    # Drawn directly from the official project's own samples/pipe.cls,
    # which uses this repeatedly: "self~init:super".
    toks = _tokens_no_whitespace(lexer, "self~init:super()")
    assert (Operator, "~") in toks
    assert (Name.Function, "init") in toks
    assert (Operator, ":") in toks
    assert (Text, "super") in toks
    from pygments.token import Error

    assert not [t for t, v in toks if t is Error]


def test_directive_modifier_keywords(lexer):
    # ooRexx Reference 5.0.0 Sec 3.2/3.3/3.5: PUBLIC/PRIVATE/MIXINCLASS/
    # SUBCLASS (::CLASS) and the same-word CLASS-as-modifier/PUBLIC
    # (::METHOD) are documented directive modifier keywords, not plain
    # identifiers. Drawn from the official project's own samples/
    # complex.cls ("::class Vector subclass complex public") and
    # samples/pipe.cls-style class hierarchies ("::class Stringlike
    # public mixinclass object").
    fragment = "::class Vector subclass complex public\n"
    toks = _tokens_no_whitespace(lexer, fragment)
    kw_vals = [v.lower() for t, v in toks if t is Keyword.Declaration]
    assert "subclass" in kw_vals
    assert "public" in kw_vals


def test_semicolon_statement_separator(lexer):
    # ";" is the explicit clause delimiter, letting multiple statements
    # share one physical line -- extremely common inside real ooRexx
    # method bodies (e.g. the official project's own samples/pipe.cls:
    # "self~write(counter);").
    toks = _tokens_no_whitespace(lexer, "self~write(counter); return")
    assert (Operator, ";") in toks
    from pygments.token import Error

    assert not [t for t, v in toks if t is Error]


# --- Regression tests for gaps found via cross-check against Till
# Winkler's independently-written ooRexx lexer (RexxLA members list
# thread, 2026-09). His lexer was written from the ooRexx docs rather
# than as a classic-RexxLexer fork, and covered several 5.0/5.2
# keyword forms this one didn't yet; these tests cover the ported
# subset (USE LOCAL, SELECT CASE, ADDRESS ... WITH redirection,
# condition names, ::ANNOTATE, ::OPTIONS, ::RESOURCE) plus a
# regression test for a real bug his ::OPTIONS body state had, which
# this port fixes rather than repeats.


def test_use_local_and_select_case_keywords(lexer):
    # ooRexx 5.0: USE LOCAL exposes only routine-local variables;
    # SELECT CASE is a switch-style variant of SELECT.
    toks = _tokens_no_whitespace(lexer, "use local x, y\n")
    kw_vals = [v.lower() for t, v in toks if t is Keyword.Reserved]
    assert "use" in kw_vals
    assert "local" in kw_vals

    toks = _tokens_no_whitespace(lexer, "select case x\nend\n")
    kw_vals = [v.lower() for t, v in toks if t is Keyword.Reserved]
    assert "select" in kw_vals
    assert "case" in kw_vals


def test_address_with_output_stem_keywords(lexer):
    # ooRexx 5.0: ADDRESS ... WITH lets a host-command invocation
    # redirect stdout/stderr into stems or streams.
    fragment = "address system 'dir' with output stem out. error stem err.\n"
    toks = _tokens_no_whitespace(lexer, fragment)
    kw_vals = [v.lower() for t, v in toks if t is Keyword.Reserved]
    for word in ("with", "output", "stem"):
        assert word in kw_vals, f"{word!r} not tokenized as a keyword"
    # "error" here is the redirection target, not the condition name --
    # it's covered by the _CONDITIONS/Keyword.Type rule instead (see
    # test_condition_names), so check that path rather than Reserved.
    type_vals = [v.lower() for t, v in toks if t is Keyword.Type]
    assert "error" in type_vals


def test_condition_names(lexer):
    # LOSTDIGITS/NOMETHOD/NOSTRING/USER are ooRexx additions to the
    # classic-Rexx condition set; all are valid after SIGNAL/CALL ON|OFF.
    toks = _tokens_no_whitespace(lexer, "signal on lostdigits\ncall on nomethod\n")
    type_vals = [v.lower() for t, v in toks if t is Keyword.Type]
    assert "lostdigits" in type_vals
    assert "nomethod" in type_vals


def test_annotate_directive(lexer):
    # ::ANNOTATE (5.0) was entirely unrecognized before this fix -- "::"
    # matched no rule at all (there's no bare ":" operator token), so it
    # produced Error tokens instead of being seen as a directive.
    from pygments.token import Error

    toks = _tokens_no_whitespace(lexer, '::annotate class Foo author "Jane"\n')
    assert (Keyword.Namespace, "::") in toks
    assert (Keyword.Declaration, "annotate") in [
        (t, v.lower()) for t, v in toks if t is Keyword.Declaration
    ]
    assert not [t for t, v in toks if t is Error]


def test_options_body_numbers_and_identifiers_not_char_split(lexer):
    # Regression test for a real bug in the lexer this feature was
    # ported from (Till Winkler's): its ::OPTIONS body state had no
    # identifier-or-number rule, so any value that wasn't itself a
    # recognized sub-keyword -- a digit count, a namespace name --
    # fell to a single-character catch-all and was split into one
    # token per character (e.g. "15" -> Text('1'), Text('5')). This
    # lexer's version must not repeat that: "15" and "myns" must each
    # come through as one token.
    toks = _tokens_no_whitespace(lexer, "::options digits 15 namespace myns\n")
    vals = [v for t, v in toks]
    assert "15" in vals
    assert "myns" in vals
    assert "1" not in vals
    assert "5" not in vals


def test_resource_body_is_raw_text(lexer):
    # ::RESOURCE's body is raw data, not Rexx code, terminated by a
    # line containing only "::" -- previously unhandled entirely, so
    # the body was mis-lexed as if it were ordinary source.
    from pygments.token import Error

    fragment = "::resource greeting\nHello, ~world~ this is not code\n::\nsay 1\n"
    toks = list(lexer.get_tokens(fragment))
    assert any(t is String.Other for t, v in toks)
    # The "~" inside the resource body must NOT be tokenized as a
    # message-send operator -- confirms the body is treated as raw text.
    body_region_ops = [
        v for t, v in toks if t is Operator and v == "~"
    ]
    assert not body_region_ops
    assert not [t for t, v in toks if t is Error]
