# pygments-extensions

Custom lexers extending Pygments ([pygments.org](https://pygments.org/)), the Python syntax highlighting library.

## Purpose

Several languages relevant to the author's work are absent from the Pygments distribution or have incomplete support. This project provides additional lexers for use in local tools, MediaWiki `<syntaxhighlight>` tags, and wherever Pygments is used as a highlighting engine.

## Languages

## PL/I

PL/I support existed in Pygments before a major rewrite and was not carried forward into the current codebase. This lexer restores that support.

## ooRexx

Open Object Rexx lexer for syntax highlighting of ooRexx source.

## Wikipedia deployment

Getting a new lexer into Wikipedia's `<syntaxhighlight>` tag requires working through several independent projects on different schedules:

- Submit the lexer to upstream Pygments and get it merged
- Wait for Pygments to cut a release containing the new lexer
- Wait for Wikimedia to pick up the new Pygments release in its SyntaxHighlight extension
- File a Phabricator task on [phabricator.wikimedia.org](https://phabricator.wikimedia.org/) asking Wikimedia to enable the new language tags
- Wait for Wikimedia to deploy the tag enablement

This project serves as a working home for the lexers during that process and as a standalone tool for local use in the meantime.

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
