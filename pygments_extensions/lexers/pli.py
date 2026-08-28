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

Preprocessor ("macro facility") design decision, checked directly rather
than assumed: PL/I's compile-time preprocessor is a genuinely distinct
sub-language (its own statements, its own BIF set, its own scan-time
execution model, per IBM's "Preprocessor facilities" chapter,
https://www.ibm.com/docs/en/epfz/6.2.0?topic=reference-preprocessor-facilities)
-- but it does NOT need a dedicated push/pop lexer state the way
ooRexx's ::CLASS/::METHOD did, for reasons verified rather than assumed:

* IBM's own docs state outright that "preprocessor references and
  expressions are written and evaluated in the same way as described in
  ... Expressions and references" -- i.e. there is no separate
  compile-time expression grammar to parse; the existing root-state
  tokenization already handles it correctly by falling through to it.
* Pygments' own precedent (pygments.lexers.c_cpp.CFamilyLexer, checked
  directly) treats C's #-directives similarly lightly: its dedicated
  'macro' state swallows the rest of the directive as one Comment.Preproc
  blob without sub-tokenizing the expression inside `#if X > 5` at all
  (no Operator/Number tokens for X, >, 5) -- this PL/I lexer's
  "wildcard-token-then-fall-through-to-shared-grammar" approach is
  actually MORE granular than that established precedent, not less.
* IBM's own footnote on preprocessor procedures says statements inside a
  %PROCEDURE...%END body don't need the leading % (e.g. plain "IF ...
  THEN ... ELSE" inside a macro procedure means preprocessor-level
  control flow, not runtime). This sounds like it needs a distinct
  lexer state -- but doesn't in practice: those bare keywords (IF, THEN,
  ELSE, RETURN, etc.) already map to the identical Keyword.Reserved
  token type in ordinary root-state tokenization, so a dedicated state
  would produce no visibly different output. Confirmed by direct test
  (test_macro_procedure_body_uses_bare_keywords), not just this
  reasoning.

What IS fixed here after direct verification against IBM's actual
"Preprocessor statements" and "Preprocessor built-in functions" pages
(links in the tokens dict below): the %null statement (a bare "%;") was
a genuine bug -- a lone "%" not followed by a letter matched no rule at
all and produced an Error token, confirmed by direct test before the
fix; and 17 preprocessor-only BIFs (COMMENT, COMPILEDATE, COMPILETIME,
COPYRIGHT, COUNTER, MACCOL, MACLMAR, MACNAME, MACRMAR, PARMSET, QUOTE,
SERVICE, SYSDIMSIZE, SYSOFFSETSIZE, SYSPARM, SYSPOINTERSIZE, SYSVERSION)
were confirmed absent from the runtime BIF list and added.

Explicitly still simplified, not silently omitted: the %GO TO statement
tokenizes as two separate tokens (Comment.Preproc("%GO") +
Keyword.Reserved("TO")) rather than one merged unit -- a minor cosmetic
gap; whether argument-less preprocessor BIFs are ever invoked without
parentheses in real source is unconfirmed (see the "function" state
comment below); and BIF-name shadowing by a same-named user-declared
preprocessor procedure (a real semantic rule per IBM's docs) is a
parser-level symbol-table concern, correctly out of scope for a lexer.

Real-world validation pass: this lexer has now been run against ~80
real PL/I files it wasn't written against, from three sources -- see
samples/pli/real-world/ for the retained portion and its provenance.
This surfaced three more genuine, IBM-doc-confirmed bugs, all now
fixed:

* Identifiers are not limited to letters/digits/underscore. IBM's
  Enterprise PL/I Language Reference (Chapter 2, "Alphabetic and
  extralingual characters" / "Identifiers"), extracted and searched
  directly rather than recalled from memory: "The default extralingual
  characters are the number sign (#), the at sign (@), and the currency
  sign ($)... The first character of an identifier must be an
  alphabetic or extralingual character... Other characters, if any, can
  be alphabetic, extralingual, digit, or the break (_) character."
  Real-world testing found this missing entirely -- every "#"/"@"/"$"
  in every real identifier (extremely common in real mainframe PL/I:
  DB2/CICS program names, JCL-adjacent symbols) produced an Error
  token, e.g. across the code_samples/PDUMP/ and CALC.pli/CHART.pli/
  DDINFO.pli files in the corpus below.
* A bare ":" was rejected outside of a label. Two distinct, unrelated,
  and both entirely standard PL/I constructs use one: an array
  dimension's explicit lower:upper bound pair (e.g. "DCL A(0:1000)
  FIXED;", found repeatedly in the real-world corpus -- ordinary PL/I
  since the 1966 original, not an Enterprise extension) and a condition
  prefix, which enables/disables a condition for the statement it
  precedes (e.g. "(NOZERODIVIDE): stmt;" -- IBM Enterprise PL/I for
  z/OS, "Prefixes" -- found in the corpus as
  "(subrg,strg,size): reform: proc(parm) options(main);", using
  standard condition-name abbreviations SUBRG/STRG/SIZE). Both produced
  Error tokens before this fix; ":" is now a generic operator/
  punctuation character, the same treatment "." and "," already had.
  (This also happens to stop erroring on the ":hostvar" syntax inside
  embedded EXEC SQL/EXEC CICS regions -- see the next paragraph -- as a
  side effect, though that embedded syntax still isn't properly
  modeled.)
* A double-quoted string wasn't recognized anywhere, including as the
  file-spec argument to %INCLUDE (e.g. `%INCLUDE "b.pli";`). Ordinary
  PL/I character-string literals are always single-quoted (see the
  vocabulary-sourcing note above) -- IBM's own %INCLUDE documentation
  wasn't reachable to confirm double-quoting is specifically documented
  there, but real double-quoted %INCLUDE targets were found in the
  code_samples/plugin-example/ corpus below, and this exact form is
  exercised by zowe-pli-language-support's own PL/I tokenizer test
  fixtures (github.com/zowe/zowe-pli-language-support) -- a real,
  purpose-built PL/I tooling project treating it as valid input is
  itself reasonable authority here. Double-quoted strings are now
  accepted anywhere a single-quoted one is, the more permissive and
  simpler option for a highlighter (rather than trying to scope
  recognition to only-after-%INCLUDE, which would need new lexer
  state); real ordinary PL/I code doesn't use "..." at all, so this
  costs nothing there.

Embedded EXEC SQL / EXEC CICS, addressed in a follow-up pass after the
validation above flagged it: real-world testing found these regions in
10 of the ~80 real-world files (code_samples/plugin-example/sql.pli and
cics.pli, PLI0000.pli, PLI0001.pli, PLI0002.pli, DB2VRM.pli, INSERT.pli,
PTASK32.pli, PTASK34.pli, PTASKTS.pli in the zowe-pli-language-support
corpus -- reproduce with
`grep -rl "EXEC *SQL\\|EXEC *CICS" samples/pli/real-world/`). An
"EXEC SQL ..." or "EXEC CICS ..." statement is a genuinely distinct
embedded sub-language (its own statement grammar, and -- for SQL -- its
own ":hostvariable" reference syntax). Before this pass the lexer didn't
model it at all: SELECT/FROM inside EXEC SQL highlit only because they
coincidentally reuse PL/I's own SELECT-statement and FROM-clause
keywords -- accidental, not correctness.

Now handled by a dedicated "exec" lexer state (see the tokens dict
below), entered on a "(EXEC)(\\s+)(SQL|CICS)" match in root and left on
the terminating ";" -- the same "bracket the region, don't parse it"
approach upstream Pygments' pygments.lexers.c_cpp.CFamilyLexer takes for
C preprocessor directives in its own 'macro' state, and that this
lexer's own preprocessor handling already follows (see above). Design
decisions, each checked against the real-world corpus rather than
assumed:

* Terminator is a plain ";". Every one of the ~50 embedded statements
  in the corpus ends that way; none use "END-EXEC". "END-EXEC"
  (optionally followed by ";") is still accepted as an alternate
  terminator -- it is what the ISO embedded-SQL standard and other host
  languages (notably COBOL, whose statements don't otherwise end in
  ";") use, and it costs nothing to allow -- but it is not the PL/I
  norm and was not observed here.
* Multi-line regions work: the state persists across newlines until the
  ";" (real in the corpus -- code_samples/PTASK32.pli's "EXEC CICS
  IGNORE CONDITION" spans 15 lines; INSERT.pli's "EXEC SQL INSERT INTO
  ..." spans 4; DB2VRM.pli's "EXEC SQL DECLARE C CURSOR FOR" spans 2).
* Host-variable references (":name") tokenize as Punctuation +
  Name.Variable -- the one piece of embedded syntax modeled
  specifically, since it is unambiguous and common (":DEPT",
  ":STATEMENT", ":SQLDA", ":TIMESTAMP", ":BUF1_CLOB" across
  sql.pli / PLI0000-2.pli / DB2VRM.pli). A following ".qualifier" or
  ":indicator" falls through to the generic rules. Before this pass a
  bare ":host" produced Operator(":") + Text(name) -- itself only
  recently better than an Error token, after ":" became a generic
  operator character (see the "Real-world validation pass" section).
* Character-string literals ("'...'", and the "..." form this lexer
  also accepts) and "/* ... */" comments are recognized inside the
  region so that a ";" or "*/" occurring inside one cannot end it early
  (real: EXEC CICS FILE('VSR404'); EXEC SQL ... VALUES ('Igor', ...)).
* Everything else stays deliberately coarse: SQL keywords, CICS command
  verbs and option keywords, and table/column/file-name identifiers all
  tokenize as a single generic Name, not sub-classified into
  keyword-vs-name. Curating an SQL + CICS keyword vocabulary is
  parser-territory, out of scope for "reasonable Pygments-style
  highlighting", and matches both the CFamilyLexer precedent and this
  lexer's existing preprocessor treatment. (zowe-pli-language-support
  ships full dedicated ANTLR grammars for its CICS and DB2-SQL exec
  blocks -- packages/preprocessor-cics/src/antlr/ and
  packages/preprocessor-db2/src/antlr/ -- corroborating that anything
  past bracketing is a substantial separate effort. This does mean the
  prior accidental SELECT/FROM highlighting inside EXEC SQL goes away;
  that is intended.)
* The "exec" state ends with a catch-all so it can never emit an Error
  token (e.g. on dynamic SQL's "?" parameter marker), consistent with
  how the rest of the lexer degrades unrecognized input to Text.

EXEC DLI (IMS) is the third member of this family but was not found in
the real-world corpus, so -- per this project's "sourced, not guessed"
rule -- it is not added; the "exec" introducer regex is trivially
extensible to it if a real sample turns up.

Still not addressed, unchanged from the validation pass: one hobbyist
sample's use of U+2260 (≠) for not-equal (undocumented, left as a lexer
Error rather than added), and one test-fixture file's "//" following a
statement in a way that looks like an intended comment (unconfirmable
against IBM docs -- every IBM PL/I doc URL returned HTTP 403 that pass).
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

# A PL/I identifier isn't limited to plain word characters. Per IBM's
# Enterprise PL/I Language Reference, Chapter 2 ("Alphabetic and
# extralingual characters" / "Identifiers"): the first character must
# be an alphabetic or "extralingual" character (IBM's own term for
# "#", "@", and "$") or, for an INTERNAL symbol, the break character
# "_"; subsequent characters may be alphabetic, extralingual, digit, or
# "_". Confirmed missing by real-world testing -- see the module
# docstring above for the specific real files this broke on.
_SYMBOL_START = r"[a-z_#@$]"
_SYMBOL_CHAR = r"[\w#@$]"
_SYMBOL = _SYMBOL_START + _SYMBOL_CHAR + r"*"


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
            # A trailing Ctrl-Z (ASCII SUB, U+001A) is a legacy DOS/
            # mainframe-file-transfer end-of-file marker byte, not PL/I
            # source -- found trailing the real END statement in
            # code_samples/X501AA.PLI (zowe-pli-language-support
            # corpus), a plausible artifact in any PL/I file that has
            # passed through an old mainframe-to-PC transfer. Treated
            # as insignificant Text rather than an Error token.
            (r"\x1a", Text),
            (r"/\*", Comment.Multiline, "comment"),
            # Preprocessor ("macro facility") statements: %INCLUDE, %DCL,
            # %IF, %ACTIVATE, etc. This wildcard's coverage was checked
            # against IBM's complete, real "Preprocessor statements"
            # alphabetic index
            # (https://www.ibm.com/docs/en/SSY2V3_6.2/lr/prepst.html) --
            # every real preprocessor statement keyword (%ACTIVATE,
            # %DEACTIVATE, %DECLARE, %DO/%END, %GO TO, %IF, %INCLUDE,
            # %INSCAN, %ITERATE, %LEAVE, %NOTE, %REPLACE, %SELECT,
            # %XINCLUDE, %XINSCAN, and the unsupported-but-still-accepted
            # %CONTROL) already matches this wildcard, so this is now a
            # verified-complete design choice, not merely a
            # never-revisited placeholder. The %GO TO statement is the
            # one case not tokenized as a single unit (it becomes
            # Comment.Preproc("%GO") + Keyword.Reserved("TO") separately,
            # since "to" is already a recognized clause keyword) -- a
            # known minor cosmetic gap, not a correctness one.
            (r"%[a-z_]\w*", Comment.Preproc),
            # The %null statement (a bare "%;", the preprocessor
            # equivalent of a plain ";") is real and documented on that
            # same page -- confirmed as a genuine bug via direct testing
            # before this fix: a lone "%" not followed by a letter
            # matched no rule at all and fell through to an Error token.
            (r"%", Comment.Preproc),
            # Embedded EXEC SQL / EXEC CICS statements -- see the module
            # docstring's "Embedded EXEC SQL / EXEC CICS" section for the
            # full design rationale and how each decision was checked
            # against the real-world corpus. Enter a dedicated "exec"
            # state that brackets the region and leaves it on the
            # terminating ";" (or "END-EXEC"), rather than lexing the
            # embedded sub-language with PL/I's own rules.
            (
                r"(exec)(\s+)(sql|cics)\b",
                bygroups(Keyword.Reserved, Whitespace, Keyword.Reserved),
                "exec",
            ),
            # Bit-string and hex-string constants: '1010'B, '1F'X. These
            # must come before the generic character-string rule, since
            # both start with the same quote character -- only the
            # trailing radix letter distinguishes them, so order matters
            # (RegexLexer takes the first matching rule, not the most
            # specific).
            (r"'[01]+'[Bb]", Number.Bin),
            (r"'[0-9A-Fa-f]+'[Xx]", Number.Hex),
            (r"'", String, "string"),
            # Double-quoted strings: not used for ordinary PL/I
            # character constants (always single-quoted -- see the
            # vocabulary-sourcing note in the module docstring), but
            # real source uses them as the %INCLUDE file-spec argument
            # (e.g. `%INCLUDE "b.pli";`) -- see the module docstring for
            # sourcing. Accepted generically here (not scoped to just
            # after %INCLUDE) since ordinary PL/I code never uses a bare
            # '"' at all, so there's no real ambiguity to introduce.
            (r'"', String, "string_double"),
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
            (
                r"(" + _SYMBOL + r")([ \t]*)(:)",
                bygroups(Name.Label, Whitespace, Punctuation),
            ),
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
            (_SYMBOL, Text),
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
            # "!!" as an alternate spelling of "||" (concatenation):
            # IBM's Enterprise PL/I Language Reference, Chapter 2,
            # "Special characters", Note 1: "The or (|)... symbol[has]
            # variant code points. You can use the compiler option[]
            # OR... to define [an] alternate symbol to represent [this]
            # operator" -- the same code-page-variance mechanism the
            # module docstring above already documents for ¬/^. Found
            # in real-world source using exactly this alternate for
            # concatenation (POSREP = POSREP !! DEL !! REPTAB(I);, in
            # the zowe-pli-language-support corpus's X501AA.PLI) which
            # previously produced Error tokens on every "!". Scoped
            # narrowly to "!!" (composite concatenation), matching what
            # was actually observed, rather than treating a bare "!"
            # as a general alternate for "|" everywhere -- that broader
            # substitution isn't evidenced in any real source found.
            (r"\|\|=|!!=|\|\||!!", Operator),
            (r"->|=>", Operator),
            # <> is a documented alternate spelling of ¬= (not-equal in
            # ordinary comparisons; "exclusive-or and assign" in the
            # compound-assignment table specifically) -- confirmed on
            # both of the pages cited above.
            (r"<>", Operator),
            (r"[-+*/|&]=", Operator),
            # ":" is a generic punctuation/operator character, not just
            # part of a label. Two distinct, entirely standard PL/I
            # constructs use a bare ":" outside a label -- see the
            # module docstring for sourcing and real-world examples: an
            # array dimension's lower:upper bound pair (e.g.
            # "DCL A(0:1000) FIXED;") and a condition prefix (e.g.
            # "(NOZERODIVIDE): stmt;"). Both produced Error tokens
            # before this fix. The label rule above is listed earlier in
            # "root" and so still wins for the "identifier immediately
            # followed by a colon" shape it specifically matches.
            (r"[-+*/=<>&|.,;():]", Operator),
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
                        # Two more full attribute names, missing from the
                        # sets above and confirmed missing by real-world
                        # testing (real corpus files declaring
                        # SEQUENTIAL/BUFFERED files): "sequential" and
                        # "buffered"/"unbuffered" (with "environment",
                        # confirmed as a real attribute in IBM's own
                        # "ENV (ENVIRONMENT) attribute" index entry, used
                        # on file declarations to pass device/access
                        # information to the operating system).
                        "sequential", "buffered", "unbuffered",
                        "environment",
                        # REFER: the self-defining-data option, real and
                        # separately confirmed ("REFER option
                        # (self-defining data)", and "For BASED data,
                        # length must be a restricted expression, unless
                        # the string is a member of a structure or a
                        # union and the REFER option is used"). Confirmed
                        # missing by real-world testing -- used in three
                        # of this project's own quickfix/ test files
                        # (DCL-ambiguity edge cases the corpus below is
                        # specifically testing), e.g.
                        # "DCL 1 A, 2 N BIN, 2 B(N) CHAR(1) REFER(N);".
                        "refer",
                        # IBM's own documented short forms for many of
                        # the names above -- confirmed directly from the
                        # Enterprise PL/I Language Reference's own index,
                        # which lists each as "FULLNAME (ABBREV)
                        # attribute" (Tables 9 and 12, "Abbreviations for
                        # coded arithmetic/string data attributes", plus
                        # the same "X (Y) attribute" pattern recurring
                        # through the rest of the index for the
                        # remainder). Confirmed missing by real-world
                        # testing: BIN, CHAR, VAR, PIC, and INIT in
                        # particular are used far more often than their
                        # full spellings in real mainframe PL/I (e.g.
                        # code_samples/CALC.pli, DDINFO.pli, CHART.pli,
                        # PLEAREP.pli in the corpus below all use them).
                        "auto", "bin", "buf", "char", "cplx", "conn",
                        "ctl", "dec", "def", "dim", "env", "ext", "init",
                        "int", "nonvar", "pic", "pos", "prec", "ptr",
                        "seql", "unbuf", "var", "varz", "wchar",
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
                        # DO-statement Type 2/3 do-group clause keywords,
                        # confirmed directly on the DO-statement syntax
                        # diagram (Enterprise PL/I Language Reference,
                        # Ch. 9): "DO WHILE(exp4); ... UNTIL(exp5)" for
                        # Type 2, and "specification: exp1 TO exp2
                        # WHILE(exp4) BY exp3 UNTIL(exp5) REPEAT exp6"
                        # plus UPTHRU/DOWNTHRU (an ordinal-range option,
                        # "Example of DO with UPTHRU and DOWNTHRU") for
                        # Type 3. Confirmed missing by real-world
                        # testing: WHILE alone appears throughout the
                        # corpus below (e.g. code_samples/FILE.pli,
                        # preprocessor/do.pli).
                        "while", "until", "repeat", "upthru", "downthru",
                        # GET/PUT statement data-specification and
                        # layout-control keywords, confirmed directly on
                        # the "Data specification options" and "Options
                        # of data transmission statements" syntax
                        # sections (same reference, Ch. 13): "If a GET or
                        # PUT statement includes a data list that is not
                        # preceded by one of the keywords LIST, DATA, or
                        # EDIT, LIST is the default" (also documents
                        # COPY); Table 34 "Options and format items for
                        # PRINT files" documents PAGE/LINE/SKIP/COLUMN as
                        # PUT statement options; STRING is documented
                        # separately as the GET/PUT STRING statement
                        # option. Confirmed missing by real-world
                        # testing: SKIP and LIST in particular are
                        # near-ubiquitous ("PUT SKIP LIST(...)" appears
                        # throughout the corpus below, e.g.
                        # code_samples/FILE.pli, INSERT.pli, PLI0000.pli).
                        "list", "data", "edit", "copy", "skip", "page",
                        "line", "column", "string",
                        # IGNORE: a documented data-transmission-
                        # statement option ("IGNORE option of data
                        # transmission statements") -- confirmed missing
                        # by real-world testing (code_samples/PTASK32.pli,
                        # PTASK34.pli both use "ON ERROR IGNORE").
                        "ignore",
                        # SYSTEM: the documented implicit-system-handling
                        # ON-unit action (e.g. "on finish system;", shown
                        # directly in IBM's own worked example in
                        # Chapter 17, "Conditions").
                        "system",
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
                        # OPTIONS and RECURSIVE: real, extremely common
                        # PROCEDURE/ENTRY/BEGIN/PACKAGE-statement
                        # keywords, confirmed missing by real-world
                        # testing despite being present in nearly every
                        # real procedure (e.g. "PROC OPTIONS(MAIN);" is
                        # close to universal). Confirmed directly against
                        # IBM's Enterprise PL/I Language Reference's own
                        # syntax diagrams: "OPTIONS option and attribute"
                        # (Ch. 6, p.131) shows OPTIONS on PACKAGE,
                        # PROCEDURE, ENTRY, and BEGIN statements; the
                        # PROCEDURE-statement syntax diagram there
                        # separately shows "entry-label: PROCEDURE
                        # (parameter) returns-option OPTIONS(options)
                        # RECURSIVE scope-attribute;" -- RECURSIVE is its
                        # own attribute alongside, not inside, OPTIONS(),
                        # per "A procedure that is invoked recursively
                        # must have the RECURSIVE attribute specified in
                        # the PROCEDURE statement."
                        "options", "recursive",
                    ),
                    suffix=r"\b",
                ),
                Keyword.Reserved,
            ),
            # PROCEDURE/ENTRY/BEGIN/PACKAGE statement OPTIONS(...) values
            # -- the complete syntax-diagram list from the same "OPTIONS
            # option and attribute" reference section cited just above
            # (PROCEDURE-statement diagram, p.131-133): ASSEMBLER,
            # COBOL, FORTRAN, FETCHABLE, MAIN, NOEXECOPS, BYADDR,
            # BYVALUE, NOCHARGRAPHIC, CHARGRAPHIC, DESCRIPTOR,
            # NODESCRIPTOR, DLLINTERNAL, FROMALIEN, LINKAGE, NOMAP,
            # NOMAPIN, NOMAPOUT, NOINLINE, INLINE, ORDER, REORDER,
            # IRREDUCIBLE, REDUCIBLE, REENTRANT, RETCODE, WINMAIN, plus
            # their own documented abbreviations (ASSEMBLER -> ASM,
            # CHARGRAPHIC -> CHARG, NOCHARGRAPHIC -> NOCHARG, again per
            # that same reference section, not guessed). Confirmed
            # missing by real-world testing: MAIN and REORDER in
            # particular appear on the overwhelming majority of real
            # PROCEDURE statements in the corpus below (e.g.
            # code_samples/CALC.pli, CHART.pli, PDUMP/*.pli all use
            # "OPTIONS(MAIN)" or "OPTIONS(MAIN REORDER)"), and fell
            # through as plain Text before this fix.
            (
                words(
                    (
                        "assembler", "asm", "cobol", "fortran",
                        "fetchable", "main", "noexecops", "byaddr",
                        "byvalue", "nochargraphic", "nocharg",
                        "chargraphic", "charg", "descriptor",
                        "nodescriptor", "dllinternal", "fromalien",
                        "linkage", "nomap", "nomapin", "nomapout",
                        "noinline", "inline", "order", "reorder",
                        "irreducible", "reducible", "reentrant",
                        "retcode", "winmain",
                    ),
                    suffix=r"\b",
                ),
                Keyword.Reserved,
            ),
            # Condition names, used in ON/SIGNAL/REVERT statements and
            # condition prefixes (e.g. "ON ENDFILE(f) ...",
            # "(NOSIZE): stmt;"). This is the complete, exhaustive list
            # from Chapter 17, "Conditions", of the Enterprise PL/I
            # Language Reference, which covers exactly these 23 names in
            # alphabetic order (CONDITION itself, the 24th, is already
            # covered via the "attribute" state's CONDITION attribute
            # entry -- the two uses share the same word). Confirmed
            # missing by real-world testing: ENDFILE and CONVERSION in
            # particular appear directly in the corpus below (e.g.
            # code_samples/FILE.pli's "ON ENDFILE", MACROS.pli's "ON
            # CONVERSION").
            (
                words(
                    (
                        "anycondition", "area", "attention", "conversion",
                        "endfile", "endpage", "error", "finish",
                        "fixedoverflow", "invalidop", "key", "name",
                        "overflow", "record", "size", "storage",
                        "stringrange", "stringsize", "subscriptrange",
                        "transmit", "undefinedfile", "underflow",
                        "zerodivide",
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
                        # ONCODE: confirmed missing from the original
                        # "complete" 420-name list -- a real gap in that
                        # sourcing pass, not a since-added name. IBM's
                        # own "Condition handling" chapter singles it
                        # out specifically ("The ONCODE built-in function
                        # is particularly useful here, as it can be used
                        # to identify the specific circumstances that
                        # raised the condition[]"), and real-world
                        # testing found it used directly in the corpus
                        # below (code_samples/MACROS.pli's "ON ERROR
                        # ONCODE").
                        'oncode',
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
            # ONCODE/ONLOC/ONCHAR/ONSOURCE used with no trailing "(" at
            # all -- confirmed as real, not a typo, by real-world
            # testing: code_samples/MACROS.pli both declares them
            # explicitly ("DCL (ALLOCATION,INDEX,ONLOC,ONCODE,ONCHAR,
            # ONSOURCE) BUILTIN;") and then uses each bare, as a plain
            # value, inside a PUT EDIT data list ("PUT SKIP EDIT(...,
            # ONLOC, ..., ONCODE, ..., ONSOURCE)(A)"). These four are
            # specifically the built-in functions IBM's "Condition
            # handling" chapter describes as taking no arguments and
            # returning information about the currently-raised
            # condition, so this isn't specific to these four literal
            # names by accident -- the same allowance plausibly applies
            # to the rest of the "on*" condition-inquiry BIF family
            # above (onkey, onfile, onsubscript, etc.), but only these
            # four were directly observed used this way in the corpus,
            # so only these four are added here rather than
            # generalizing on assumption.
            (
                words(
                    ("oncode", "onloc", "onchar", "onsource"),
                    suffix=r"\b",
                ),
                Name.Builtin,
            ),
            # Preprocessor-only built-in functions: confirmed, by direct
            # comparison against the runtime BIF list above, to be a
            # genuinely separate set -- not simply a subset of the
            # runtime BIFs, per IBM's complete "Preprocessor built-in
            # functions" list
            # (https://www.ibm.com/docs/en/SSY2V3_6.2/lr/prbif.html).
            # 17 of that page's 34 names (COMMENT, COMPILEDATE,
            # COMPILETIME, COPYRIGHT, COUNTER, MACCOL, MACLMAR, MACNAME,
            # MACRMAR, PARMSET, QUOTE, SERVICE, SYSDIMSIZE,
            # SYSOFFSETSIZE, SYSPARM, SYSPOINTERSIZE, SYSVERSION) do not
            # appear at all in the runtime list; the other 17 (SUBSTR,
            # LENGTH, MAX, MIN, etc.) already do and so aren't repeated
            # here. Not modeled: the semantic rule that a BIF name can be
            # shadowed by a same-named user-declared preprocessor
            # procedure (requires symbol-table tracking, a parser-level
            # concern, out of scope for a lexer). Also not confirmed:
            # IBM's page notes that 17 of these (the argument-less ones,
            # e.g. SYSPARM, COMPILEDATE, COUNTER) "must not be given a
            # null argument" -- if real source ever invokes them bare,
            # with no parentheses at all, this rule's suffix=r"(\()"
            # requirement means they'd fall through to plain Text
            # instead of Name.Builtin. Not verified either way; flagged
            # rather than assumed.
            (
                words(
                    (
                        'comment', 'compiledate', 'compiletime', 'copyright',
                        'counter', 'maccol', 'maclmar', 'macname', 'macrmar',
                        'parmset', 'quote', 'service', 'sysdimsize',
                        'sysoffsetsize', 'sysparm', 'syspointersize',
                        'sysversion',
                    ),
                    suffix=r"(\s*)(\()",
                ),
                bygroups(Name.Builtin, Whitespace, Operator),
            ),
        ],
        "exec": [
            # Dedicated state for an embedded EXEC SQL / EXEC CICS
            # statement -- see the module docstring's "Embedded EXEC SQL
            # / EXEC CICS" section for the design and its sourcing
            # against the real-world corpus.
            #
            # Terminated by a plain ";" (every one of the ~50 embedded
            # statements in the real-world corpus ends this way). Listed
            # first so it wins over the generic-punctuation rule below.
            (r";", Punctuation, "#pop"),
            # "END-EXEC" (optionally followed by ";") is the terminator
            # the ISO embedded-SQL standard and COBOL use; accepted as an
            # alternate even though no PL/I file in the corpus uses it. A
            # trailing ";" then falls through to root as an ordinary
            # statement terminator.
            (r"end-exec\b", Keyword.Reserved, "#pop"),
            (r"\s+", Whitespace),
            # A "/* ... */" comment can appear mid-statement; the shared
            # "comment" state pops straight back here, so a ";" inside
            # the comment can't end the region early.
            (r"/\*", Comment.Multiline, "comment"),
            # Host-variable reference (SQL): ":name". Any following
            # ".qualifier" or ":indicator" falls through to the generic
            # rules below. Real in the corpus: ":DEPT", ":STATEMENT",
            # ":SQLDA", ":TIMESTAMP", ":BUF1_CLOB".
            (
                r"(:)(\s*)(" + _SYMBOL + r")",
                bygroups(Punctuation, Whitespace, Name.Variable),
            ),
            # String literals -- recognized so an embedded ";" or "*/"
            # inside one doesn't end the region/comment. Corpus:
            # EXEC CICS FILE('VSR404'); EXEC SQL ... VALUES ('Igor',...).
            (r"'", String, "string"),
            (r'"', String, "string_double"),
            (r"[0-9]+(?:\.[0-9]+)?(?:[Ee][+-]?[0-9]+)?", Number),
            # Everything else stays coarse on purpose: SQL keywords, CICS
            # command verbs and option keywords, and table/column/file
            # names all become a single generic Name (see the module
            # docstring for why this matches the CFamilyLexer 'macro'
            # precedent and this lexer's own preprocessor handling).
            (_SYMBOL, Name),
            (r"[(),.]", Punctuation),
            (r"[-+*/=<>|&:]", Operator),
            # Catch-all: never emit an Error token from inside an
            # embedded region (e.g. dynamic SQL's "?" parameter marker),
            # consistent with how the rest of the lexer degrades
            # unrecognized input to Text.
            (r".", Text),
        ],
        "string": [
            (r"[^'\n]+", String),
            (r"''", String),
            (r"'", String, "#pop"),
            (r"\n", Text, "#pop"),  # Stray linefeed also terminates strings.
        ],
        "string_double": [
            (r'[^"\n]+', String),
            (r'""', String),
            (r'"', String, "#pop"),
            (r"\n", Text, "#pop"),  # Stray linefeed also terminates strings.
        ],
        "comment": [
            (r"[^*]+", Comment.Multiline),
            (r"\*/", Comment.Multiline, "#pop"),
            (r"\*", Comment.Multiline),
        ],
    }
