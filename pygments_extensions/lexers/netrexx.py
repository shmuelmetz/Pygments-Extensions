"""
NetRexx lexer.

NetRexx (Mike Cowlishaw, RexxLA) compiles to Java source or JVM bytecode.
It shares classic Rexx's clause-based instruction syntax and its "simple
symbol" identifier rules, but layers a Java-facing object model directly
onto that syntax rather than growing an independent message-send model
the way ooRexx does: ``class``/``extends``/``implements``/``properties``/
``method``/``returns`` declarations, optional static type annotations on
variables and parameters (``x=Rexx``, ``arguments=String[]``), and ``[]``
array declarators, all resolving to real Java types and Java class-library
access at the language's core rather than as an add-on.

This is written independently against the official language documentation
(the NetRexx Tutorial, netrexx.org) -- not a fork of Pygments' built-in
classic-Rexx lexer or of this project's own OORexxLexer, since NetRexx's
type/class layer is Java-shaped rather than Rexx-object-shaped and shares
comparatively little of its concrete syntax with ooRexx's ``::``-directive
model. What IS carried over from classic Rexx, confirmed identical in the
NetRexx tutorial: block comments (``/* */``, nestable), string literals
(single or double quoted, doubled to escape a same-type quote), and the
basic clause/instruction shape.

Verified against the real NetRexx 4.02-GA Language Reference (the NRL,
netrexx.org/documents/), Sections 6.2/6.3/6.4/6.5/6.6, replacing the
initial pass that only checked the Tutorial's two "Language Basics"/
"Classes and Objects" pages -- two real bugs surfaced by that closer
check, both now fixed here rather than left as a known gap:

* The symbol/identifier character set was WRONG in the first pass: it
  copied OORexxLexer's ``@ # $ ! ?`` set on the (unverified) assumption
  NetRexx's identifier rules matched classic Rexx/ooRexx. The NRL
  (Sec 6.3 "Symbols") is explicit instead: "Symbols are groups of
  characters selected from the Roman alphabet in uppercase or lowercase
  (A-Z, a-z), the Arabic numerals (0-9), or the characters underscore,
  dollar, and euro (``_ $ €``)" -- no ``@``, ``#``, ``!``, or ``?``
  at all. Fixed below (``_SYMBOL_START``/``_SYMBOL_CHAR``); the NRL's
  further Unicode-based "extra letters"/"extra digits" allowance
  (Sec 6.3, implementation-defined via ``Character.isJavaIdentifierPart``/
  ``isDigit``) is deliberately not modeled here, matching this project's
  existing scope-limiting choice for ooRexx's own extended-charset note.
* String escapes were badly incomplete in the first pass: only the
  ``\\xhh`` hex form was handled. The NRL's Table 1 ("Escape sequences",
  p18) lists nine forms total -- ``\\t`` ``\\n`` ``\\r`` ``\\f`` ``\\"``
  ``\\'`` ``\\\\`` ``\\-`` (null character, used for ``say``-instruction
  continuation) ``\\0`` (alternative spelling of the same null) ``\\xhh``
  (2 hex digits) and ``\\uhhhh`` (4 hex digits, full Unicode) -- all now
  recognized as ``String.Escape`` below.

Also verified from the same NRL sections, now reflected below:

* Two comment forms: ``/* ... */`` (nestable -- NRL Sec 6.2 confirms
  "Block comments may be nested"; implementation minimum is nesting
  depth 10, not modeled as a lexer limit since a lexer doesn't need to
  enforce it) and ``--`` to end of line. NetRexx had the ``--`` form
  first -- Cowlishaw designed NetRexx before Open Object Rexx existed.
* String literals: single or double quoted; a same-type quote is
  escaped by doubling it (NRL Sec 6.3 "Literal strings" -- identical
  rule to classic Rexx/ooRexx).
* Numeric-symbol exponential notation (NRL Sec 6.3) requires an
  EXPLICIT sign after E/e -- every one of the NRL's own examples
  (``17.3E-12``, ``3e+12``, ``0.03E+9``) has one, and footnote 21
  states "The sign in this context is part of the symbol; it is not an
  operator" -- i.e. ``1e10`` with no sign is not this construct at all.
  Modeled below with a mandatory ``[+-]``, not the optional-sign
  pattern this project's other two lexers use for their own numeric
  exponents (a real, cited difference from those, not an oversight).
* Hexadecimal/binary numeric symbols (NRL Sec 6.6), e.g. ``2x81``,
  ``4b1000`` -- an *n*-Xstring / *n*-Bstring form encoding a signed
  whole number, entirely unhandled in the first pass (falling through
  as a Number followed by a stray symbol). Now matched as a single
  ``Number`` token before the plain-decimal rule.
* ``class NAME [public|private] [extends SUPER] [implements IFACE,...]``
  class headers; the source filename must match the class name
  (informational for a lexer, not enforceable here).
* ``properties [public|private|...]`` sections introducing plain
  data-member declarations.
* ``method NAME(params) [modifiers] [returns TYPE]`` method headers,
  including the same-name-as-class constructor form and the
  ``static``-marked ``main(arguments=String[])`` entry point.
* Optional inline type annotations via ``name=Type`` in parameter lists
  and elsewhere (NetRexx's syntax for declaring a variable's or
  parameter's Java type without a separate declaration statement).
* ``[]`` array-type/array-literal brackets (``String[]``, ``list[]``).
* Method/property access via a plain ``.`` (period), Java-style --
  e.g. ``v.mag()``, ``n.abs()``, ``System.out.println(...)`` (the
  Tutorial's own constructor example, ``this.xc = x``, already shows
  this for property assignment) -- confirmed via netrexx.org search
  results quoting the Tutorial's internal-function-call examples
  (``n = n.abs()``, ``sn = s.right(2,'0')``). This is the opposite of
  ooRexx, which uses ``~``/``~~`` message-send syntax instead (see
  OORexxLexer) -- the single most likely point of confusion between
  the two lexers for anyone reading them side by side. Deliberately NOT
  given any special dot-message-send handling here (unlike OORexxLexer's
  dedicated message-send rules): a plain ``.`` needs no dedicated rule
  beyond the generic operator table below, since NetRexx has no
  environment-directory-lookup concept or cascading-send syntax for a
  dot rule to disambiguate against.

Explicitly NOT yet covered, pending a fuller reference pass: the
complete reserved-word set (only the words actually shown in the
Tutorial pages and the NRL sections read so far -- Types/Classes,
Terms, Methods and Constructors, Type conversions, Sec 6.2-6.6 -- are
included below; NRL sections on Exceptions (p149), the `numeric`
instruction (p89), `select`/`signal` (p104/108), and the built-in
`Rexx`-class method names (p159) have not yet been read); condition
names and full exception-handling keyword coverage; and any real-world
corpus validation of the kind OORexxLexer and PLILexer both received
before being considered real-world-ready -- see this project's own
README for that standard before treating this lexer as done.
"""

import re

from pygments.lexer import RegexLexer, bygroups, include, words
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

__all__ = ["NetRexxLexer"]

# A NetRexx "simple symbol" (identifier): Roman letters, digits, and
# underscore/dollar/euro ONLY -- NRL Sec 6.3 "Symbols", verified
# directly (see this module's docstring for the correction history;
# this is NOT the same charset as classic Rexx/ooRexx's, which also
# allow @ # ! ?). "." is excluded from the character class and handled
# as its own operator (a symbol may not contain "." unless it's a
# numeric symbol, per NRL Sec 6.3's "it may include a period" carve-out
# for symbols that start with a digit -- not modeled as part of the
# general identifier charset since an ordinary identifier never has
# one). The euro sign is a real allowed character per the NRL (UTF-8
# source only) but is included here as a literal for completeness
# rather than a \w-based escape hatch.
# Lowercase-only ranges are deliberate, not a gap: the lexer runs under
# re.IGNORECASE (see `flags` below), so "[a-z]" already matches upper
# case too -- same convention OORexxLexer's _SYMBOL_START/_CHAR use.
_SYMBOL_START = r"[a-z_$€]"
_SYMBOL_CHAR = r"[a-z0-9_$€]"
_SYMBOL = _SYMBOL_START + _SYMBOL_CHAR + r"*"

# Keywords confirmed so far from the NetRexx Tutorial's "Language Basics"
# and "Classes and Objects" pages only (nr_6.html, nr_11.html). This is
# deliberately a small, cited starting set, not a transcription of the
# full Language Reference's reserved-word list -- expand only against
# that Reference or real .nrx source, per this file's own docstring.
_DECLARATION_KEYWORDS = (
    "class", "extends", "implements", "properties", "method", "returns",
    "public", "private", "static", "protected",
)

_KEYWORDS = (
    "if", "then", "else", "do", "end", "loop", "leave", "iterate",
    "select", "when", "otherwise", "return", "say", "parse", "signal",
    "call", "arg", "options", "numeric", "trace", "interpret", "exit",
    "this", "super", "new",
)


class NetRexxLexer(RegexLexer):
    """
    NetRexx is Mike Cowlishaw's Rexx-syntax language for the JVM: classic
    Rexx clause syntax with a Java-shaped class/method/type layer built
    directly into the core language rather than added as a message-send
    object model.
    """

    name = "NetRexx"
    url = "https://www.netrexx.org/"
    aliases = ["netrexx", "nrx"]
    filenames = ["*.nrx"]
    mimetypes = []
    version_added = "0.1"
    flags = re.IGNORECASE | re.MULTILINE

    tokens = {
        "root": [
            (r"\s+", Whitespace),
            (r"/\*", Comment.Multiline, "comment"),
            # Line comment: "--" to end of line. Per the NetRexx Tutorial
            # ("Language Basics"): "any sequence of characters following
            # a double dash character will be considered as comments (up
            # to the end of line)". Must precede the operator rule so
            # the second "-" doesn't win a single-hyphen match first
            # (same ordering reason as OORexxLexer's identical comment).
            (r"--.*", Comment.Single),
            (r'"', String, "string_double"),
            (r"'", String, "string_single"),
            # Hexadecimal/binary numeric symbol: nXstring / nBstring,
            # e.g. "2x81", "4b1000" (NRL Sec 6.6). Must precede the
            # plain-decimal rule below, or the leading digits match as
            # an ordinary number and strand the "x81"/"b1000" tail to
            # be mis-read as a separate symbol.
            (r"[0-9]+[xX][0-9a-fA-F]+\b", Number),
            (r"[0-9]+[bB][01]+\b", Number),
            # Simple number, optionally with exponential notation. The
            # sign after E/e is REQUIRED per NRL Sec 6.3 -- every one of
            # its own examples (17.3E-12, 3e+12, 0.03E+9) has one, and
            # footnote 21 confirms the sign is part of the symbol, not
            # a separate operator. Deliberately not "[+-]?" here.
            (r"[0-9]+(\.[0-9]+)?([eE][+-][0-9]+)?", Number),
            # Class header: class NAME [public|private ...]
            # [extends SUPER] [implements IFACE, ...]
            (
                r"\b(class)\b(\s+)(" + _SYMBOL + r")",
                bygroups(Keyword.Declaration, Whitespace, Name.Class),
            ),
            (
                r"\b(extends|implements)\b(\s+)(" + _SYMBOL + r")",
                bygroups(Keyword.Declaration, Whitespace, Name.Class),
            ),
            # Method header: method NAME(...) -- name captured as
            # Name.Function; the parameter list and any trailing
            # modifiers/`returns TYPE` are left to fall through to the
            # ordinary rules below (symbol/keyword/operator), since
            # NetRexx parameter lists mix plain names, `name=Type`
            # annotations, and modifier keywords freely.
            (
                r"\b(method)\b(\s+)(" + _SYMBOL + r")",
                bygroups(Keyword.Declaration, Whitespace, Name.Function),
            ),
            (r"\breturns\b", Keyword.Declaration),
            (r"\bproperties\b", Keyword.Declaration),
            # Inline type annotation: name=Type (parameter lists, and
            # NetRexx's general "declare with a type" syntax elsewhere).
            # Confirmed in the Tutorial's constructor example
            # ("x=Rexx, y=Rexx, z=Rexx") and the main() entry point
            # ("arguments=String[]"). Array brackets on the type are
            # matched as part of the same token per the Tutorial's own
            # `String[]` spelling.
            (
                r"(" + _SYMBOL + r")(=)(" + _SYMBOL + r")(\[\])?",
                bygroups(Text, Operator, Name.Class, Operator),
            ),
            include("declaration_keyword"),
            include("keyword"),
            include("operator"),
            (_SYMBOL, Text),
        ],
        "declaration_keyword": [
            (words(_DECLARATION_KEYWORDS, prefix=r"\b", suffix=r"\b"),
             Keyword.Declaration),
        ],
        "keyword": [
            (words(_KEYWORDS, prefix=r"\b", suffix=r"\b"), Keyword.Reserved),
        ],
        "operator": [
            (
                r"(-|//|/|\(|\)|\*\*|\*|\\==|\\=|\\|"
                r"\[|\]|\|\||\||&&|&|%|\+|<=|<|==|=|>=|>|\.|,|;)",
                Operator,
            ),
        ],
        # All nine escape forms from NRL Table 1 (p18), shared by both
        # quote styles since the rules don't differ by delimiter. Listed
        # longest/most-specific first only where it matters (\0 vs \-
        # can't collide with anything else here, order is otherwise
        # unconstrained).
        "escape": [
            (r"\\[tnrf]", String.Escape),
            (r'\\"', String.Escape),
            (r"\\'", String.Escape),
            (r"\\\\", String.Escape),
            (r"\\-", String.Escape),  # null char; also a `say` continuation
            (r"\\0", String.Escape),  # alternative spelling of the same null
            (r"\\x[0-9a-fA-F]{2}", String.Escape),
            (r"\\u[0-9a-fA-F]{4}", String.Escape),
        ],
        "string_double": [
            include("escape"),
            (r'[^"\n\\]+', String),
            (r'""', String),
            (r'"', String, "#pop"),
            (r"\n", Text, "#pop"),  # Stray linefeed also terminates strings.
        ],
        "string_single": [
            include("escape"),
            (r"[^'\n\\]+", String),
            (r"''", String),
            (r"'", String, "#pop"),
            (r"\n", Text, "#pop"),
        ],
        "comment": [
            # Comments nest in NetRexx (per the Tutorial: "Comments can
            # be nested") -- unlike this project's OORexxLexer/PLILexer
            # comment states, this one tracks nesting depth explicitly
            # rather than popping on the first "*/".
            (r"/\*", Comment.Multiline, "#push"),
            (r"\*/", Comment.Multiline, "#pop"),
            (r"[^*/]+", Comment.Multiline),
            (r"[*/]", Comment.Multiline),
        ],
    }
