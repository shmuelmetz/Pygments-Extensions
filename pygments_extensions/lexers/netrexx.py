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

The entire NRL body (Sec 6-50, all instructions, all special names,
the complete built-in-method reference table, and both appendices) has
now been read -- see the section list below. What's genuinely still
outstanding is real-world corpus validation of the kind OORexxLexer
and PLILexer both received before being considered real-world-ready
(this lexer has 107 tests, all hand-written against the NRL's own
examples, and has not yet seen a single line of real .nrx source) --
see this project's own README for that standard before treating this
lexer as done. A handful of exception/condition TYPE NAMES from
Appendix B (BadArgumentException, DivideException, etc.) are used only
as ordinary class-name arguments to `catch`, and correctly fall
through as plain symbols already -- not a gap needing a dedicated
keyword list, the same way `extends`/`implements` type-name arguments
already work.

Sections read: 6.2-6.6 (Structure/Tokens), 7-10 (Types/Terms/Methods/
Conversions), 18 (Class), 19 (Do), 20 (Exit), 21 (If), 22 (Import), 23
(Iterate), 24 (Leave), 25 (Loop), 26 (Method), 27 (Nop), 28 (Numeric),
29 (Options), 30 (Package), 31 (Parse), 32 (Properties), 33 (Return),
34 (Say), 35 (Select), 36 (Signal), 37 (Trace), 38 (Program
structure), 39 (Minor and Dependent classes), 40 (Special names and
methods, full), 41 (JavaBean Support), 42 (Parsing templates), 43
(Numbers and Arithmetic), 44 (Binary values and operations), 45
(Exceptions), 46 (Thread Pool Support), 47 (Structured Lists
Interface), 48 (built-in Rexx-string methods, full), 49-50 (Appendix
A sample program, Appendix B netrexx.lang package overview). Sections
42-47 and the appendices introduced no new lexical rules -- their
syntax (parsing-template patterns, arithmetic, binary-class
semantics, exception handling, thread-pool/structured-list method
calls, the sample program) is all expressed in tokens already covered
(strings, numbers, operators, symbols, dot-notation calls); only 48
added something new (the built-in-method Name.Builtin highlighting
below).
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

# Visibility/modifier-family keywords confirmed against the real NRL
# (Sections 18 Class, 19 Do, 25 Loop, 26 Method, 32 Properties) --
# "class"/"extends"/"implements"/"method"/"returns"/"properties"
# themselves get their own dedicated regex rules above/below instead of
# living in this generic list, since they need bygroups() treatment
# (name/type capture) that a plain words() alternation can't give them.
# CORRECTION from the first pass: "protected" was removed -- it is NOT
# a NetRexx keyword at all (that's Java/ooRexx; NetRexx's real
# visibility words are private/public/shared/inheritable, confirmed
# NRL Sec 18.1/26.2/32.1).
_DECLARATION_KEYWORDS = (
    "private", "public", "shared", "inheritable",  # visibility
    "abstract", "adapter", "final", "interface",  # class modifier
    "constant", "native", "static", "transient", "volatile",  # method/
    # properties modifier (some already covered above; static/abstract/
    # final/constant recur across class/method/properties per the NRL)
    "binary", "deprecated", "unused", "protect", "uses", "signals",
    # "dependent" -- Minor and Dependent classes (NRL Sec 39.2): a
    # child class modifier giving it simplified access to its parent
    # object's properties. Confirmed real this pass, not in the
    # original guess set.
    "dependent",
)

# Instruction/control-flow keywords, now confirmed against every
# instruction-grammar section in the NRL (Sec 18-38: Class through
# Program structure) -- no more "seen in the table of contents but not
# the grammar" entries left in this list; see this module's docstring
# for the remaining truly-unread sections (Exceptions, JavaBean
# Support, Parsing templates, Numbers and Arithmetic, built-in
# Rexx-string methods).
#
# CORRECTIONS from this pass: "case" (Select instruction, Sec 35.3)
# and the Trace instruction's own sub-keywords (all/methods/off/
# results/var, Sec 37) were missing entirely.
#
# CORRECTIONS from the first pass: "call" and "arg" removed -- neither
# is a real NetRexx keyword. NetRexx has no classic-Rexx CALL
# instruction at all (NRL Sec 9.1 "Method call instructions": a method
# invocation is itself the instruction, `symbol(...)`, no separate
# keyword). "arg" is explicitly NOT a keyword per the NRL's own words
# (Sec 31 Parse instruction, footnote): "`parse arg template`... will
# work... even though **arg is not a keyword** in this case" -- it's
# just the conventional name of the variable holding command args.
# "new" removed -- never verified, and now positively contradicted:
# every constructor example in the NRL (Sec 9.5 Constructor methods,
# Sec 39 Minor/Dependent classes) constructs objects as
# `ClassName(args)` with no "new" keyword anywhere. NetRexx has no
# Java-style `new` operator.
_KEYWORDS = (
    "if", "then", "else", "do", "end", "loop", "leave", "iterate",
    "label", "catch", "finally", "to", "by", "for", "while", "until",
    "forever", "over", "exit", "nop", "import", "package", "options",
    "numeric", "digits", "form", "scientific", "engineering",
    "select", "when", "otherwise", "case", "return", "say", "parse",
    "signal", "trace", "interpret",
    "all", "methods", "off", "results", "var",  # trace sub-keywords
)

# Special names (NRL Sec 40.1): recognized specially, but explicitly
# and repeatedly stated NOT to be reserved words -- "these may only be
# used alone as a term... they are not reserved; they may be used as
# variable names instead, if desired." This is a real, documented
# difference from _KEYWORDS/_DECLARATION_KEYWORDS above (which ARE
# reserved), so it gets its own token type (Keyword.Pseudo, the same
# category Pygments uses for e.g. Python's self/cls -- recognized by
# convention, not grammar). CORRECTION: "this" and "super" were
# wrongly filed under _KEYWORDS (Keyword.Reserved) in the first pass;
# moved here, since the NRL places them in this same special-names
# list, not among the true reserved instruction keywords.
# "digits" and "form" are deliberately NOT repeated here even though
# the NRL lists them among the special names too (retrieving the
# current `numeric digits`/`numeric form` setting) -- they're already
# in _KEYWORDS above for the `numeric digits`/`numeric form`
# sub-keyword position, and duplicating the same literal into a second
# words() alternation would just make one of the two rules dead code.
# Simplification, not an omission: both roles exist, only one token
# type is picked.
_SPECIAL_NAMES = (
    "ask", "asknoecho", "class", "length", "this", "super", "version",
    "parent", "source",
    # Confirmed same section, continued (p122-123): null (the "empty
    # reference" value), RC (returncode of the last ADDRESSed
    # command), sourceline (current clause's line number).
    "null", "rc", "sourceline",
)

# Built-in methods of the NetRexx string class Rexx (NRL Sec 48, full
# list p159-176) -- always called via dot-notation (string.method()),
# never bare like classic Rexx's BIFs, so they get their own dot-call
# rule below rather than living in _BUILTIN_FUNCTIONS-style bare-call
# handling. "length" is deliberately excluded: it's already in
# _SPECIAL_NAMES (NRL Sec 40.1 documents both the special-name and
# zero-arg-method spellings as equivalent; picking one token type,
# same simplification as digits/form above).
_BUILTIN_METHODS = (
    "abbrev", "abs", "b2d", "b2x", "center", "centre", "changestr",
    "compare", "copies", "copyindexed", "countstr", "c2d", "c2x",
    "datatype", "date", "delstr", "delword", "exists", "format",
    "insert", "lastpos", "left", "lower", "max", "min", "overlay",
    "pos", "reverse", "right", "sequence", "sign", "soundex", "space",
    "strip", "substr", "subword", "time", "translate", "trunc",
    "upper", "verify", "word", "wordindex", "wordlength", "wordpos",
    "words", "x2b", "x2c", "x2d",
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
            include("special_name"),
            # Built-in method call: .methodname, e.g. string.abbrev(...).
            # Must precede the generic operator rule below, which would
            # otherwise claim the bare "." first and leave the method
            # name to fall through as plain Text. Highlighting quality,
            # not a correctness fix -- these already lexed fine as
            # Operator(".") + Text(name); this makes them read as the
            # recognizable built-ins they are, same as OORexxLexer does
            # for classic Rexx's bare-call BIFs.
            (
                r"(\.)(" + "|".join(_BUILTIN_METHODS) + r")\b",
                bygroups(Operator, Name.Builtin),
            ),
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
        # NRL Sec 40.1 special names: recognized specially but NOT
        # reserved (see _SPECIAL_NAMES above for the exact quote).
        # "class" here is the String.class-style special-name usage
        # (Sec 40.1's own example, `obj=String.class`); it doesn't
        # collide with the earlier `class NAME` declaration rule above,
        # which only matches "class" immediately followed by
        # whitespace and a name, never "class" on its own or after a
        # dot.
        "special_name": [
            (words(_SPECIAL_NAMES, prefix=r"\b", suffix=r"\b"),
             Keyword.Pseudo),
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
