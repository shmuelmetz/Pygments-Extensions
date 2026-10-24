"""
RXU (TUTOR) lexer.

RXU is the Rexx Preprocessor for Unicode in Josep Maria Blasco's Unicode
Tools Of Rexx (TUTOR, https://rexx.epbcn.com/TUTOR/): it reads ``.rxu``
files written in ooRexx extended for Unicode and translates them to
plain ``.rex`` for ooRexx 5.2 to run. Everything ooRexx has, RXU has, so
this lexer subclasses ``OORexxLexer`` and adds only what RXU adds. A
separate lexer, not a mode of ``OORexxLexer``: the extensions are not
ooRexx, and in plain ooRexx ``"abc"Y`` is the string ``"abc"`` abutted to
the variable ``Y`` -- one lexer cannot read it both ways.

Sources: the TUTOR documentation pages "New types of strings",
"New built-in functions" and "New values for the OPTIONS instruction"
(read 2026-10-24, TUTOR 0.7), and Blasco's answer to TUTOR issue #13
(https://github.com/JosepMariaBlasco/TUTOR/issues/13): the suffixes are
unchanged since 0.5 (March 2024), case-insensitive, and "stable enough to
build a lexer on".

What RXU adds, and how it is tokenized:

* Suffixed string literals. The suffix follows the closing quote:
  ``Y`` (BYTES), ``P`` (CODEPOINTS), ``G`` (GRAPHEMES), ``T`` (TEXT) and
  ``U`` (Unicode codepoints in hex, ``U+`` optional, or names, aliases
  and labels in parentheses: ``"E9"U``, ``"(Man)(Bell)"U``), beside
  ooRexx's ``X`` and ``B``, which ``OORexxLexer`` handles. The literal is
  one token for its body and a ``String.Affix`` token for the suffix --
  the token type Pygments defines for string prefixes and suffixes, and
  the one ``OORexxLexer`` uses for X and B. Bodies of ``Y``, ``P``,
  ``G`` and ``T`` strings are text, so they stay ``String``; bodies of
  ``U`` strings, like X and B ones, are codes, not text, so they are
  ``String.Other``. This mirrors the Rexx Parser's element categories
  (BYTES_STRING, CODEPOINTS_STRING, GRAPHEMES_STRING, TEXT_STRING,
  UNICODE_STRING), which separate the same kinds. A suffix letter
  followed by another symbol character is not a suffix (``"abc"Yes`` is
  ``"abc"`` abutted to ``Yes``), as in Rexx's own X and B rule.
* U strings are checked as RXU checks them: each item is a hex
  codepoint (``U+`` optional) no greater than 10FFFF and not a
  surrogate, or a parenthesized name, alias or label. A body TUTOR would
  reject (Syntax error 22) is an ``Error`` token. Names are checked
  against Python's ``unicodedata``; see ``_valid_name`` for its limits.
* Built-in functions: BYTES, CODEPOINTS, GRAPHEMES, TEXT, C2U, U2C, N2P,
  P2N, STRINGTYPE, UNICODE, UTF8, ENCODE and DECODE, highlighted like
  the ooRexx built-ins (a name followed by ``(``).
* The OPTIONS instruction's new values: ``DEFAULTSTRING`` with BYTES,
  CODEPOINTS, GRAPHEMES, TEXT or NONE, and ``COERCIONS`` with PROMOTE,
  DEMOTE, LEFT, RIGHT or NONE (the TUTOR page marks COERCIONS highly
  experimental).

Not covered: the TUTOR classes (``.Bytes``, ``.Codepoints``, ``.Text``)
need nothing new -- environment symbols are already
``Name.Variable.Global`` in ``OORexxLexer``.
"""

import re
import unicodedata

from pygments.lexer import bygroups, inherit, words
from pygments.token import Error, Keyword, Name, Operator, String, Whitespace

from pygments_extensions.lexers.oorexx import OORexxLexer

__all__ = ["RxuLexer"]

# A suffix must not run into a further symbol character, or it is the
# start of a symbol abutted to the string instead.
_END_OF_SUFFIX = r"(?![\w@#$!?.])"

_DOUBLE = r'"(?:[^"\n]|"")*"'
_SINGLE = r"'(?:[^'\n]|'')*'"

# A U string's items: a parenthesized name, or a codepoint word
_U_ITEM = re.compile(r"\s*(?:\(([^)]*)\)|([^\s(]+))")
# TUTOR's labels for unnamed codepoints, e.g. <control-000A> (Unicode
# section 4.8, "Code Point Labels")
_U_LABEL = re.compile(
    r"<(?:control|reserved|noncharacter|private-use|surrogate)-([0-9a-f]{4,6})>",
    re.IGNORECASE,
)

# Loose name key -> True, for every named codepoint; built on first need
_loose_names = None


def _loose(name):
    """A name's loose-matching key: casing, blanks, underscores and
    hyphens dropped. TUTOR ignores casing and spacing in names
    ("(LatincapitalletterA)"U); this approximates Unicode's loose
    matching rule UAX44-LM2, which also ignores medial hyphens."""
    return re.sub(r"[\s_-]", "", name).upper()


def _valid_codepoint(word):
    """A hex codepoint, optionally prefixed by U+, that TUTOR accepts:
    at most 10FFFF and not a surrogate (D800-DFFF)."""
    if word[:2].upper() == "U+":
        word = word[2:]
    if not re.fullmatch(r"[0-9a-f]+", word, re.IGNORECASE):
        return False
    value = int(word, 16)
    return value <= 0x10FFFF and not 0xD800 <= value <= 0xDFFF


def _valid_name(name):
    """A character name, alias or label that TUTOR accepts, as far as
    Python's own Unicode database (``unicodedata``) can tell: an exact
    name or alias first (unicodedata.lookup ignores casing), then a
    loose match against every character name, for names written without
    their blanks. Aliases are found only when written with their blanks
    -- unicodedata cannot list them -- and the database is Python's
    Unicode version, which may differ from TUTOR's."""
    global _loose_names
    label = _U_LABEL.fullmatch(name.strip())
    if label:
        return _valid_codepoint(label.group(1))
    try:
        unicodedata.lookup(name.strip())
        return True
    except KeyError:
        pass
    if _loose_names is None:
        _loose_names = {
            _loose(unicodedata.name(chr(cp)))
            for cp in range(0x110000)
            if unicodedata.name(chr(cp), None)
        }
    return _loose(name) in _loose_names


def _valid_u_body(body):
    """Whether the text between a U string's quotes is well formed:
    blank-separated hex codepoints and parenthesized names, in any mix."""
    at = 0
    while at < len(body):
        item = _U_ITEM.match(body, at)
        if item is None:  # only trailing blanks, or a stray ")"
            return body[at:].strip() == ""
        name, word = item.groups()
        if name is not None and not _valid_name(name):
            return False
        if word is not None and not _valid_codepoint(word):
            return False
        at = item.end()
    return True


def _u_string(lexer, match):
    """Tokens for a U string: the body, as String.Other when it is well
    formed and as Error when TUTOR would reject it (Syntax error 22),
    then the suffix."""
    literal = match.group(1)
    quote = literal[0]
    body = literal[1:-1].replace(quote * 2, quote)
    yield match.start(1), (String.Other if _valid_u_body(body) else Error), literal
    yield match.start(2), String.Affix, match.group(2)


class RxuLexer(OORexxLexer):
    """
    RXU is the Rexx Preprocessor for Unicode in TUTOR, the Unicode Tools
    Of Rexx: ooRexx extended with Unicode string types and built-in
    functions.
    """

    name = "RXU (TUTOR)"
    url = "https://rexx.epbcn.com/TUTOR/"
    aliases = ["rxu", "tutor"]
    filenames = ["*.rxu"]
    mimetypes = []
    version_added = "0.1"

    flags = re.IGNORECASE | re.MULTILINE

    tokens = {
        "root": [
            # Codes, not text: Unicode-codepoint strings (hex and binary
            # strings are OORexxLexer's, inherited below)
            (
                r"(" + _DOUBLE + r"|" + _SINGLE + r")(u)" + _END_OF_SUFFIX,
                _u_string,
            ),
            # Text of a given string type: bytes, codepoints, graphemes,
            # text
            (
                r"(" + _DOUBLE + r"|" + _SINGLE + r")([ypgt])" + _END_OF_SUFFIX,
                bygroups(String, String.Affix),
            ),
            (
                r"(options)(\s+)(defaultstring)(\s+)"
                r"(bytes|codepoints|graphemes|text|none)\b",
                bygroups(
                    Keyword.Reserved,
                    Whitespace,
                    Keyword.Type,
                    Whitespace,
                    Keyword.Constant,
                ),
            ),
            (
                r"(options)(\s+)(coercions)(\s+)"
                r"(promote|demote|left|right|none)\b",
                bygroups(
                    Keyword.Reserved,
                    Whitespace,
                    Keyword.Type,
                    Whitespace,
                    Keyword.Constant,
                ),
            ),
            inherit,
        ],
        "function": [
            (
                words(
                    (
                        "bytes", "c2u", "codepoints", "decode", "encode",
                        "graphemes", "n2p", "p2n", "stringtype", "text",
                        "u2c", "unicode", "utf8",
                    ),
                    suffix=r"(\s*)(\()",
                ),
                bygroups(Name.Builtin, Whitespace, Operator),
            ),
            inherit,
        ],
    }

    def analyse_text(text):
        """
        RXU files are known by their ``.rxu`` extension; from text alone,
        only constructs no plain ooRexx program has are counted: an
        ``OPTIONS DEFAULTSTRING`` or ``OPTIONS COERCIONS`` instruction,
        or a U string naming characters in parentheses (``"(Bell)"U``).
        A Y, P, G or T suffix alone proves nothing -- in ooRexx it is an
        abutted variable.
        """
        if re.search(
            r"^\s*options\s+(defaultstring|coercions)\b",
            text,
            re.IGNORECASE | re.MULTILINE,
        ):
            return 1.0
        if re.search(r"[\"']\([^\"'\n]*\)[\"']u(?![\w@#$!?.])", text, re.IGNORECASE):
            return 0.5
        return 0.0
