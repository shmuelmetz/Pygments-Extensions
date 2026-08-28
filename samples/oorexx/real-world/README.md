# ooRexx real-world validation corpus

Real-world ooRexx and classic-Rexx source, gathered to validate
`OORexxLexer` (tokenization correctness and the `analyse_text`
disambiguation heuristic) against source this project didn't write
itself. See `pygments_extensions/lexers/oorexx.py`'s module docstring
for what this testing found and fixed.

Every file here has a short provenance header (source URL, project,
license) prepended as its own comment block.

## What's committed here, and why

### `from-oorexx-project/` (30 files)

Pulled directly from the official [ooRexx/ooRexx](
https://github.com/ooRexx/ooRexx) interpreter repository on GitHub
(the `master` branch mirror of the project's own SourceForge SVN),
specifically its `samples/`, `extensions/`, and
`interpreter/RexxClasses/` directories -- real OO-heavy sample
programs and class libraries written and maintained by the ooRexx
project itself, not by this project. Licensed under the Common Public
License v1.0 (CPL-1.0), which permits this redistribution; each file's
own CPL/copyright header (already present in the original source) is
preserved below this project's added provenance header.

### `from-rexxla-classic-rexx/` (7 files)

Pulled from [RexxLA/rexx-repository](
https://github.com/RexxLA/rexx-repository) (a community source/library
archive maintained by the Rexx Language Association), specifically the
seven `.rex`/`.REX`-extensioned files under its `Classic_Rexx/` tree
(the CRX interpreter's own historical test suite, and a 1982-vintage
demo program translated from BASIC). These are **classic Rexx, not
ooRexx** -- kept deliberately as *negative* test cases for
`analyse_text()`: since both dialects commonly share the `.rex`
extension, the heuristic must score exactly `0.0` on every one of
these (no `::` directive, no `~` message send anywhere), correctly
leaving classic `RexxLexer` as the lexer Pygments actually picks. One
of them, `MSGS.REX`, is itself the CRX interpreter's own test fixture
of *deliberately invalid* Rexx fragments used to exercise its error
handling -- it is not expected to tokenize cleanly even under classic
`RexxLexer`, and isn't required to here either (see
`tests/test_oorexx.py`'s `test_real_world_classic_rexx_scores_zero`,
which checks only the disambiguation score, not clean tokenization,
for this directory). Per the repository's own README: "all materials
are donated under various open source licenses, or are in the public
domain" -- no more specific per-file license notice was found in any
of these seven files.

## What was used for testing but is NOT committed here

**Rosetta Code** (10 community-contributed snippets, from pages like
*Abstract type*, *Active object*, *Polymorphism*, *Singleton*, etc. in
its [ooRexx category](https://rosettacode.org/wiki/Category:OoRexx)):
real, genuine ooRexx source from a different author pool than either
directory above, and it lexed with zero Error tokens after this
validation pass's fixes -- but Rosetta Code content is licensed under
the GNU Free Documentation License (GFDL) 1.2, which isn't a
straightforward fit for redistributing bare snippets inside an
MIT-licensed project (it has its own attribution/license-text-carrying
requirements). Rather than get that wrong, these were used only for
local testing during this pass and are not included here. If someone
wants to reproduce that part of the testing, the ten task pages used
were: Abstract type, Active object, Add a variable to a class instance
at runtime, Constrained genericity, Inheritance/Multiple, Polymorphism,
Polymorphic copy, Respond to an unknown method call, and Singleton
(fetched via each page's `?action=raw` raw-wikitext URL).

## Reproducing this corpus

```
# from-oorexx-project/: raw.githubusercontent.com/ooRexx/ooRexx/master/<path>
# from-rexxla-classic-rexx/: raw.githubusercontent.com/RexxLA/rexx-repository/master/<path>
```

The original relative path within its source repository is recorded
in each file's own provenance header comment.
