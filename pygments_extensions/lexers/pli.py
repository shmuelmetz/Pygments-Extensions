"""
PL/I lexer.

Unlike the ooRexx lexer, this is a from-scratch build: Pygments has never
shipped a PL/I lexer at any point in its history (confirmed by an
exhaustive check of every branch/tag, GitHub's issue/PR index, and every
historical revision of the CHANGES file -- including the two actual
Python 2->3 transition commits, both confirmed clean of any lexer
removal). There is no legacy source to port.

Vocabulary sourcing (per user direction: "stick with Enterprise" rather
than pursue the formal ANSI/ISO PL/I standards, which proved hard to
access online -- see below): the DCL-attribute, statement-keyword, and
built-in-function (BIF) word lists below are sourced directly from
IBM's current Enterprise PL/I for z/OS 6.2 Language Reference (Last
Updated: 2026-05-14 per IBM's own docs), not reconstructed from memory:

* BIFs (420 names): the complete alphabetic list at "Descriptions of
  individual built-in functions, pseudovariables, and subroutines",
  https://www.ibm.com/docs/en/epfz/6.2.0?topic=subroutines-descriptions-individual-built-in-functions-pseudovariables
* Statement/directive keywords: the complete alphabetic index at
  "Statements and directives",
  https://www.ibm.com/docs/en/SSY2V3_6.2/lr/gest.html
* DCL attributes, assembled from several real IBM 6.2 pages (there is
  no single flat alphabetical attributes index the way there is for
  BIFs and statements -- confirmed by checking, not assumed): the
  "Data attributes" category index (35 names),
  https://www.ibm.com/docs/en/epfz/6.2.0?topic=attributes-data ;
  the storage-class attributes named in running prose in "Storage
  control", https://www.ibm.com/docs/en/epfz/6.2.0?topic=reference-storage-control
  (STATIC, AUTOMATIC, CONTROLLED, BASED, ASSIGNABLE, NONASSIGNABLE,
  NORMAL, ABNORMAL, BIGENDIAN, LITTLEENDIAN, HEXADEC, IEEE, CONNECTED,
  NONCONNECTED, DEFINED, POSITION, INITIAL); and individually-confirmed
  pages for ALIGNED/UNALIGNED, INTERNAL/EXTERNAL, BUILTIN, CONDITION,
  GENERIC, and VALUE. This attribute list is NOT claimed exhaustive --
  PL/I has attributes (e.g. LIKE, and RECURSIVE -- spotted used in a
  real worked example on the "Packages" page while checking PACKAGE
  coverage, but not separately chased down to its own attribute page
  during this pass) not confirmed against a page yet -- but every name
  present here is sourced, not guessed.

Not pursued, per explicit user direction: the formal language standards
(ANSI X3.53-1976 / ISO 6160:1979; ANSI X3.74-1981 and X3.74-1987 Subset
G, two distinct editions, not one standard with a later reprint; and
their ISO counterparts ISO 6522:1985 and ISO/IEC 6522:1992) would be
more authoritative than any vendor's implementation guide, but weren't
readily accessible online at the time of writing. If the PL/I community
(outreach still pending, see README.md "Community awareness") turns out
to include someone with access -- personal copy, university library,
IBM/ANSI archive -- the vocabulary below should be cross-checked against
them and revised where IBM's current vendor extensions diverge from the
standard.

Newer-extension double-check: a follow-up pass specifically looked for
statements/operators that might have been under-weighted by leaning on
general/classic-1976-era PL/I recall rather than purely the current 6.2
docs index, since IBM's Enterprise PL/I has grown considerably since
then. DEFINE (and ALIAS/STRUCTURE/ORDINAL) were already present --
DEFINE/ALIAS in the statement-keyword list, STRUCTURE/ORDINAL in the
attribute list, since those two words are also attribute names in their
own right. What the first pass genuinely missed, found by following up
on "Compound assignment statements" (a page title the statement index
itself surfaced, but whose contents weren't followed into at the time)
and "Expressions and references": the compound assignment operators
(+=, -=, *=, /=, |=, &=, ||=, **=) and the locator-qualifier operators
(->, =>) -- both real Enterprise PL/I additions beyond the classic
operator set, now added to the "operator" state below with their
sourcing.

NOT operator (settled, sourced independently of the above): IBM
Enterprise PL/I for z/OS 6.2 Language Reference, "Special characters"
table -- ¬ has default EBCDIC hex 5F / default ASCII hex 5E (the same
code point as caret, ^); the OR/NOT/QUOTE compiler options exist
specifically because these three symbols have variant code points across
code pages. Since Pygments lexes already-decoded Unicode text, the actual
regex target is U+00AC (NOT SIGN) -- matched unconditionally, with ^
recognized alongside it as a genuine alternate representation seen in
real-world source, not as a substitute for matching U+00AC itself.
(Deeper history, not specific to PL/I: pre-1967 ASCII had unsettled/dual
glyph assignment at that same 0x5E code position -- documented as
up-arrow-vs-caret contention, not confirmed specifically as
NOT-sign-vs-caret -- predating any EBCDIC-conversion-artifact framing.)

¬ genuinely has two distinct meanings depending on grammatical position
-- this is not an analogy or a guess, it is stated outright in IBM's
Enterprise PL/I 6.2 Language Reference, "Bit operations"
(https://www.ibm.com/docs/en/epfz/6.2.0?topic=expressions-bit-operations),
Table 1 "Logical operators for bit operations": ¬ is listed as usable
both "As prefix operator" (Yes) and "As a infix operator" (Yes) --
prefix ¬ means logical NOT, infix ¬ (bare ¬ between two operands, e.g.
"A ¬ B") means bitwise exclusive-or (XOR), confirmed by that page's
worked example (Table 3): for A = '010111'B, B = '111111'B, "A ¬ B"
yields '101000'B. This is a completely separate fact from, and unrelated
to, the atomic ¬=/¬</¬> negated-relational operators below -- those
remain three distinct operator symbols that happen to incorporate the ¬
glyph, not a second sense of "infix ¬". This lexer's tokenization already
handles both senses correctly as a side effect of how the rules are
ordered: a bare ¬ not immediately followed by =/</> falls through to a
single generic Operator("¬") token regardless of whether it sits in
prefix or infix position -- disambiguating NOT from XOR is a parser-level
concern (position-dependent), not something the lexer needs to do, the
same way "-" tokenizes identically whether it's unary minus or binary
subtraction.

Known overlap, not a bug: some words are both a DCL attribute and a BIF
name in real PL/I (e.g. BINARY, FIXED, CHARACTER are attributes in a
DECLARE and also type-conversion functions when called like BINARY(x)).
The attribute rule is checked before the function rule below, so these
tokenize as Keyword.Type rather than Name.Builtin in both uses --
correct for the overwhelmingly more common DCL usage, an acceptable
simplification for the rarer function-call usage.
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
            # ¬/^: settled per the module docstring above. ¬=, ¬<, ¬>
            # (the atomic negated-relational operators) must be listed
            # before the bare ¬/^ rule, so they aren't split into two
            # tokens. The final bare rule below is intentionally
            # position-agnostic: it matches ¬ (or ^) whenever not
            # immediately followed by =/</>, which covers BOTH real
            # grammatical positions ¬ has -- prefix (logical NOT) and
            # infix (bitwise XOR, e.g. "A ¬ B") -- as a single generic
            # Operator token either way. Disambiguating which semantic
            # meaning applies is a parser-level, position-dependent
            # concern, not a lexer one.
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
            # Compound assignment operators (+=, -=, *=, /=, |=, &=,
            # ||=, **=) and the locator-qualifier operators (->, =>,
            # pointer/handle-based member access, e.g. p->field) are
            # real IBM Enterprise PL/I additions confirmed directly
            # against current docs -- "Compound assignment statements"
            # (https://www.ibm.com/docs/en/epfz/6.2.0?topic=statements-compound-assignment)
            # and "Expressions and references"
            # (https://www.ibm.com/docs/en/epfz/6.2.0?topic=reference-expressions-references).
            # Longer sequences must be ordered before their own
            # prefixes (e.g. "**=" before "**" before "*=" before "*"),
            # since RegexLexer takes the first list entry that matches,
            # not the longest.
            (r"\*\*=|\*\*", Operator),
            (r"\|\|=|\|\|", Operator),
            (r"->|=>", Operator),
            # <> is a documented alternate spelling of ¬= (not-equal in
            # ordinary comparisons; "exclusive-or and assign" in the
            # compound-assignment table specifically) -- confirmed on
            # both of the pages cited above.
            (r"<>", Operator),
            (r"[-+*/|&]=", Operator),
            (r"[-+*/=<>&|.,;()]", Operator),
        ],
        "attribute": [
            # DCL attribute keywords -- see module docstring for the
            # specific IBM 6.2 pages each of these is sourced from.
            (
                words(
                    (
                        # "Data attributes" category index (35 names).
                        "area", "binary", "bit", "character", "complex",
                        "decimal", "dimension", "entry", "file", "fixed",
                        "float", "format", "graphic", "handle", "label",
                        "locates", "nonvarying", "offset", "ordinal",
                        "picture", "pointer", "precision", "real",
                        "returns", "signed", "structure", "task", "type",
                        "uchar", "unsigned", "union", "varying",
                        "varying4", "varyingz", "widechar", "widepic",
                        # "Storage control" chapter, named in prose.
                        "static", "automatic", "controlled", "based",
                        "assignable", "nonassignable", "normal",
                        "abnormal", "bigendian", "littleendian",
                        "hexadec", "ieee", "connected", "nonconnected",
                        "defined", "position", "initial",
                        # Individually-confirmed attribute pages.
                        "aligned", "unaligned", "internal", "external",
                        "builtin", "condition", "generic", "value",
                    ),
                    suffix=r"\b",
                ),
                Keyword.Type,
            ),
        ],
        "keyword": [
            # Statement/directive keywords, from the complete alphabetic
            # "Statements and directives" index (see module docstring).
            # %-prefixed directives (INCLUDE, LINE, NOPRINT, etc.) are
            # already handled by the generic "%[a-z_]\w*" rule above and
            # so are deliberately not repeated here.
            (
                words(
                    (
                        "allocate", "assert", "attach", "begin", "call",
                        "cancel", "thread", "close", "declare", "dcl",
                        "default", "define", "alias", "delay", "delete",
                        "detach", "display", "do", "end", "exit", "fetch",
                        "flush", "free", "get", "go", "if", "then",
                        "else", "iterate", "leave", "locate", "null",
                        "on", "open", "otherwise", "package", "procedure",
                        "proc", "put", "qualify", "read", "reinit",
                        "release", "resignal", "return", "revert",
                        "rewrite", "select", "signal", "stop", "wait",
                        "when", "write", "xdeclare", "xdefine",
                        "xprocedure",
                        # Common clause keywords used within statements
                        # (DO ... TO ... BY ..., READ ... INTO(...)),
                        # not "statements" themselves in IBM's index but
                        # real reserved words -- "into" directly confirmed
                        # in IBM's own example: "read file(In) into(Input)".
                        "to", "by", "from", "into",
                        # PACKAGE-statement clause keywords, confirmed on
                        # IBM's "Packages" chapter
                        # (https://www.ibm.com/docs/en/SSY2V3_6.2/lr/lsh-package.html),
                        # whose syntax diagram and worked example use both
                        # -- "package-name: PACKAGE EXPORTS(...)
                        # RESERVES(...) OPTIONS(...); ... END package-name;".
                        # No dedicated lexer state is needed for PACKAGE the
                        # way ooRexx's ::CLASS/::METHOD needed one: unlike
                        # those, PACKAGE has no distinguishing sigil and no
                        # qualified-name/member-access syntax (it's a pure
                        # block-scoping construct -- exported names are
                        # referenced as ordinary external procedure names,
                        # not package.procedure-style) -- it uses the exact
                        # same generic keyword-statement grammar as
                        # PROCEDURE/DO/BEGIN, already handled. %PACKAGE is
                        # NOT a real distinct directive -- confirmed absent
                        # from the complete alphabetic "Statements and
                        # directives" index already pulled (see above).
                        "exports", "reserves",
                    ),
                    suffix=r"\b",
                ),
                Keyword.Reserved,
            ),
        ],
        "function": [
            # Built-in functions (BIFs): the complete list of 420 names
            # from IBM's alphabetic BIF reference (see module docstring).
            (
                words(
                    (
                        'abs', 'acos', 'add', 'adddays', 'addr', 'addrdata', 'all',
                        'allcompare', 'alloc31', 'allocate', 'allocation', 'allocnext',
                        'allocsize', 'any', 'asin', 'atan', 'atand', 'atanh', 'automatic',
                        'availablearea', 'base64decode', 'base64decode16', 'base64decode8',
                        'base64encode', 'base64encode16', 'base64encode8', 'between',
                        'betweenexclusive', 'betweenleftexclusive', 'binary',
                        'binaryvalue', 'binsearch', 'binsearchx', 'bit', 'bitlocation',
                        'bool', 'byte', 'bytelength', 'cds', 'ceil', 'centerleft',
                        'centerright', 'centreleft', 'centreright', 'character',
                        'chargraphic', 'charval', 'checkstg', 'checksum', 'codepage',
                        'collapse', 'collate', 'compare', 'complex', 'conjg', 'copy',
                        'cos', 'cosd', 'cosh', 'count', 'cs', 'currentsize',
                        'currentstorage', 'datafield', 'date', 'datetime', 'days',
                        'daystodate', 'daystomicrosecs', 'daystosecs', 'decimal',
                        'dimension', 'divide', 'edit', 'empty', 'entryaddr', 'epsilon',
                        'erf', 'erfc', 'exp', 'exponent', 'fileddint', 'fileddtest',
                        'fileddword', 'fileid', 'filenew', 'fileopen', 'fileread',
                        'fileseek', 'filetell', 'filewrite', 'fixed', 'fixedbin',
                        'fixeddec', 'float', 'floatbin', 'floatdec', 'floor',
                        'foldedfullmatch', 'foldedsimplematch', 'fracval', 'gamma',
                        'getenv', 'getjclsymbol', 'getsysint', 'getsysword', 'graphic',
                        'gtca', 'handle', 'hbound', 'hboundacross', 'hex', 'hex8',
                        'hexdecode', 'hexdecode8', 'hexencode', 'hexencode8', 'heximage',
                        'heximage8', 'high', 'huge', 'iand', 'iclz', 'ieor', 'ifthenelse',
                        'imag', 'inarray', 'index', 'indexr', 'indicators', 'inlist',
                        'inot', 'ior', 'ipopcnt', 'irll', 'irrl', 'isfinite', 'isigned',
                        'isinf', 'isjclsymbol', 'isleap', 'isll', 'ismain', 'isnan',
                        'isnormal', 'isrl', 'iszero', 'iunsigned', 'jsongetarrayend',
                        'jsongetarraystart', 'jsongetcolon', 'jsongetcomma',
                        'jsongetmember', 'jsongetobjectend', 'jsongetobjectstart',
                        'jsongetvalue', 'jsonputarrayend', 'jsonputarraystart',
                        'jsonputcolon', 'jsonputcomma', 'jsonputmember',
                        'jsonputobjectend', 'jsonputobjectstart', 'jsonputvalue',
                        'jsonvalid', 'juliantosmf', 'lastday', 'lbound', 'lboundacross',
                        'left', 'length', 'lineno', 'location', 'locstg', 'locval', 'log',
                        'log10', 'log2', 'loggamma', 'low', 'lowerascii', 'lowercase',
                        'lowerlatin1', 'mainname', 'max', 'maxdate', 'maxexp', 'maxlength',
                        'maxval', 'memcollapse', 'memconvert', 'memcu12', 'memcu14',
                        'memcu21', 'memcu24', 'memcu41', 'memcu42', 'memindex',
                        'memreplace', 'memsearch', 'memsearchr', 'memsqueeze',
                        'memuvalid16', 'memuvalid8', 'memverify', 'memverifyr',
                        'microsecs', 'microsecstodate', 'microsecstodays', 'min',
                        'mindate', 'minexp', 'minval', 'mod', 'mpstr', 'multiply', 'null',
                        'nullentry', 'offset', 'offsetadd', 'offsetdiff', 'offsetsubtract',
                        'offsetvalue', 'omitted', 'onactual', 'onarea', 'onchar',
                        'oncondcond', 'oncondid', 'oncount', 'onexpected', 'onfile',
                        'ongsource', 'onhbound', 'onjsonname', 'onkey', 'onlbound',
                        'online', 'onloc', 'onoffset', 'onoperator', 'onpackage',
                        'onprocedure', 'onsource', 'onsubcode', 'onsubcode2',
                        'onsubscript', 'ontext', 'onuchar', 'onusource', 'onwchar',
                        'onwsource', 'ordinalname', 'ordinalpred', 'ordinalsucc',
                        'packagename', 'pageno', 'picspec', 'places', 'pliascii',
                        'pliattn', 'plicanc', 'plickpt', 'plidelete', 'plidump',
                        'pliebcdic', 'plifill', 'plifree', 'plimove', 'pliover',
                        'pliparse', 'plirest', 'pliretc', 'pliretv', 'plisaxa', 'plisaxb',
                        'plisaxc', 'plisaxd', 'plisrta', 'plisrtb', 'plisrtc', 'plisrtd',
                        'plistck', 'plistcke', 'plistckelocal', 'plistckeutc', 'plistckf',
                        'plistcklocal', 'plistckp', 'plistckplocal', 'plistckputc',
                        'plistckutc', 'plitran11', 'plitran12', 'plitran21', 'plitran22',
                        'pointer', 'pointeradd', 'pointerdiff', 'pointersubtract',
                        'pointervalue', 'poly', 'precision', 'precval', 'pred', 'present',
                        'procedurename', 'prod', 'putenv', 'quicksort', 'quicksortx',
                        'radix', 'random', 'rank', 'real', 'regex', 'rem', 'repattern',
                        'repeat', 'replace', 'reverse', 'right', 'round',
                        'roundawayfromzero', 'roundtoeven', 'samekey', 'scale', 'scaleval',
                        'scrubout', 'search', 'searchr', 'secs', 'secstodate',
                        'secstodays', 'sign', 'signed', 'sin', 'sind', 'sinh', 'size',
                        'smftojulian', 'sourcefile', 'sourceline', 'sqrt', 'sqrtf',
                        'squeeze', 'stackaddr', 'stcketodate', 'stcktodate', 'storage',
                        'string', 'substr', 'subto', 'subtract', 'succ', 'sum', 'sysnull',
                        'system', 'tally', 'tan', 'tand', 'tanh', 'threadid', 'time',
                        'timestamp', 'tiny', 'translate', 'trim', 'trunc', 'type', 'uhigh',
                        'ulength', 'ulength16', 'ulength8', 'ulow', 'unallocated', 'unhex',
                        'unsigned', 'unspec', 'upos', 'upperascii', 'uppercase',
                        'upperlatin1', 'usubstr', 'usupplementary', 'utcdatetime',
                        'utcmicrosecs', 'utcsecs', 'utf8', 'utf8stg', 'utf8tochar',
                        'utf8towchar', 'uuid', 'uuid4', 'uvalid', 'uwidth', 'valid',
                        'validdate', 'validvalue', 'varglist', 'vargsize', 'verify',
                        'verifyr', 'wcharval', 'weekday', 'wherediff', 'whigh', 'widechar',
                        'wlow', 'wscollapse', 'wscollapse16', 'wsreplace', 'wsreplace16',
                        'xmlchar', 'xmlscrub', 'xmlscrub16', 'xmluchar', 'y4date',
                        'y4julian', 'y4year',
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
