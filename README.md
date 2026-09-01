# pygments-extensions

Custom lexers extending Pygments ([pygments.org](https://pygments.org/)), the Python syntax highlighting library.

## Purpose

Several languages relevant to the author's work are absent from the Pygments distribution or have incomplete support. This project provides additional lexers for use in local tools, MediaWiki `<syntaxhighlight>` tags, and wherever Pygments is used as a highlighting engine.

## Languages

### Current focus

## PL/I

Pygments itself has never shipped a PL/I lexer — confirmed directly against its lexer registry, its full CHANGES history, and a commit-message search of its entire history, all turning up nothing. As far as Pygments is concerned, this is a from-scratch build, not a restoration.

That said, PL/I syntax highlighting **did** once work on Wikipedia — just not through Pygments. MediaWiki's `SyntaxHighlight` extension is still literally named `SyntaxHighlight_GeSHi` internally, a fossil from its actual history: it ran on [GeSHi](https://github.com/GeSHi/geshi-1.0) (a PHP syntax highlighter) before switching to a Pygments backend, and GeSHi's own language files include a real `pli.php` (confirmed directly in its repo). Checked further than the name fossil alone: in the extension's pre-Pygments source (GitHub mirror, branch `REL1_19`, ~2012-era MediaWiki, confirmed genuinely GeSHi-backed by its own README referencing "GeSHi 1.0.8.10"), `SyntaxHighlight_GeSHi.class.php` auto-discovered every supported language straight from GeSHi's own bundled files with no separate whitelist:

```php
foreach( glob( GESHI_LANG_ROOT . "/*.php" ) as $file ) {
    self::$languages[] = basename( $file, '.php' );
}
```

No curation step existed to have left `pli.php` out — whatever GeSHi shipped, Wikipedia exposed automatically via `<syntaxhighlight lang="pli">`. So PL/I highlighting on Wikipedia was a real, working feature once, lost specifically in the GeSHi-to-Pygments switch — this project is restoring a capability Wikipedia used to have, even though it's new to Pygments itself. Worth using in outreach messaging: "restoring what Wikipedia lost" is a stronger hook than "brand new, nobody asked."

## ooRexx

Open Object Rexx lexer for syntax highlighting of ooRexx source. Built as a fork/extension of Pygments' existing classic-Rexx lexer (`pygments.lexers.scripting.RexxLexer`), which covers a useful subset of shared syntax already.

### Future direction

Other lexers have been discussed for this project — including ISPF panels/messages/skeletons/DTL and other mainframe-adjacent languages (HLASM, NetRexx, Regina Rexx) — and some scaffolding for them (entry points, an earlier draft README) already exists in this repo. They are not being worked on yet; PL/I and ooRexx are the current priority. This section will grow as that work starts.

## Pre-submission checklist against Pygments' own requirements

Checked directly against Pygments' lexer-development docs (2026-08-28), not assumed. Both lexers already meet the hard structural requirements: `name`, `aliases`, and `filenames` are all correctly defined on both `OORexxLexer` and `PLILexer` (`mimetypes = []` on both is normal, not a gap — plenty of accepted lexers have no registered MIME type). One real gap, not yet closed:

- **Test format**: Pygments requires new-lexer tests in its own golden-file format — `tests/snippets/<lexer_alias>/*.txt`, generated/verified via `tox -- --update-goldens`, or `tests/examplefiles/` for larger files — and states plainly: "Lexers which can't be tested will not be accepted." This project's existing tests (`tests/test_oorexx.py`, `tests/test_pli.py`, 72 passing) are solid pytest-style coverage for this repo's own purposes but aren't in Pygments' required format on their own; conversion is under way via `scripts/generate_snippet_goldens.py` (replicates Pygments' own golden-file token-formatting algorithm exactly, verified against `pygments/pygments@master`). Currently 17 ooRexx and 14 PL/I golden-file snippets exist in `tests/snippets/`, covering most feature clusters each pytest suite tests directly (real-world sample validation, EXEC SQL/CICS handling, the 5.0 keyword-form port, and the NOT-operator/preprocessor/compound-operator families are all represented); a handful of narrower pytest cases (mostly `analyse_text` dialect-detection tests, which aren't lexer-output snippets at all) still have no golden-file counterpart. Not yet run through Pygments' own `tox -- --update-goldens`/pytest harness itself, since these lexers aren't inside an actual pygments/pygments checkout yet — that's the remaining verification step once submission is imminent.

## Wikipedia deployment

Getting a new lexer into Wikipedia's `<syntaxhighlight>` tag requires working through several independent projects on different schedules:

- Submit the lexer to upstream Pygments and get it merged
- Wait for Pygments to cut a release containing the new lexer
- Wait for Wikimedia to pick up the new Pygments release in its SyntaxHighlight extension
- File a Phabricator task on [phabricator.wikimedia.org](https://phabricator.wikimedia.org/) asking Wikimedia to enable the new language tags
- Wait for Wikimedia to deploy the tag enablement

This project serves as a working home for the lexers during that process and as a standalone tool for local use in the meantime.

## Community awareness

Getting a lexer merged and deployed is a technical pipeline; getting it *used* also depends on the people who actually write PL/I and ooRexx knowing it exists. This is an explicit step, not an afterthought of "write code and submit upstream":

- **ooRexx**: [RexxLA](https://www.rexxla.org/) (the Rexx Language Association) is the right organization — ooRexx is itself a RexxLA project. Two confirmed contact channels, both worth reaching rather than picking just one: `oorexx-users@lists.sourceforge.net` and `main@rexxla-members.groups.io`. Useful both before and after a working lexer exists: real-world source samples for the test suite are worth asking for early; an announcement and request for review/testing once there's something concrete to show.
- **PL/I**: **IBM-MAIN** is the primary venue for reaching practicing Enterprise PL/I developers — widest reach among people actually maintaining z/OS PL/I portfolios, per the author's own assessment (2026-08-28), not independently re-verified against traffic/membership data by this project. The IBM Community PL/I group and `comp.lang.pl1` are secondary venues: lower traffic, but comp.lang.pl1 in particular skews toward long-time language experts and historical/dialect knowledge IBM-MAIN may not surface. This project's own PL/I lexer has no legacy Pygments code to point to, so real-world sample source matters even more here than for ooRexx — frame outreach as "help find what's mis-highlighted," not "look at my project," since that concretely invites people to send breaking examples rather than just comment. Explicitly ask for Enterprise-PL/I-specific constructs current coverage doesn't touch yet: preprocessor directives (`%IF`/`%DO`/`%INCLUDE`/`%PROCESS`), embedded `EXEC SQL`/`EXEC CICS`/IMS blocks, and fixed-vs-free source format — these are exactly where a lexer that's only ever seen synthetic samples tends to break on real mainframe code. When this outreach happens, also explicitly solicit volunteers who might have personal or institutional access to the formal PL/I language standards — more authoritative than IBM's vendor docs, which is what the lexer's DCL-attribute/keyword/BIF vocabulary is currently sourced from, but not readily accessible online: ANSI X3.53-1976 (or its ISO counterpart, ISO 6160:1979), and both ANSI Subset G editions — X3.74-1981 and the later, distinct X3.74-1987 — plus their ISO counterparts ISO 6522:1985 and ISO/IEC 6522:1992. A personal copy, university library access, or an IBM/ANSI archive from someone in that community could let the vocabulary be cross-checked against the actual standards rather than just IBM's current implementation. This is a concrete ask, not just "let us know if you're interested."
- **Pygments**: no dedicated mailing list or IRC — Pygments is entirely GitHub-native (confirmed directly, not assumed). The outreach venue is settled: [GitHub Discussions](https://github.com/pygments/pygments/discussions), confirmed enabled on the repo, is where to float "I'm working on PL/I and ooRexx lexers, here's my plan" before a cold PR. Actual submission goes through the normal Issues/PR review process — new-language PRs aren't a separate ask-permission-first step — and the named maintainers (Georg Brandl, Matthäus Chajdas, Jean Abou-Samra) are reachable via that same PR/issue flow, not a separate email list. Not posting anything yet; this locks in the plan for when the lexers are further along.
- **Wikimedia**: already implied by the deployment pipeline above, but worth doing deliberately rather than just filing the Phabricator task silently.

What "aware" means in practice will firm up once each lexer is far enough along to actually show — this section will get more specific then.

## Platform

The lexers target upstream Pygments and, through the Wikimedia deployment pipeline, Wikipedia's syntaxhighlight extension. The Rexx and ooRexx lexers also target submission to RexxLA. Other lexers may have different targets.

## Collaboration

Contributions and corrections are welcome. If you maintain lexers for languages not yet covered here, please open an issue or pull request, or incorporate whatever is useful into your own work. See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, lexer/file naming conventions, and test requirements.

## Author

Shmuel (Seymour J. Metz) (שְׁמוּאֵל בֵּן לייביש ולאה)
[smetz3@gmu.edu](mailto:smetz3@gmu.edu)
[mason.gmu.edu/~smetz3](https://mason.gmu.edu/~smetz3)
GitHub: [shmuelmetz](https://github.com/shmuelmetz)

## License

[MIT](LICENSE)
