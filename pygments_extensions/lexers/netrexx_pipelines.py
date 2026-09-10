"""
NetRexx Pipelines lexer.

Pipelines (John P. Hartmann's CMS Pipelines, ported to run under NetRexx)
is a genuinely separate language from NetRexx itself, not a NetRexx
dialect or library API: a pipe specification is a single character
string -- a sequence of *stages* connected by a *stage separator*
(``|`` by default) -- compiled by its own pipeline compiler into
NetRexx/Java source, then into a runnable class. This is the same
relationship HTML has to CSS: two coexisting, separately-parsed
languages, not one lexer's job to cover (see the rexxla-members list
thread this lexer was written in response to, where J. Leslie Turriff
made exactly that comparison). ``.njp`` files hold pipe specifications
in this syntax; ``.nrx`` files holding the NetRexx stage
*implementations* (``pipe.nrx`` and the ``njpipes.stages.*`` classes)
are ordinary NetRexx and already covered by ``NetRexxLexer`` -- this
lexer is for the ``.njp`` specification language only.

Written against the project's own primary sources, not inferred from
samples alone: ``NetRexx 5.10 Pipelines Guide and Reference`` (the
prose guide) and ``stages.db``, the maintainer's (Jeff Hennick's) own
SQLite database of every stage name and alias, cross-checked against
232 real ``.njp``/``.nrx`` files from the project's own
``examples/pipes/`` and ``src/org/netrexx/njpipes/`` trees (a superset
of the 10 curated in this repo's own
``samples/netrexx/real-world/from-netrexx-project/``).

Confirmed from the Guide:

* A pipe specification is introduced by ``pipe`` (or, for a pipe
  attached to a running one, ``addpipe``), optionally followed by a
  parenthesized name/option list -- ``pipe (hello) literal ... | console``
  -- and consists of two or more stages connected by the stage
  separator, ``|`` unless overridden by an option.
* Two comment forms, both shared with NetRexx itself: ``/* ... */``
  and ``--`` to end of line -- except ``--`` is *also* a real stage
  name (a no-op comment stage, distinct from the line-comment reading)
  when it appears where a stage is expected rather than where a
  comment is; this lexer does not attempt to disambiguate the two
  positions and always treats a bare ``--`` as a comment, the more
  common reading and the one that costs nothing when wrong (a
  same-line comment stage still highlights sensibly as a comment).
* Stage names are looked up by minimum unambiguous abbreviation
  (confirmed by ``stages.db``'s own ``xalias`` table, which records
  chains like ``getf``/``getfi``/``getfil``/``getfile`` all resolving
  to ``getfiles``) -- so this lexer treats any bare identifier in
  stage position as a potential stage name (``Name.Builtin`` if it
  matches a real stage or a documented alias from ``stages.db``,
  plain ``Name`` otherwise) rather than trying to model abbreviation
  resolution itself.
* Labels (``o:``, ``c1:``) mark a branch/fan-in point that a later
  ``?`` in the specification connects back to -- both confirmed
  against real usage in ``all_tests1.njp`` and ``aggrc_tests1.njp``
  from the project's own test suite, not just the prose guide.
* Many stage options take a delimiter-quoted literal where the
  delimiter is the option's own first character, not a fixed quote
  mark -- ``/a/``, ``~...~`` in ``compare``/``locate``-family stages,
  the same free-delimiter convention classic Rexx's ``PARSE`` and
  CMS Pipelines itself use. Modeled here as a generic
  delimiter-matched String token rather than special-casing ``/`` or
  ``~`` specifically, since the guide does not fix the delimiter set.
* Column/record ranges (``2-*``, ``1-*``) use ``*`` as "to end" --
  confirmed in ``spec``/``specs`` usage throughout the sample corpus.

The ``compare``-stage substitution escapes inside delimited literals
are modeled: per the Pipelines Guide and Reference p.50 (confirmed by
Jeff Hennick on the rexxla-members thread), a DString may carry
``\\C`` (record number), ``\\B`` (column number), ``\\P`` (primary
stream record), ``\\S`` (secondary stream record), ``\\L`` (shorter
stream number, -1 if equal) and ``\\M`` (longer stream number), or
their lowercase forms. DStrings carry them in DString-escaped form --
a doubled backslash -- which is how they appear in ``all_tests1.njp``.
This lexer does not track which stage precedes a literal, so it
highlights the family as ``String.Escape`` in *any* DString, not only
``compare``'s; a stray ``\\c`` in some other stage's argument is a
possible but cosmetic over-highlight.

Not modeled: the DString's own escapes (``\\n`` for newline etc. --
also in ``all_tests1.njp`` but the DString escape set is not in the
portion of the Guide read so far) and the full stage-option grammar
per stage (each stage has its own argument shape; this lexer tokenizes
stage names and pipeline structure, not each stage's internal option
syntax).

First-draft status. Smoke-tested clean (0 Error tokens) across all 232
``.njp`` files under the reference implementation's
``documentation/njpipes/``, ``examples/pipes/`` and ``test/`` trees,
but not given the deeper per-feature validation pass ``NetRexxLexer``
had, and not yet reviewed by anyone from the Pipelines project. Seven
representative files are kept as a regression corpus in
``samples/netrexx-pipelines/real-world/from-netrexx-project/``.
"""

import re

from pygments.lexer import RegexLexer, words
from pygments.token import (
    Comment,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
    Whitespace,
)

# Real NetRexx-Pipelines stage names and their documented abbreviations,
# from stages.db (stages.nr=1, i.e. stages implemented for NetRexx
# Pipelines specifically, not CMS-only entries) and its xalias table --
# the maintainer's own reference, not a hand-typed guess. "--" and the
# device-driver symbols (<, >, >>) are stage names too but are handled
# by the comment/operator rules below instead, to avoid a token that
# means two different things depending on position.
_STAGE_NAMES = (
    "64decode 64encode abbreviation aggrc append array between buffer "
    "casei change changeparse changeregex chop cmd collate combine "
    "command comment compare console copy count dam dateconvert deal "
    "deblock decode64 dict disk diska diskr diskw display drop "
    "duplicate elastic encode64 fanin faninany fanout fblock file "
    "filea filer filew find frlabel fromlabel frtarget gate getfiles "
    "getovers getstems grep hash hole hostbyaddr hostbyname hostid "
    "hostname htmlrows insert inside join joincont juxtapose listzip "
    "literal locate lookup nfind ninside nlocate noEofBack nop not "
    "notfind notinside notlocate outside overlay pad parse pick "
    "pickparse prefix query random regex reverse serialize snake sort "
    "space spec split sql sqlselect stem strfind strfrlabel "
    "strfromlabel strip strliteral strnfind strtolabel strwhilelable "
    "tag tags take tcpclient tcpdata tcplisten terminal timestamp "
    "tokenise tolabel totarget translate truncate unique var varover "
    "vector vectora vectorr vectorw verify whilelabel xlate xrange "
    "zone"
).split()

_STAGE_ALIASES = (
    "abbrev abbrevi abbrevia abbreviat abbreviati abbreviatio "
    "changepars changepar changep changer changere changereg changerege "
    "cmd cons conso consol dup dupl dupli duplic duplica duplicat file "
    "filea fileback filefast filer filerandom fileslow fileupdate "
    "filew fromlabel get getf getfi getfil getfile grep hash hasha "
    "hashr hashw notfind notinside notlocate over overl overla specs "
    "strfrlab strfrlabe strfromlabel strtolab strtolabe strwhile "
    "strwhilel strwhilela strwhilelab strwhilelabe synchronize term "
    "termi termin termina terminal tokenize tolab tolabe trans transl "
    "transla translat translate trunc truncat truncate uniq uniqu"
).split()

_STAGE_WORDS = sorted(set(_STAGE_NAMES) | set(_STAGE_ALIASES), key=len, reverse=True)

# compare-stage substitution escapes (Pipelines Guide & Reference p.50):
# \C \B \P \S \L \M and lowercase. In a DString they are carried
# DString-escaped -- a doubled backslash -- so match that form first,
# then the bare form defensively.
_DSTRING_ESC = re.compile(r"\\\\[CBPSLMcbpslm]|\\[CBPSLMcbpslm]")


def _dstring(lexer, match):
    """Sub-tokenize a delimiter-quoted literal, breaking out the
    compare-stage substitution escapes. The whole literal is matched
    by one regex (with the closing-delimiter backreference, so an
    unclosed delimiter never reaches here); this callback just splits
    the already-bounded text."""
    text = match.group()
    start = match.start()
    delim = text[0]
    yield start, String, delim
    body = text[1:-1]
    last = 0
    for m in _DSTRING_ESC.finditer(body):
        if m.start() > last:
            yield start + 1 + last, String, body[last : m.start()]
        yield start + 1 + m.start(), String.Escape, m.group()
        last = m.end()
    if last < len(body):
        yield start + 1 + last, String, body[last:]
    yield match.end() - 1, String, delim


class NetRexxPipelinesLexer(RegexLexer):
    """
    Lexer for NetRexx Pipelines specifications (``.njp`` files) --
    the pipe-specification language, not the NetRexx stage
    implementations (use ``NetRexxLexer`` for those ``.nrx`` files).
    """

    name = "NetRexx Pipelines"
    aliases = ["netrexx-pipelines", "njp"]
    filenames = ["*.njp"]
    mimetypes = []
    url = "https://www.netrexx.org/"

    tokens = {
        "root": [
            (r"[ \t]+", Whitespace),
            (r"\r?\n", Text),
            (r"/\*", Comment.Multiline, "comment"),
            (r"--.*$", Comment.Single),
            (r"\b(pipe|addpipe)\b", Name.Builtin.Pseudo),
            # A label: an identifier immediately followed by ':' that is
            # not itself a numeric range colon -- used for fanin/fanout
            # branch points (o:, c1:) that a later '?' connects back to.
            (r"[A-Za-z_$][A-Za-z0-9_$]*(?=:)", Name.Label),
            (r":", Punctuation),
            (r"\?", Name.Label),
            (r"\|", Operator),
            (r"\(", Punctuation, "options"),
            (words(tuple(_STAGE_WORDS), prefix=r"\b", suffix=r"\b"), Name.Builtin),
            # Record/column ranges: 2-*, 1-*, plain numbers.
            (r"\*", Number),
            (r"\d+", Number.Integer),
            (r"-", Operator),
            # A delimiter-quoted literal: the option's first character
            # is reused as its own closing delimiter (the same
            # free-delimiter convention as classic Rexx PARSE), e.g.
            # /a/, ~text~. Any non-alphanumeric, non-whitespace
            # character except the structural ones (| ( ) and the range
            # chars * -) can be the delimiter; this matches the first
            # such character seen in stage-option position and reads up
            # to its next occurrence. A ``/`` delimiter is safe here
            # because the ``/*`` comment rule above already ran, so a
            # ``/`` reaching this point cannot start a comment; an
            # unclosed delimiter simply doesn't match (needs the closing
            # ``\1``) and falls through to Text.
            (r"([^\sA-Za-z0-9|()*-])(?:(?!\1).)*\1", _dstring),
            (r"[A-Za-z_$][A-Za-z0-9_$]*", Name),
            (r".", Text),
        ],
        "comment": [
            (r"[^*/]+", Comment.Multiline),
            (r"/\*", Comment.Multiline, "#push"),
            (r"\*/", Comment.Multiline, "#pop"),
            (r"[*/]", Comment.Multiline),
        ],
        "options": [
            (r"\)", Punctuation, "#pop"),
            (r"[ \t]+", Whitespace),
            (r"[A-Za-z_$][A-Za-z0-9_$]*", Name.Attribute),
            (r"\d+", Number.Integer),
            (r".", Text),
        ],
    }
