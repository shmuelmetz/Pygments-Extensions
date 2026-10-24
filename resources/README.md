# resources

The dialect registry: which language or dialect each lexer covers, and
the reference manuals it was written from.

- `dialects/<name>.json` -- one file per dialect, implemented or planned.
- `bib/*.bib` -- BibTeX entries for the manuals, keyed by `doc_keys`.

## dialects/*.json

| Key | Meaning |
|-----|---------|
| `dialect` | Display name of the language or dialect |
| `version` | Version line the lexer targets (`5.x` = any 5 release) |
| `product` | Product name as the vendor gives it |
| `doc_keys` | BibTeX keys in `bib/*.bib` for the manuals used |
| `lexer` | Lexer class name |
| `status` | `implemented` (the lexer exists) or `planned` |
| `entry_point` | For an implemented lexer: its name in `pyproject.toml`'s `pygments.lexers` entry points |

## bib/*.bib

`@manual` entries. IBM manuals carry the form number with its edition
suffix (`SA32-0972-70`) and the date the manual itself gives; title,
form, edition, date and copyright years were read from the manuals'
title pages, not from catalog listings. Manuals not kept locally (the
Enterprise PL/I 6.2 and REXX/VM 7.4 books) are cited from IBM's online
documentation.

`tests/test_resources.py` checks that every file parses, every
`doc_keys` entry exists in a `.bib` file, and every implemented
dialect's entry point resolves to the class named in `lexer`.
