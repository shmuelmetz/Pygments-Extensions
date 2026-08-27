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
* Dot-prefixed class references (``.array``, ``.string``, ``.true``,
  ``.MyClass``), tokenized as a single ``Name.Class`` token rather than
  falling through to a bare Operator("." ) + Text(name) split.
* The additional OO keywords these features bring along: ``guard``,
  ``expose``, ``forward``, ``use``, ``self``, ``super``.

Known open design question, not yet resolved: classic Rexx and ooRexx
source both commonly use the ``.rex`` extension, so filename-based lexer
guessing can't disambiguate them. ``analyse_text`` below is weighted to
prefer this lexer specifically when OO markers (a ``::`` directive, or a
``~`` message send) are present in the body, mirroring the weighted-
pattern approach ``RexxLexer.analyse_text`` already uses upstream to
disambiguate Rexx from other C-comment-using languages. This has only
been checked against the hand-written samples in samples/oorexx/ and
tests/test_oorexx.py so far -- it should be re-validated against real-
world ooRexx source before this lexer is proposed upstream.
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

__all__ = ["OORexxLexer"]


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
            (r"\s+", Whitespace),
            (r"/\*", Comment.Multiline, "comment"),
            (r'"', String, "string_double"),
            (r"'", String, "string_single"),
            (r"[0-9]+(\.[0-9]+)?(e[+-]?[0-9])?", Number),
            # ooRexx directives: ::CLASS, ::METHOD, ::ROUTINE, etc.
            # Must come before the generic operator rule below, since
            # plain Rexx has no other use of a doubled colon.
            (
                r"(::)(\s*)"
                r"(class|method|routine|requires|attribute|constant|"
                r"options|resource|package)\b",
                bygroups(Keyword.Namespace, Whitespace, Keyword.Declaration),
            ),
            # Dot-prefixed class/object references: .array, .string,
            # .true, .false, .nil, .MyClass, etc. Placed before the
            # generic operator rule so the leading "." doesn't get
            # split off on its own as a bare Operator token.
            (r"\.[a-z_]\w*", Name.Class),
            # Message-send operators. ~~ (cascading send) must be
            # listed before ~ since RegexLexer tries rules in order and
            # takes the first match, not the longest.
            (
                r"(~~|~)(\s*)([a-z_]\w*)",
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
                r"([a-z_]\w*)([ \t]*)(:)([ \t]*)(procedure)\b",
                bygroups(
                    Name.Function,
                    Whitespace,
                    Operator,
                    Whitespace,
                    Keyword.Declaration,
                ),
            ),
            (r"([a-z_]\w*)([ \t]*)(:)", bygroups(Name.Label, Whitespace, Operator)),
            include("function"),
            include("keyword"),
            include("operator"),
            (r"[a-z_]\w*", Text),
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
                r"trace|until|use|when|while)\b",
                Keyword.Reserved,
            ),
        ],
        "operator": [
            (
                r"(-|//|/|\(|\)|\*\*|\*|\\<<|\\<|\\==|\\=|\\>>|\\>|\\|\|\||"
                r"\||&&|&|%|\+|<<=|<<|<=|<>|<|==|=|><|>=|>>=|>>|>|\.|,)",
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
    }

    def analyse_text(text):
        """
        Prefer this lexer over classic RexxLexer specifically when OO
        markers are present: a ``::`` directive is unambiguous (classic
        Rexx never uses one), a ``~`` message send is a strong signal,
        and ``.name~`` (a class reference immediately sent a message) is
        a corroborating one. A plain classic-Rexx-looking file with none
        of these should score 0 here and fall through to RexxLexer.
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
        if re.search(r"~~?[a-z_]", text, re.IGNORECASE):
            result += 0.1
        if re.search(r"\.[a-z_]\w*~", text, re.IGNORECASE):
            result += 0.05
        return min(result, 1.0)
