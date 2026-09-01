# PL/I real-world validation corpus

Real-world PL/I source, gathered to validate `PLILexer` (tokenization
correctness, keyword/attribute/BIF coverage) against source this
project didn't write itself. See `pygments_extensions/lexers/pli.py`'s
module docstring for what this testing found and fixed.

Every file here has a short provenance header (source URL, project,
license) prepended as its own comment block.

## What's committed here, and why

### `from-zowe-pli-language-support/` (73 files)

Pulled from [zowe/zowe-pli-language-support](
https://github.com/zowe/zowe-pli-language-support), an IBM/Zowe
open-source PL/I language-server ("LSP") tooling project -- its own
`code_samples/` directory, a real corpus the project itself maintains
specifically to test its PL/I parser/tokenizer against realistic
input. Per that directory's own `README.md`, each sample is expected
to document the PL/I compiler version it targets; the ones checked
during this pass cite IBM PL/I for z/OS V6.1, built with the IBA
Group's Enterprise PL/I compiler. This is by far the largest and most
authoritative part of this corpus: genuine legacy mainframe programs
(fixed-format sequence-numbered source, DB2/CICS-embedded code,
preprocessor macro-facility examples, and hand-picked "quickfix"
DCL-ambiguity edge cases the project's own tooling had to handle),
spanning decades of vintage and (implicitly) more than one original
author. Licensed under the Eclipse Public License 2.0 (EPL-2.0), which
permits this redistribution.

### `from-nkimotou-pli/` (6 files)

Pulled from [nkimotou/PLI](https://github.com/nkimotou/PLI), an
individual GitHub author's small collection of PL/I examples (string
manipulation, sorting, date/time, file procedures). MIT-licensed
(confirmed via the source repository's own `LICENSE` file, Copyright
(c) 2024 Nanami Kimoto), which permits this redistribution. Included
for author diversity beyond the single large corpus above -- a
different, much more modern (2024) PL/I writing style than the
mainframe-vintage code in `from-zowe-pli-language-support/`.

One file here, `General__SORT_ARRAY.pli`, uses the Unicode "not equal
to" sign U+2260 (`≠`) in place of any of PL/I's documented not-equal
spellings (`¬=`, `^=`, `<>`) -- not confirmed anywhere in IBM's
documentation as valid PL/I syntax, so it's kept as a sample but is
explicitly excused from the "lexes with zero Error tokens" test
assertion in `tests/test_pli.py` (see that file's
`test_sample_file_lexes_without_error` for the specific carve-out and
reasoning).

### `from-prino-neocities/` (1 file, ~21,700 lines)

`lift.pli`, Robert AH Prins' hitchhiking-statistics extraction program,
sent in as real-world test data in response to this project's own
IBM-MAIN outreach post. Served as syntax-highlighted HTML by the
source site (via the author's own REXX-based PL/I-to-HTML converter)
rather than plain text; the HTML wrapper and highlighting spans were
stripped mechanically, verified to leave no residual markup or
entities, before saving here. GPLv3-or-later, per the license notice
embedded in the file's own header (confirmed, not assumed, against
the actual license text). A genuinely large, heavily
preprocessor-macro-using legacy program (`%dcl`, a `%filler`
procedure, a `%$$`-named preprocessor procedure) with no embedded
EXEC SQL/CICS -- lexes cleanly, zero Error tokens across ~200,000
tokens.

## What was used for testing but is NOT committed here

* **[benni-wdev/pliExamples](https://github.com/benni-wdev/pliExamples)**
  (4 files: `AG7000.pli`, `AG7010.pli`, `AG7020.pli`,
  `bucketsort.pli`) -- real PL/I source from an individual GitHub
  author ("Some PLI Code created long back, maybe useful for
  somebody"), but the repository carries no license file or notice at
  all, so no redistribution terms are established. Used only for local
  testing during this pass; lexed cleanly (zero Error tokens) after
  this pass's fixes.
* **Rosetta Code** (4 real snippets successfully fetched, from its
  [PL/I category](https://rosettacode.org/wiki/Category:PL/I): *100
  doors*, *Fibonacci sequence*, *Towers of Hanoi*, *Factorial*) -- like
  the ooRexx side of this corpus, Rosetta Code content is GFDL 1.2
  licensed, which isn't a straightforward fit for bare-snippet
  redistribution here. Used only for local testing; lexed cleanly.

## Reproducing this corpus

```
# from-zowe-pli-language-support/: raw.githubusercontent.com/zowe/zowe-pli-language-support/development/<path>
# from-nkimotou-pli/: raw.githubusercontent.com/nkimotou/PLI/main/<path>
# from-prino-neocities/: prino.neocities.org/resources/<path> (served as
#   syntax-highlighted HTML -- strip the <body>...</body> tags and any
#   remaining markup/entities to recover plain source)
```

The original relative path within its source repository is recorded
in each file's own provenance header comment.
