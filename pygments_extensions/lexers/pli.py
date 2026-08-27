"""
PL/I lexer.

Unlike the ooRexx lexer, this is a from-scratch build: Pygments has never
shipped a PL/I lexer at any point in its history (confirmed by an
exhaustive check of every branch/tag, GitHub's issue/PR index, and every
historical revision of the CHANGES file -- including the two actual
Python 2->3 transition commits, both confirmed clean of any lexer
removal). There is no legacy source to port.

STATUS: work in progress. Comments, character strings, bit/hex string
constants, numeric literals, and the operator set (including the NOT
operator, see below) are implemented and tested. The DCL-attribute,
statement-keyword, and built-in-function (BIF) lists are a first-pass
draft sourced from IBM's Enterprise PL/I for z/OS 6.2 Language Reference
plus general PL/I knowledge -- NOT yet cross-checked against the formal
language standards (ANSI X3.53-1976, ISO 6160:1979, ANSI X3.74-1981
"Subset G", and the corresponding ISO Subset G standard), which are more
authoritative than any single vendor's implementation guide and may
differ from IBM's current vocabulary in either direction (IBM extensions
not in the standard; standard keywords IBM has since deprecated). Treat
the keyword/attribute/BIF lists below as provisional until that
cross-check happens.

NOT operator (settled, not provisional): IBM Enterprise PL/I for z/OS
6.2 Language Reference, "Special characters" table -- ¬ has default
EBCDIC hex 5F / default ASCII hex 5E (the same code point as caret, ^);
the OR/NOT/QUOTE compiler options exist specifically because these three
symbols have variant code points across code pages. Since Pygments lexes
already-decoded Unicode text, the actual regex target is U+00AC (NOT
SIGN) -- matched unconditionally, with ^ recognized alongside it as a
genuine alternate representation seen in real-world source, not as a
substitute for matching U+00AC itself. (Deeper history, not specific to
PL/I: pre-1967 ASCII had unsettled/dual glyph assignment at that same
0x5E code position -- documented as up-arrow-vs-caret contention, not
confirmed specifically as NOT-sign-vs-caret -- predating any
EBCDIC-conversion-artifact framing.)
"""

import re

from pygments.lexer import RegexLexer, bygroups, include, words
from pygments.token import (
    Comment,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
    Whitespace,
)

__all__ = ["PLILexer"]


class PLILexer(RegexLexer):
    """
    PL/I is IBM's general-purpose, case-insensitive programming language,
    originally developed for mainframe use and still current in IBM
    Enterprise PL/I for z/OS. This lexer covers the classic/mainframe
    dialect; it has never previously existed in Pygments.
    """

    name = "PL/I"
    url = "https://www.ibm.com/docs/en/epfz"
    aliases = ["pli", "pl1"]
    filenames = ["*.pli", "*.pl1", "*.plx"]
    mimetypes = []
    version_added = "0.1"
    flags = re.IGNORECASE

    tokens = {
        "root": [
            (r"\s+", Whitespace),
            (r"/\*", Comment.Multiline, "comment"),
            # Preprocessor directives: %INCLUDE, %DCL, %IF, %ACTIVATE, etc.
            (r"%[a-z_]\w*", Comment.Preproc),
            # Bit-string and hex-string constants: '1010'B, '1F'X. These
            # must come before the generic character-string rule, since
            # both start with the same quote character -- only the
            # trailing radix letter distinguishes them, so order matters
            # (RegexLexer takes the first matching rule, not the most
            # specific).
            (r"'[01]+'[Bb]", Number.Bin),
            (r"'[0-9A-Fa-f]+'[Xx]", Number.Hex),
            (r"'", String, "string"),
            # Numeric literals: decimal fixed (123, 123.45) and decimal
            # float with an exponent (1.5E10, 1.5E+10, 1.5E-10).
            (r"[0-9]+\.[0-9]+[Ee][+-]?[0-9]+", Number.Float),
            (r"[0-9]+[Ee][+-]?[0-9]+", Number.Float),
            (r"[0-9]+\.[0-9]+", Number.Float),
            (r"[0-9]+", Number.Integer),
            # Labels: identifier immediately followed by a colon on the
            # same line, e.g. "loop: DO ...;". Same-line whitespace only
            # ([ \t]*, not \s*) -- see the ooRexx lexer's own fix for
            # why a bare \s* here would be a real bug, not just style:
            # it can cross a newline and swallow a token meant for the
            # following line.
            (r"([a-z_]\w*)([ \t]*)(:)", bygroups(Name.Label, Whitespace, Punctuation)),
            # NOT operator: settled per the module docstring above. ¬=,
            # ¬<, ¬> (negated comparisons) must be listed before the
            # bare comparison operators below, and before the bare NOT
            # rule, so they aren't split into NOT + "=".
            (r"[¬^]=", Operator),
            (r"[¬^]<", Operator),
            (r"[¬^]>", Operator),
            (r"[¬^]", Operator),
            include("operator"),
            include("attribute"),
            include("keyword"),
            include("function"),
            (r"[a-z_]\w*", Text),
        ],
        "operator": [
            (r"\*\*|\|\||[-+*/=<>&|.,;()]", Operator),
        ],
        "attribute": [
            # DCL attribute keywords. DRAFT -- see module docstring:
            # sourced from IBM's current docs + general knowledge, not
            # yet cross-checked against the formal ANSI/ISO standards.
            (
                words(
                    (
                        "fixed", "float", "binary", "decimal", "char",
                        "character", "bit", "varying", "pointer", "handle",
                        "offset", "entry", "label", "file", "picture",
                        "based", "defined", "aligned", "unaligned",
                        "static", "automatic", "controlled", "external",
                        "internal", "initial", "init", "like", "returns",
                        "builtin", "condition", "dimension", "area",
                        "format", "generic", "structure", "union",
                        "variable", "parameter", "unsigned", "signed",
                        "real", "complex", "precision",
                    ),
                    suffix=r"\b",
                ),
                Keyword.Type,
            ),
        ],
        "keyword": [
            # Statement keywords. DRAFT, same caveat as "attribute" above.
            (
                words(
                    (
                        "declare", "dcl", "procedure", "proc", "if", "then",
                        "else", "do", "end", "call", "return", "select",
                        "when", "otherwise", "get", "put", "read", "write",
                        "open", "close", "on", "signal", "revert", "goto",
                        "go", "to", "allocate", "free", "stop", "exit",
                        "list", "data", "edit", "skip", "page", "line",
                        "from", "into", "by", "while", "until", "repeat",
                        "not", "and", "or",
                    ),
                    suffix=r"\b",
                ),
                Keyword.Reserved,
            ),
        ],
        "function": [
            # Built-in functions (BIFs). DRAFT, same caveat as above.
            (
                words(
                    (
                        "substr", "length", "index", "abs", "trunc", "ceil",
                        "floor", "mod", "sign", "max", "min", "sqrt", "sin",
                        "cos", "exp", "log", "date", "time", "translate",
                        "verify", "search", "tally", "reverse", "repeat",
                        "hbound", "lbound", "dimension", "null", "addr",
                    ),
                    suffix=r"(\s*)(\()",
                ),
                bygroups(Name.Builtin, Whitespace, Operator),
            ),
        ],
        "string": [
            (r"[^'\n]+", String),
            (r"''", String),
            (r"'", String, "#pop"),
            (r"\n", Text, "#pop"),  # Stray linefeed also terminates strings.
        ],
        "comment": [
            (r"[^*]+", Comment.Multiline),
            (r"\*/", Comment.Multiline, "#pop"),
            (r"\*", Comment.Multiline),
        ],
    }
