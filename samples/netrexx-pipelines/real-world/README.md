# NetRexx Pipelines real-world validation corpus

Real-world NetRexx Pipelines *specifications* (`.njp` files), gathered
to validate `NetRexxPipelinesLexer` (tokenization correctness) against
source this project didn't write itself. See
`pygments_extensions/lexers/netrexx_pipelines.py`'s module docstring
for the lexer's own scope and sourcing notes -- in short, this is a
separate language from NetRexx proper (the same relationship HTML has
to CSS), so it gets its own lexer rather than an extension to
`NetRexxLexer`.

Every file here has a short provenance header (source URL, project,
license) prepended as its own comment block; `all_tests1.njp`'s header
also notes it was transcoded from the original's ISO-8859-1 encoding
to UTF-8, for consistency with every other sample file in this repo.

## What's committed here, and why

Pulled from the same official NetRexx reference implementation as
`samples/netrexx/real-world/from-netrexx-project/`
([sourceforge.net/p/netrexx/code](https://sourceforge.net/p/netrexx/code/ci/master/tree/)),
specifically `documentation/njpipes/` (the two "hello world"-scale
examples from the Pipelines Guide itself) and `examples/pipes/` (the
project's own test suite for the Pipelines feature). Licensed under
the ICU License (ICU 1.8.1 and later), same as the rest of the
NetRexx reference implementation.

Seven files, chosen to cover the syntax actually exercised across the
232-file `.njp` corpus this lexer was smoke-tested against (0 Error
tokens across all 232, not just these seven):

* `documentation__njpipes__firstsample.njp`,
  `documentation__njpipes__secondsample.njp` -- the simplest possible
  pipe specifications (`pipe (hello) literal ... | console`), covering
  the baseline `pipe (name) stage | stage | stage` shape.
* `examples__pipes__all_tests1.njp`, `examples__pipes__aggrc_tests1.njp`,
  `examples__pipes__alter_tests02.njp` -- labels (`o:`, `c1:`) and the
  `?` fan-in/fan-out connector, delimiter-quoted literals with a
  variety of delimiter characters (`/a/`, `~...~`), and the escape
  sequences inside `compare`'s message-format strings
  (`\c`/`\b`/`\p`/`\s`) that the lexer's docstring flags as not yet
  specially modeled.
* `examples__pipes__addpipetest3.njp` -- `addpipe` (as opposed to a
  top-level `pipe`), and a file that mixes an `.njp` pipe specification
  with actual NetRexx class code in the same file (the Pipelines Guide
  notes this is supported, provided the two are kept textually
  separated) -- a real stress case for where this lexer's scope ends.
* `examples__pipes__abbrev_tests1.njp` -- a large `/* ... */` block
  comment containing a railroad-diagram-style syntax description with
  heavy use of `+`/`-`/`|` box-drawing characters, which must not be
  misread as pipeline operators while inside a comment.

## Status

First-draft lexer, written 2026-09-08 against the project's own
`NetRexx 5.10 Pipelines Guide and Reference` and the maintainer's
`stages.db` (the real stage-name/alias list), not inferred from
samples alone -- prompted by
[a rexxla-members thread](https://mail.rexxla.org) in which Jeff
Hennick asked whether Pipelines syntax could be covered and J. Leslie
Turriff noted it's better treated as its own language, the same way
HTML and CSS are. Smoke-tested clean (0 Error tokens) across all 232
`.njp` files under the reference implementation's
`documentation/njpipes/`, `examples/pipes/`, and `test/` trees. Not
yet reviewed by anyone from the Pipelines project itself, and the
per-stage option grammar (each of the ~136 stage names has its own
argument shape) is deliberately not modeled in this first pass --
only pipeline structure (stages, separators, labels, comments,
delimited literals) is tokenized in detail.
