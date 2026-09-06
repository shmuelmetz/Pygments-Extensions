# NetRexx real-world validation corpus

Real-world NetRexx source, gathered to validate `NetRexxLexer`
(tokenization correctness) against source this project didn't write
itself. See `pygments_extensions/lexers/netrexx.py`'s module docstring
for what this testing found and fixed.

Every file here has a short provenance header (source URL, project,
license) prepended as its own comment block.

## What's committed here, and why

### `from-netrexx-project/` (32 files)

Pulled directly from the official NetRexx reference implementation
([sourceforge.net/p/netrexx/code](https://sourceforge.net/p/netrexx/code/ci/master/tree/),
mirrored at `git.code.sf.net/p/netrexx/code`) -- specifically its
`src/netrexx/lang/` (the compiler's own self-hosted runtime classes,
written in NetRexx), `examples/rosettacode/` (the project's own
solutions to Rosetta Code tasks -- original code written for this
repository, not scraped from the rosettacode.org wiki, so the wiki's
GFDL terms don't apply here), and a handful of files chosen
specifically because they exercise constructs the first validation
pass got wrong (see below). Licensed under the ICU License (ICU 1.8.1
and later), a permissive license that allows this redistribution;
each file's own copyright/license header, where the original had one,
is preserved below this project's added provenance header.

This is the full corpus that surfaced real defects during the
2026-09-06 validation pass -- 912 files scanned (911 after excluding
one false-positive extension collision, see below), 116 Error tokens
across 8 files before the fixes documented in `netrexx.py`, 0 after.
The 32 files kept here are a representative subset chosen to keep the
regression corpus a manageable size while still exercising every bug
class that pass found:

* `examples/rexxtry.nrx` and `examples/rexxtry-org.nrx` -- both open
  with a `#!/usr/bin/env nr` shebang line (NRL Sec 3.3.2).
* `examples/new-3.06/annotations/AnnotateTest.nrx` -- exercises
  `@Override`/`@Deprecated`/`@SuppressWarnings`/custom `@Author`
  annotations (NRL Sec 4.1).
* `src/org/netrexx/diag/DiagUTF8.nrx`, `test/testUTF8Default.nrx`,
  `examples/unicode/UnicodeDemo.nrx`, and
  `examples/unicode/UnicodeDémo.nrx` (non-ASCII even in the filename)
  -- exercise the NRL's "extra letters"/"extra digits" allowance for
  symbols and numeric literals (NRL Sec 3.3.3), including a numeric
  literal written entirely in Arabic-Indic digits (`num=١١`).
* The remaining files (10 from `src/netrexx/lang/`, 15 from
  `examples/rosettacode/`) lexed cleanly even before the fixes above;
  kept as general-purpose regression coverage across a wide range of
  ordinary language constructs (classes, exceptions, loops, arrays,
  string handling, recursion, sorting algorithms) from two very
  different code populations -- the compiler's own production runtime
  and small task-focused example programs.

**Excluded, not a lexer defect**: `tools/epm/EPMKWDS.NRX`, found
during the same scan, is not NetRexx source at all -- it's an IBM EPM
(OS/2-era Enhanced Editor) keywords-highlighting configuration file
that happens to share the `.NRX` extension by coincidence (its own
header: "Sample of keywords file for the keywords highlighting feature
of EPM"). Not committed here and not counted against the validation
pass.

## Reproducing this corpus

```
git clone --depth 1 https://git.code.sf.net/p/netrexx/code netrexx-upstream
```

The original relative path within the source repository is recorded
in each file's own provenance header comment, and also in this
project's git history (see the commit that added this directory).
