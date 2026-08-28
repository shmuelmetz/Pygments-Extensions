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
    Text,
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


def test_not_sign_as_prefix_unary(lexer):
    # This test exercises ¬ specifically in its prefix/unary position
    # (logical NOT). ¬ genuinely ALSO has a separate, real infix
    # position with a different meaning (bitwise XOR) -- see
    # test_infix_not_sign_is_bitwise_xor below, sourced to IBM's "Bit
    # operations" page. This test only claims that the prefix use, on
    # its own, produces one clean token. ¬A must be a single "¬"
    # Operator token immediately followed by identifier A -- not
    # combined with A, and not accidentally consuming any part of it.
    toks = _tokens_no_whitespace(lexer, "¬A")
    assert toks[0] == (Operator, "¬")
    assert (Text, "A") in toks
    assert (Operator, "¬A") not in toks


def test_infix_not_sign_is_bitwise_xor(lexer):
    # ¬ genuinely has TWO distinct meanings depending on grammatical
    # position -- this is stated outright, not inferred by analogy, in
    # IBM's Enterprise PL/I 6.2 Language Reference, "Bit operations"
    # (https://www.ibm.com/docs/en/epfz/6.2.0?topic=expressions-bit-operations),
    # Table 1 "Logical operators for bit operations": ¬ is listed as
    # usable both "As prefix operator" (Yes, = logical NOT) and "As a
    # infix operator" (Yes, = bitwise exclusive-or). Confirmed by that
    # page's own worked example (Table 3), reused here as the operand
    # values: for A = '010111'B, B = '111111'B, "A ¬ B" yields
    # '101000'B. A lexer only tokenizes, it doesn't evaluate -- so this
    # test confirms standalone infix ¬ is one Operator token distinct
    # from its operands and from the unrelated ¬=/¬</¬> atomic-operator
    # family, not that pytest itself computes the XOR.
    toks = _tokens_no_whitespace(lexer, "A ¬ B")
    assert (Operator, "¬") in toks
    assert (Operator, "¬=") not in toks
    assert (Operator, "¬<") not in toks
    assert (Operator, "¬>") not in toks

    # The exact worked example from IBM's Table 3, same operand values.
    toks = _tokens_no_whitespace(lexer, "'010111'B ¬ '111111'B")
    ops = [v for t, v in toks if t is Operator]
    assert ops.count("¬") == 1


def test_not_sign_prefix_does_not_swallow_adjacent_equals(lexer):
    # The specific worry: does the bare prefix-¬ rule greedily grab a
    # following "=" that isn't actually adjacent to it in the source
    # (¬A=B has a variable name between ¬ and =, so ¬ and = must NOT
    # merge into ¬=)? Confirmed by direct token inspection, not just
    # reasoning about rule order.
    toks = _tokens_no_whitespace(lexer, "¬A=B")
    assert (Operator, "¬") in toks
    assert (Operator, "=") in toks
    assert (Operator, "¬=") not in toks


def test_negated_less_than_operator(lexer):
    # ¬< is its own atomic operator symbol ("not less than"), part of a
    # family (¬=, ¬<, ¬>) unrelated to the separate, real infix-¬-as-XOR
    # sense documented in test_infix_not_sign_is_bitwise_xor above --
    # ¬< is a distinct two-character symbol that happens to incorporate
    # the ¬ glyph, the same way "<=" is one atomic operator despite
    # containing "<". ¬< is documented alongside ¬= and ¬> in IBM's
    # "Priority of operators" table (Table 1, priority group 5) --
    # already fetched and on hand, not re-guessed.
    toks = _tokens_no_whitespace(lexer, "X ¬< Y")
    assert (Operator, "¬<") in toks
    assert (Operator, "¬") not in toks


def test_negated_greater_than_operator(lexer):
    # ¬>: its own atomic operator symbol ("not greater than"), same
    # relationship to ¬ as ¬< above. Same source as ¬< above.
    toks = _tokens_no_whitespace(lexer, "X ¬> Y")
    assert (Operator, "¬>") in toks
    assert (Operator, "¬") not in toks


def test_prefix_not_and_the_negated_relational_operators_together(lexer):
    # One expression exercising the real prefix use of ¬ (NOT) alongside
    # all three separate atomic operators that happen to incorporate its
    # glyph (¬=, ¬<, ¬>) -- confirming the lexer doesn't confuse them
    # with each other. This is deliberately NOT exercising the separate
    # infix-¬-as-XOR sense (see test_infix_not_sign_is_bitwise_xor for
    # that) -- the two facts are unrelated and both real.
    toks = _tokens_no_whitespace(lexer, "¬A & (B ¬= C) & (D ¬< E) & (F ¬> G)")
    ops = [v for t, v in toks if t is Operator]
    assert ops.count("¬") == 1  # only the genuine prefix use
    assert "¬=" in ops
    assert "¬<" in ops
    assert "¬>" in ops


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


def test_define_statement_family_covered(lexer):
    # DEFINE/ALIAS/STRUCTURE/ORDINAL: user-flagged double-check that a
    # real but lesser-known PL/I addition wasn't missed. All four words
    # are covered (DEFINE/ALIAS via the keyword list, STRUCTURE/ORDINAL
    # via the attribute list, since those two are also attribute names
    # in their own right) -- split across two token types, but every
    # word highlights as something other than plain Text.
    toks = _tokens_no_whitespace(lexer, "DEFINE ALIAS Foo Bar;")
    assert (Keyword.Reserved, "DEFINE") in toks
    assert (Keyword.Reserved, "ALIAS") in toks

    toks = _tokens_no_whitespace(lexer, "DEFINE STRUCTURE Point ...;")
    assert (Keyword.Type, "STRUCTURE") in toks

    toks = _tokens_no_whitespace(lexer, "DEFINE ORDINAL Color ...;")
    assert (Keyword.Type, "ORDINAL") in toks


def test_compound_assignment_operators(lexer):
    # Newer Enterprise PL/I addition, confirmed on "Compound assignment
    # statements" -- missed in the first vocabulary pass, added after a
    # specific double-check for newer extensions.
    for op in ("+=", "-=", "*=", "/=", "|=", "&=", "||=", "**="):
        toks = _tokens_no_whitespace(lexer, f"X {op} 1;")
        assert (Operator, op) in toks, f"{op} not tokenized as one Operator"


def test_locator_qualifier_operators(lexer):
    # Newer Enterprise PL/I addition, confirmed on "Expressions and
    # references" (locator-qualifier syntax for pointer/handle-based
    # member access).
    toks = _tokens_no_whitespace(lexer, "P->Field")
    assert (Operator, "->") in toks
    toks = _tokens_no_whitespace(lexer, "H=>Field")
    assert (Operator, "=>") in toks


def test_package_statement_keywords(lexer):
    # PACKAGE/EXPORTS/RESERVES: confirmed on IBM's "Packages" chapter
    # (https://www.ibm.com/docs/en/SSY2V3_6.2/lr/lsh-package.html) --
    # user-flagged coverage gap (EXPORTS/RESERVES had no test and
    # weren't even in the keyword list before this pass). PACKAGE has no
    # qualified-name/member-access syntax to test -- confirmed on that
    # same page, it's a pure block-scoping construct like BEGIN/
    # PROCEDURE, not a namespace with dotted member access -- so plain
    # keyword tokenization is genuinely sufficient here, unlike ooRexx's
    # ::CLASS/::METHOD which needed a dedicated directive state.
    toks = _tokens_no_whitespace(lexer, "MathTools: PACKAGE EXPORTS(Square) RESERVES(Counter);")
    assert (Keyword.Reserved, "PACKAGE") in toks
    assert (Keyword.Reserved, "EXPORTS") in toks
    assert (Keyword.Reserved, "RESERVES") in toks


def test_packagename_bif(lexer):
    # PACKAGENAME: confirmed present in IBM's alphabetic BIF list
    # (already sourced in test_bif_from_sourced_list's list generally --
    # this spot-checks the package-specific one the user asked about).
    toks = _tokens_no_whitespace(lexer, "PACKAGENAME()")
    assert (Name.Builtin, "PACKAGENAME") in toks


def test_no_percent_package_directive_exists(lexer):
    # %PACKAGE is not a real distinct construct -- confirmed absent from
    # the complete alphabetic "Statements and directives" index already
    # sourced (see pli.py's module docstring). The generic "%[a-z_]\w*"
    # preprocessor rule tokenizes it as Comment.Preproc regardless of
    # the specific name, which is the correct/only handling needed for
    # any %-directive, real or not -- this test just confirms that
    # generic rule doesn't error out on this specific (nonexistent)
    # spelling.
    toks = _tokens_no_whitespace(lexer, "%PACKAGE;")
    assert (Comment.Preproc, "%PACKAGE") in toks


def test_percent_null_statement_no_longer_errors(lexer):
    # Real bug, confirmed by direct test before this fix: "%;" (the
    # documented %null statement -- IBM's "Preprocessor statements"
    # index, https://www.ibm.com/docs/en/SSY2V3_6.2/lr/prepst.html) used
    # to produce Token.Error("%") because a lone "%" not followed by a
    # letter matched no rule at all.
    toks = list(PLILexer().get_tokens("%;\n"))
    assert not any(t is Error for t, v in toks), toks
    assert (Comment.Preproc, "%") in [(t, v) for t, v in toks]


def test_preprocessor_statement_keywords(lexer):
    # %DECLARE, %IF, %THEN, %ELSE, %DO, %END, %INCLUDE, %NOTE: spot
    # checks against IBM's complete "Preprocessor statements" index
    # (link above) -- confirmed this project's existing generic
    # "%[a-z_]\w*" wildcard already covers the full real list (verified
    # by checking, not merely assumed complete because it's a wildcard).
    for stmt in ("%DECLARE", "%IF", "%THEN", "%ELSE", "%DO", "%END",
                 "%INCLUDE", "%NOTE", "%ACTIVATE", "%DEACTIVATE",
                 "%ITERATE", "%LEAVE", "%REPLACE", "%SELECT",
                 "%XINCLUDE", "%XINSCAN", "%INSCAN"):
        toks = _tokens_no_whitespace(lexer, f"{stmt} X;")
        assert (Comment.Preproc, stmt) in toks, f"{stmt} not recognized"


def test_preprocessor_only_bifs_distinct_from_runtime_list(lexer):
    # Confirmed by direct comparison against IBM's separate
    # "Preprocessor built-in functions" list
    # (https://www.ibm.com/docs/en/SSY2V3_6.2/lr/prbif.html): these 17
    # names are preprocessor-only and were absent from the runtime BIF
    # list before this fix.
    for bif in ("COMMENT", "COMPILEDATE", "COMPILETIME", "COPYRIGHT",
                "COUNTER", "MACCOL", "MACLMAR", "MACNAME", "MACRMAR",
                "PARMSET", "QUOTE", "SERVICE", "SYSDIMSIZE",
                "SYSOFFSETSIZE", "SYSPARM", "SYSPOINTERSIZE",
                "SYSVERSION"):
        toks = _tokens_no_whitespace(lexer, f"{bif}()")
        assert (Name.Builtin, bif) in toks, f"{bif} not tokenized as Name.Builtin"


def test_macro_procedure_body_uses_bare_keywords(lexer):
    # Per IBM's docs, statements inside a %PROCEDURE...%END body don't
    # need the leading % (a footnote on "Preprocessor facilities" says
    # so explicitly) -- e.g. plain "IF ... THEN ... ELSE ... RETURN"
    # inside a macro procedure means preprocessor-level control flow,
    # not runtime. This confirms, by direct test rather than reasoning
    # alone, that no dedicated lexer state is needed for this: the bare
    # keywords already tokenize as the identical Keyword.Reserved type
    # they would in ordinary runtime code, so a dedicated
    # "macro-procedure-body" state would produce no visibly different
    # highlighting output.
    fragment = (
        "Sq: %PROCEDURE(X);\n"
        "    IF X < 0 THEN\n"
        "        RETURN('0');\n"
        "    ELSE\n"
        "        RETURN(X);\n"
        "%END;\n"
    )
    toks = _tokens_no_whitespace(lexer, fragment)
    assert (Comment.Preproc, "%PROCEDURE") in toks
    assert (Keyword.Reserved, "IF") in toks
    assert (Keyword.Reserved, "THEN") in toks
    assert (Keyword.Reserved, "ELSE") in toks
    assert (Keyword.Reserved, "RETURN") in toks
    assert (Comment.Preproc, "%END") in toks


def test_alternate_not_equal_spelling(lexer):
    # <> is a documented alternate spelling of ¬=, confirmed on both the
    # "Priority of operators" table and the compound-assignment table.
    toks = _tokens_no_whitespace(lexer, "A <> B")
    assert (Operator, "<>") in toks


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
