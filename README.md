# pygments-extensions

Custom lexers extending Pygments ([pygments.org](https://pygments.org/)), the Python syntax highlighting library.

## Purpose

Several languages relevant to the author's work are absent from the Pygments distribution or have incomplete support. This project provides additional lexers for use in local tools, MediaWiki `<syntaxhighlight>` tags, and wherever Pygments is used as a highlighting engine.

## Languages

### Current focus

## PL/I

Pygments has never shipped a PL/I lexer (confirmed against its lexer registry and commit history) — this is a from-scratch build, not a restoration.

## ooRexx

Open Object Rexx lexer for syntax highlighting of ooRexx source. Built as a fork/extension of Pygments' existing classic-Rexx lexer (`pygments.lexers.scripting.RexxLexer`), which covers a useful subset of shared syntax already.

### Future direction

Other lexers have been discussed for this project — including ISPF panels/messages/skeletons/DTL and other mainframe-adjacent languages (HLASM, NetRexx, Regina Rexx) — and some scaffolding for them (entry points, an earlier draft README) already exists in this repo. They are not being worked on yet; PL/I and ooRexx are the current priority. This section will grow as that work starts.

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
- **PL/I**: the right community/forum is not yet identified with confidence and needs its own verification pass when the time comes (candidates to check rather than assume: IBM's PL/I user communities/forums, any active PL/I mailing lists or newsgroups, compiler-vendor user groups) — this project's own PL/I lexer has no legacy Pygments code to point to, so real-world sample source will matter even more here than for ooRexx. When this outreach happens, explicitly solicit volunteers who might have personal or institutional access to the formal PL/I language standards — more authoritative than IBM's vendor docs, which is what the lexer's DCL-attribute/keyword/BIF vocabulary is currently sourced from, but not readily accessible online: ANSI X3.53-1976 (or its ISO counterpart, ISO 6160:1979), and both ANSI Subset G editions — X3.74-1981 and the later, distinct X3.74-1987 — plus their ISO counterparts ISO 6522:1985 and ISO/IEC 6522:1992. A personal copy, university library access, or an IBM/ANSI archive from someone in that community could let the vocabulary be cross-checked against the actual standards rather than just IBM's current implementation. This is a concrete ask, not just "let us know if you're interested."
- **Pygments**: no dedicated mailing list or IRC — Pygments is entirely GitHub-native (confirmed directly, not assumed). The outreach venue is settled: [GitHub Discussions](https://github.com/pygments/pygments/discussions), confirmed enabled on the repo, is where to float "I'm working on PL/I and ooRexx lexers, here's my plan" before a cold PR. Actual submission goes through the normal Issues/PR review process — new-language PRs aren't a separate ask-permission-first step — and the named maintainers (Georg Brandl, Matthäus Chajdas, Jean Abou-Samra) are reachable via that same PR/issue flow, not a separate email list. Not posting anything yet; this locks in the plan for when the lexers are further along.
- **Wikimedia**: already implied by the deployment pipeline above, but worth doing deliberately rather than just filing the Phabricator task silently.

What "aware" means in practice will firm up once each lexer is far enough along to actually show — this section will get more specific then.

## Platform

The lexers target upstream Pygments and, through the Wikimedia deployment pipeline, Wikipedia's syntaxhighlight extension. The Rexx and ooRexx lexers also target submission to RexxLA. Other lexers may have different targets.

## Collaboration

Contributions and corrections are welcome. If you maintain lexers for languages not yet covered here, please open an issue or pull request, or incorporate whatever is useful into your own work.

## Author

Shmuel (Seymour J. Metz) (שְׁמוּאֵל בֵּן ל״ביש)
[smetz3@gmu.edu](mailto:smetz3@gmu.edu)
[mason.gmu.edu/~smetz3](https://mason.gmu.edu/~smetz3)
GitHub: [shmuelmetz](https://github.com/shmuelmetz)

## License

[MIT](LICENSE)
