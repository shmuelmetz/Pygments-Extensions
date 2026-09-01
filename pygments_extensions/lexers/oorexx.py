"""
ooRexx (Open Object Rexx) lexer.

Built as an independent fork of Pygments' built-in classic-Rexx lexer
(``pygments.lexers.scripting.RexxLexer``, itself unchanged since the ideas
here were drafted) rather than a subclass, since the two languages need
different ``analyse_text`` heuristics and additional lexer states that
don't cleanly layer on top of inheritance. The classic-Rexx token rules
(comments, strings, numbers, the label/procedure patterns, the shared
operator and built-in-function sets) are carried over essentially as-is,
since ooRexx is upwardly compatible with classic Rexx and executes
unmodified classic Rexx programs.

What's new here, specific to the object-oriented layer ooRexx adds:

* ``::CLASS`` / ``::METHOD`` / ``::ROUTINE`` / ``::REQUIRES`` /
  ``::ATTRIBUTE`` / ``::CONSTANT`` / ``::OPTIONS`` / ``::RESOURCE`` /
  ``::PACKAGE`` directive lines.
* Message-send syntax: ``~`` and ``~~`` (cascading message send), and
  ``[`` / ``]`` -- bracket notation is itself sugar for a ``[]`` message
  send in ooRexx (e.g. ``stem[foo] = bar``), not just array-indexing
  punctuation, distinct from the classic Rexx compound-variable
  ``stem.tail`` access which is plain inherited syntax with no
  message-send semantics. See AI-Priming/ooRexx/RULES.md, "Indirect/
  computed stem access: three forms" for the full three-way distinction
  this is drawn from.
* Dot-prefixed environment-directory symbol lookups (``.array``,
  ``.string``, ``.true``, ``.MyClass``). A leading dot does not itself
  mean "this is a class" -- it designates a lookup of the following name
  in ooRexx's environment directory, the special symbol table holding
  ``.true``/``.false``/``.nil``, built-in classes like ``.array``,
  user-defined classes, and other environment entries alike. Classes are
  commonly what's found there, but the syntax is a general directory
  lookup, not class-specific syntax -- so this is tokenized as a single
  ``Name.Variable.Global`` token (a directory is effectively a global
  symbol table) rather than as ``Name.Class``, and rather than falling
  through to a bare Operator(".") + Text(name) split.
* The additional OO keywords these features bring along: ``guard``,
  ``expose``, ``forward``, ``use``, ``self``, ``super``.

Real-world validation (resolved): the ``analyse_text`` disambiguation
heuristic below -- weighted to prefer this lexer specifically when OO
markers (a ``::`` directive, or a ``~`` message send) are present in the
body -- has now been checked against real-world source, not just the
hand-written samples in samples/oorexx/ and tests/test_oorexx.py. The
corpus: ~30 files from the official ooRexx/ooRexx interpreter repo's own
samples/, extensions/, and interpreter/RexxClasses/ directories (real
OO-heavy library code, e.g. the JSON/YAML class libraries and the
built-in CoreClasses.orx); 7 genuinely classic-Rexx-only files (no OO
markers at all) from RexxLA/rexx-repository's Classic_Rexx/ tree, used
as negative cases; and 10 community-contributed snippets from Rosetta
Code's ooRexx category. Across all of these, analyse_text scored 0.0 on
every classic-only file (no false positives) and correctly preferred
this lexer (score > 0, usually 1.0) on every genuine ooRexx file that
had *any* OO marker in it -- see samples/oorexx/real-world/ for the
retained portion of this corpus and its provenance. One real gap the
corpus did surface, now fixed below rather than in the heuristic itself:
plain classic-Rexx-style ooRexx files that happen not to use ``::`` or
``~`` at all (e.g. samples/api/classic/unix/rexxapi1/apitest1.rex, which
ships *inside* the ooRexx distribution but contains no OO syntax) score
0.0 here and fall through to classic RexxLexer -- which is correct,
since such a file's tokenization is identical either way; there is
nothing for this lexer to add. The heuristic itself needed no changes.

What real-world testing DID find and fix (see the lexer body below for
each, and tests/test_oorexx.py for regression coverage): the ``--``
line-comment form (ooRexx Reference 5.0.0 Sec 1.10.3) was not recognized
at all and left every one of its comments to be mis-tokenized word by
word; a leading ``#!`` shebang line (used throughout the official
project's own Unix sample scripts) produced Error tokens; ooRexx's
inherited classic-Rexx symbol charset (letters, digits, and
``@ # $ ! ? _`` -- IBM's TSO/E REXX Reference, since ooRexx documents
itself as upwardly compatible with classic Rexx symbol rules) was
under-recognized, rejecting real symbols like the ``?`` conditional-
selection message name used in the project's own samples/complex.cls;
and the ``~name:ClassSymbol`` scoped/explicit method-search-order form
(ooRexx Reference 5.0.0 Sec 4.2.7, e.g. ``self~init:super``) wasn't
recognized at all, despite being used repeatedly in the official
samples/pipe.cls. ``::CLASS``/``::METHOD``/``::ATTRIBUTE`` directive
modifier keywords (PUBLIC, PRIVATE, PACKAGE, PROTECTED, UNPROTECTED,
GUARDED, UNGUARDED, ABSTRACT, DELEGATE, EXTERNAL, METACLASS,
MIXINCLASS, SUBCLASS, INHERIT, the bare CLASS/GET/SET modifiers -- all
per ooRexx Reference 5.0.0 Sec 3.2/3.3/3.5) were falling through as
plain Text despite being extremely common on real ``::CLASS``/
``::METHOD`` lines; they're now recognized as Keyword.Declaration.

Cross-check against an independent lexer (2026-09): Till Winkler
(RexxLA members list) shared a second ooRexx Pygments lexer he wrote
independently from the ooRexx documentation, and a feature-by-feature
comparison against a 95-case corpus found six real gaps here --
``USE LOCAL`` and ``SELECT CASE`` (5.0), ``ADDRESS ... WITH`` I/O
redirection sub-keywords (5.0), the ooRexx-specific condition names
(``LOSTDIGITS``/``NOMETHOD``/``NOSTRING``/``USER``), the ``::ANNOTATE``
directive (5.0, previously producing raw Error tokens since no rule
matched a bare unrecognized ``::``), and ``::RESOURCE``/``::OPTIONS``
body handling (previously absent for ``::RESOURCE``, entirely
unhandled beyond the bare directive keyword for ``::OPTIONS``) -- now
ported in below, implemented independently against the ooRexx
reference rather than copied from his file. The same comparison found
his lexer's own ``::OPTIONS`` body has no identifier-or-number rule
and splits any value that isn't itself a sub-keyword into one
character-token per character; this port's version (see
``options_body`` below) fixes that rather than reproducing it. See
``tests/test_oorexx.py``'s cross-check regression tests for coverage
of all of the above.
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

# Condition names recognized by SIGNAL/CALL ON|OFF (and, since ooRexx 5.0,
# ::OPTIONS' CONDITION subkeyword). ERROR/FAILURE/HALT/NOVALUE/SYNTAX/
# NOTREADY are inherited from classic Rexx; LOSTDIGITS, NOMETHOD, NOSTRING,
# and USER (user-defined conditions raised via RAISE) are ooRexx additions.
# Verified against a second, independently-written ooRexx lexer (Till
# Winkler's, RexxLA members list, 2026-09) as a cross-check before adding.
_CONDITIONS = (
    "error", "failure", "halt", "lostdigits", "nomethod", "nostring",
    "notready", "novalue", "syntax", "user",
)

# ::OPTIONS body sub-keywords (ooRexx 5.0's ::OPTIONS directive sets
# package-wide parser/runtime options). Cross-checked against Till
# Winkler's independently-written lexer, which already enumerated these
# from the ooRexx docs; his version had a real bug here (see
# "options_body" state below) that this port fixes rather than repeats.
_OPTIONS_SUBKW = (
    "condition", "digits", "error", "failure", "form", "fuzz",
    "lostdigits", "namespace", "nocrossref", "noformat", "noprolog",
    "noreplace", "nostrictargs", "nostrictassign", "nostrictcase",
    "nostrictsignal", "nostring", "notrace", "notready", "novalue",
    "noverbose", "normal", "prolog", "syntax", "trace", "verbose",
)

__all__ = ["OORexxLexer"]

# A Rexx "symbol" (identifier) is not limited to plain word characters.
# Per IBM's TSO/E REXX Reference (the authoritative cross-dialect source
# for classic-Rexx symbol rules, which ooRexx documents itself as
# upwardly compatible with): a symbol consists of letters, digits, and
# the special characters "@ # $ . ! ? _" (the cent sign, historically
# also included, is omitted here as it's not observable in any UTF-8
# real-world source and is not otherwise meaningful to a Pygments
# lexer). "." is deliberately excluded from these classes -- it is
# handled separately below (environment-directory lookups, and the
# generic "." operator for compound-variable tails) rather than folded
# into a single "symbol" token, an existing, deliberate simplification
# unrelated to this fix. Confirmed missing for the rest of the set
# (@ # $ ! ?) by real-world testing: e.g. the "?" conditional-selection
# message name in the official project's own samples/complex.cls
# (`sign~?(-1, 1)`), and "$"-prefixed variable names in real classic
# Rexx source from the same era this symbol rule originates in.
_SYMBOL_START = r"[a-z_@#$!?]"
_SYMBOL_CHAR = r"[\w@#$!?]"
_SYMBOL = _SYMBOL_START + _SYMBOL_CHAR + r"*"
# A label may itself be a compound symbol (stem.tail, e.g. "TRAP.SIGL:"
# or "UTF.8:") -- a common convention for grouping related SIGNAL/CALL
# targets under a shared prefix. _SYMBOL alone stops at the first ".",
# so without this, "TRAP.SIGL:" tokenized as bare-symbol "TRAP" (Text,
# via the catch-all rule) followed by ".SIGL" (matching the unrelated
# dot-prefixed-environment-symbol rule below) followed by a now-orphaned
# ":" that no rule expects, producing an Error token on the colon.
# Confirmed via real-world testing (D:\utility\rxwhois.cmd, a genuine
# classic-Rexx script using exactly this labeling convention).
# A compound symbol's tail piece may also be a bare number (e.g.
# "UTF.8:", "stem.1") -- _SYMBOL alone can't match that since
# _SYMBOL_START excludes digits, confirmed by the same real-world test
# file above (D:\utility\rxwhois.cmd's "UTF.8:" label).
_COMPOUND_SYMBOL = _SYMBOL + r"(?:\.(?:" + _SYMBOL + r"|[0-9]+))*"


class OORexxLexer(RegexLexer):
    """
    Open Object Rexx is an open-source, object-oriented extension of
    classic Rexx: it executes unmodified classic Rexx programs and adds
    classes, methods, and message-send syntax on top.
    """

    name = "ooRexx"
    url = "https://www.oorexx.org/"
    aliases = ["oorexx", "openobjectrexx"]
    filenames = ["*.rex", "*.orx", "*.cls"]
    mimetypes = []
    version_added = "0.1"
    flags = re.IGNORECASE | re.MULTILINE

    tokens = {
        "root": [
            # A leading "#!" line (a Unix shebang, e.g.
            # "#!/usr/bin/env rexx") is standard content in real ooRexx
            # scripts -- the official project's own samples/ ship it in
            # nearly every Unix sample, and the ooRexx SourceForge
            # tracker treats a *missing* shebang as a bug in a sample
            # file. \A anchors this to the very start of the source, so
            # it can never fire on a "#" appearing later as part of an
            # ordinary symbol (see _SYMBOL_START below, which does allow
            # "#" mid-program). Mirrors Pygments' own BashLexer, which
            # uses the identical `\A#!.+\n` -> Comment.Hashbang pattern
            # for the same real-world construct.
            (r"\A#!.*\n", Comment.Hashbang),
            (r"\s+", Whitespace),
            (r"/\*", Comment.Multiline, "comment"),
            # Line comment: two subsequent minus signs to end of line.
            # Confirmed in the ooRexx 5.0.0 Reference, Sec 1.10.3
            # "Comments": "A line comment is started by two subsequent
            # minus signs (--) and ends at the end of a line." This is
            # an ooRexx/modern-Rexx-only comment form (on top of the
            # classic /* */ form carried over below) -- extremely common
            # in real source (nearly every official sample uses it for
            # inline documentation) and, before this fix, entirely
            # unhandled: each "--" was mis-split into two Operator("-")
            # tokens and the comment text itself mis-tokenized word by
            # word as if it were code. Must be listed before the
            # "operator" include below, so the second "-" doesn't win
            # the single-hyphen operator rule first.
            (r"--.*", Comment.Single),
            (r'"', String, "string_double"),
            (r"'", String, "string_single"),
            (r"[0-9]+(\.[0-9]+)?(e[+-]?[0-9])?", Number),
            # ooRexx directives: ::CLASS, ::METHOD, ::ROUTINE, etc.
            # Must come before the generic operator rule below, since
            # plain Rexx has no other use of a doubled colon.
            (
                r"(::)(\s*)"
                r"(class|method|routine|requires|attribute|constant|"
                # ::ANNOTATE (5.0) was missing entirely -- found via
                # cross-check against Till Winkler's independently-
                # written ooRexx lexer (RexxLA members list, 2026-09):
                # "::" isn't matched by the operator rule (no bare ":"
                # token exists there), so an unrecognized "::" produced
                # an Error token, confirmed against this file before
                # this fix.
                r"annotate|package)\b",
                bygroups(Keyword.Namespace, Whitespace, Keyword.Declaration),
            ),
            # ::RESOURCE name -- transitions to a raw-text body state
            # (see "resource_body" below), terminated by a line
            # containing only "::". Must come before the generic
            # directive rule above's match window closes, but since
            # that rule doesn't push a state, list this dedicated
            # ::RESOURCE form first so it wins and enters resource_body.
            (
                r"(::)(\s*)(resource)\b([ \t]*)(" + _SYMBOL + r")?",
                bygroups(
                    Keyword.Namespace,
                    Whitespace,
                    Keyword.Declaration,
                    Whitespace,
                    Name.Label,
                ),
                "resource_body",
            ),
            # ::OPTIONS -- transitions to its sub-keyword body state
            # (see "options_body" below), which lasts until end of line.
            (
                r"(::)(\s*)(options)\b",
                bygroups(Keyword.Namespace, Whitespace, Keyword.Declaration),
                "options_body",
            ),
            # Dot-prefixed environment-directory symbol lookups: .array,
            # .string, .true, .false, .nil, .MyClass, etc. The dot means
            # "look this up in the environment directory", not "this is
            # a class" -- classes are commonly, but not exclusively,
            # what's found there. Placed before the generic operator
            # rule so the leading "." doesn't get split off on its own
            # as a bare Operator token.
            (r"\." + _SYMBOL, Name.Variable.Global),
            # Scoped/explicit message send: obj~method:ClassSymbol, e.g.
            # self~init:super. Confirmed in the ooRexx 5.0.0 Reference,
            # Sec 4.2.7 "Changing the Search Order for Methods": "You
            # can change the usual search order for methods by
            # specifying a colon and a class symbol after the message
            # name... The class symbol is usually the special variable
            # SUPER, but it can be any environment symbol or variable
            # name." Used repeatedly in the official project's own
            # samples/pipe.cls. Must come before the plain message-send
            # rule below (a longer, more specific alternative listed
            # first), since otherwise the plain rule consumes only the
            # message name and leaves a bare ":" that nothing else
            # matches -- confirmed by real-world testing to previously
            # produce an Error token on every occurrence. The class
            # symbol itself may be a dot-prefixed environment symbol
            # (":.MyClass"), tagged the same as the equivalent bare
            # ".MyClass" form elsewhere in this lexer (Name.Variable.
            # Global), or a plain variable/environment name (":super"),
            # tagged generically as Text -- note this is plain Text even
            # for the literal word "super", not Keyword.Reserved as a
            # bare "super" elsewhere gets: in this position it names an
            # environment symbol to search from, a different
            # grammatical role than "super" the message-receiver
            # keyword, and bygroups() can't conditionally re-check a
            # captured group against the keyword list.
            (
                r"(~~|~)(\s*)(" + _SYMBOL + r")(\s*)(:)(\s*)(\." + _SYMBOL + r")",
                bygroups(
                    Operator,
                    Whitespace,
                    Name.Function,
                    Whitespace,
                    Operator,
                    Whitespace,
                    Name.Variable.Global,
                ),
            ),
            (
                r"(~~|~)(\s*)(" + _SYMBOL + r")(\s*)(:)(\s*)(" + _SYMBOL + r")",
                bygroups(
                    Operator,
                    Whitespace,
                    Name.Function,
                    Whitespace,
                    Operator,
                    Whitespace,
                    Text,
                ),
            ),
            # Message-send operators. ~~ (cascading send) must be
            # listed before ~ since RegexLexer tries rules in order and
            # takes the first match, not the longest.
            (
                r"(~~|~)(\s*)(" + _SYMBOL + r")",
                bygroups(Operator, Whitespace, Name.Function),
            ),
            (r"[\[\]]", Operator),
            # Same-line whitespace only ([ \t]*, not \s*) -- a bare \s*
            # here would cross newlines and can swallow the first colon
            # of a following-line "::" directive as part of a label
            # match (e.g. "Point\n::METHOD" reads as label "Point" then
            # a stray second colon), starving the directive rule above
            # of a chance to match. Confirmed by test failure before
            # this fix.
            (
                r"(" + _COMPOUND_SYMBOL + r")([ \t]*)(:)([ \t]*)(procedure)\b",
                bygroups(
                    Name.Function,
                    Whitespace,
                    Operator,
                    Whitespace,
                    Keyword.Declaration,
                ),
            ),
            (
                r"(" + _COMPOUND_SYMBOL + r")([ \t]*)(:)",
                bygroups(Name.Label, Whitespace, Operator),
            ),
            include("function"),
            include("keyword"),
            include("operator"),
            (_SYMBOL, Text),
        ],
        "function": [
            (
                words(
                    (
                        "abbrev", "abs", "address", "arg", "b2x", "bitand",
                        "bitor", "bitxor", "c2d", "c2x", "center", "charin",
                        "charout", "chars", "compare", "condition", "copies",
                        "d2c", "d2x", "datatype", "date", "delstr", "delword",
                        "digits", "errortext", "form", "format", "fuzz",
                        "insert", "lastpos", "left", "length", "linein",
                        "lineout", "lines", "max", "min", "overlay", "pos",
                        "queued", "random", "reverse", "right", "sign",
                        "sourceline", "space", "stream", "strip", "substr",
                        "subword", "symbol", "time", "trace", "translate",
                        "trunc", "value", "verify", "word", "wordindex",
                        "wordlength", "wordpos", "words", "x2b", "x2c",
                        "x2d", "xrange",
                    ),
                    suffix=r"(\s*)(\()",
                ),
                bygroups(Name.Builtin, Whitespace, Operator),
            ),
        ],
        "keyword": [
            (
                r"(address|arg|by|call|do|drop|else|end|exit|expose|for|"
                r"forever|forward|guard|if|interpret|iterate|leave|nop|"
                r"numeric|off|on|options|otherwise|parse|pull|push|queue|"
                r"return|say|select|self|signal|strict|super|then|to|"
                r"trace|until|use|when|while|"
                # USE LOCAL (5.0) and SELECT CASE (5.0) sub-keywords --
                # gap found via cross-check against Till Winkler's
                # independently-written ooRexx lexer, RexxLA members
                # list 2026-09; both fell through to plain Text before.
                r"local|case|"
                # ADDRESS ... WITH <io-type> STEM|STREAM redirection
                # (5.0) sub-keywords. Same cross-check.
                r"with|input|output|stem|stream|append|replace|normal)\b",
                Keyword.Reserved,
            ),
            # Condition names, valid after SIGNAL/CALL ON|OFF and
            # ::OPTIONS' CONDITION sub-keyword. See _CONDITIONS above.
            (words(_CONDITIONS, prefix=r"\b", suffix=r"\b"), Keyword.Type),
            # ::CLASS / ::METHOD / ::ATTRIBUTE directive modifier
            # keywords -- e.g. "::method foo class public",
            # "::class Vector subclass complex public",
            # "::class Stringlike public mixinclass object". Confirmed
            # against the ooRexx 5.0.0 Reference: the ::METHOD directive
            # (Sec 3.5) accepts ATTRIBUTE/CLASS/PUBLIC/PACKAGE/PRIVATE/
            # GUARDED/UNGUARDED/UNPROTECTED/PROTECTED/ABSTRACT/DELEGATE/
            # EXTERNAL; ::CLASS (Sec 3.3) accepts METACLASS/PRIVATE/
            # PUBLIC/MIXINCLASS/SUBCLASS/ABSTRACT/INHERIT; ::ATTRIBUTE
            # (Sec 3.2) additionally accepts GET/SET. Before this fix,
            # real-world testing found every one of these falling
            # through as plain Text on real ::CLASS/::METHOD lines --
            # PUBLIC and MIXINCLASS/SUBCLASS in particular are near-
            # universal in real class hierarchies (e.g. the official
            # project's own samples/complex.cls and samples/pipe.cls).
            (
                r"(public|private|package|protected|unprotected|guarded|"
                r"unguarded|abstract|delegate|external|metaclass|"
                r"mixinclass|subclass|inherit|attribute|class|get|set)\b",
                Keyword.Declaration,
            ),
        ],
        "operator": [
            # ";" is the explicit clause (statement) delimiter -- lets
            # multiple Rexx clauses share one physical line (e.g.
            # "self~write(counter);"). Real-world testing found this
            # missing entirely: every semicolon in every multi-clause
            # line across the whole corpus produced an Error token,
            # since normally clauses are separated by newlines and this
            # explicit form, while extremely common in real object
            # method bodies, happened not to appear in the original
            # hand-written samples/tests this lexer shipped with.
            # "¬" (U+00AC, NOT SIGN) is a documented alternate spelling
            # for "\" as the NOT operator (¬=, ¬>, ¬<, or standalone ¬x)
            # -- inherited from mainframe/DOS-era code pages where some
            # keyboards render backslash as this glyph instead. Real-
            # world testing (D:\utility\*.cmd, a genuine ArcaOS-era
            # script corpus) found it used throughout and entirely
            # unhandled: every occurrence produced an Error token.
            (
                r"(-|//|/|\(|\)|\*\*|\*|"
                r"\\<<|\\<|\\==|\\=|\\>>|\\>|\\|"
                r"\u00ac<<|\u00ac<|\u00ac==|\u00ac=|\u00ac>>|\u00ac>|\u00ac|"
                r"\|\||\||&&|&|%|\+|<<=|<<|<=|<>|<|==|=|><|>=|>>=|>>|>|\.|,|;)",
                Operator,
            ),
        ],
        "string_double": [
            (r'[^"\n]+', String),
            (r'""', String),
            (r'"', String, "#pop"),
            (r"\n", Text, "#pop"),  # Stray linefeed also terminates strings.
        ],
        "string_single": [
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
        # ::OPTIONS body -- a line of package-wide parser/runtime
        # sub-keywords (see _OPTIONS_SUBKW above), e.g.
        # "::options digits 15 namespace myns". Gap and a concrete bug
        # found via cross-check against Till Winkler's independently-
        # written ooRexx lexer (RexxLA members list, 2026-09): his
        # version's equivalent state has no identifier-or-number rule,
        # so any value that isn't itself a recognized sub-keyword (the
        # "15" and "myns" above) falls to a single-character catch-all
        # and gets split into one Text token per character. Fixed here
        # by including "function" (numbers) and a plain identifier
        # fallback rule, not just the sub-keyword list.
        "options_body": [
            (r"\n", Whitespace, "#pop"),
            (r"[ \t]+", Whitespace),
            (r"--.*", Comment.Single),
            (r"/\*", Comment.Multiline, "comment"),
            include("strings"),
            (words(_OPTIONS_SUBKW, prefix=r"\b", suffix=r"\b"), Keyword.Type),
            (r"[0-9]+(\.[0-9]+)?(e[+-]?[0-9])?", Number),
            (_SYMBOL, Text),
        ],
        # ::RESOURCE body -- raw text (not Rexx code) until a line
        # containing only "::". Previously unhandled entirely: the
        # ::RESOURCE keyword itself was recognized as a directive, but
        # its body was left to fall through to ordinary code rules,
        # which mis-tokenizes arbitrary resource content as if it were
        # Rexx. Gap found via cross-check against Till Winkler's
        # independently-written ooRexx lexer (RexxLA members list,
        # 2026-09), which already handles this correctly.
        "resource_body": [
            (r"^[ \t]*::[ \t]*$", Keyword.Namespace, "#pop"),
            (r"[^\n]+", String.Other),
            (r"\n", String.Other),
        ],
        "strings": [
            (r'"', String, "string_double"),
            (r"'", String, "string_single"),
        ],
    }

    def analyse_text(text):
        """
        Prefer this lexer over classic RexxLexer specifically when OO
        markers are present: a ``::`` directive is unambiguous (classic
        Rexx never uses one), a ``~`` message send is a strong signal,
        and ``.name~`` (an environment-directory symbol immediately sent
        a message) is a corroborating one. A plain classic-Rexx-looking
        file with none of these should score 0 here and fall through to
        RexxLexer.
        """
        if re.search(r"/\*\**\s*(oorexx|object rexx)", text, re.IGNORECASE):
            return 1.0

        result = 0.0
        if re.search(
            r"^\s*::\s*(class|method|routine|requires|attribute|constant|"
            r"options|resource|package)\b",
            text,
            re.IGNORECASE | re.MULTILINE,
        ):
            result += 0.9
        # The character class here matches _SYMBOL_START in the lexer
        # body above (message names and dot-lookups aren't limited to
        # plain word characters -- see that constant's own comment) so
        # a message send like "~?" isn't missed as an OO marker.
        if re.search(r"~~?[a-z_@#$!?]", text, re.IGNORECASE):
            result += 0.1
        if re.search(r"\.[a-z_@#$!?][\w@#$!?]*~", text, re.IGNORECASE):
            result += 0.05
        return min(result, 1.0)
