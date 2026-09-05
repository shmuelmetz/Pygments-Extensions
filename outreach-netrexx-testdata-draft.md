**Venue:** groups.io/g/netrexx (NetRexx Forum), cross-posted to
main@rexxla-members.groups.io

**Subject:** New Pygments lexer for NetRexx — looking for real-world
.nrx source and reviewers

---

Hi all,

I maintain [pygments-extensions](https://github.com/shmuelmetz/Pygments-Extensions),
a set of Pygments (Python syntax-highlighting library) lexers already
covering Open Object Rexx and PL/I. I've just added a first-pass
NetRexx lexer and would like help validating it against real code
before calling it ready.

The lexer is built independently against the NetRexx 4.02-GA Language
Reference (comments, string escapes, numeric symbols, class/method/
properties declarations, type annotations) rather than adapted from
the classic-Rexx or ooRexx lexers already in the project — NetRexx's
Java-shaped class/method/type layer and dot-notation method calls
don't share enough structure with either to make that a good fit.
99 tests currently pass, all against hand-written snippets drawn from
the Tutorial and Language Reference's own examples.

What I don't have yet is real .nrx source to test against, and that's
historically where a from-the-spec lexer finds its actual gaps — the
ooRexx and PL/I lexers here both had real bugs surface only once real
code was thrown at them (a missing line-comment form, symbol-charset
gaps, embedded-block handling), not from re-reading the spec harder.

If you have NetRexx source you're willing to share — anything from a
small utility to a full project — I'd be glad to run it through the
lexer and fix whatever it gets wrong. Particularly useful:

- Real class hierarchies using `extends`/`implements`/`uses`
- Binary classes/methods (the `binary` keyword)
- `select`/`signal`/exception-handling code (catch/finally, signals
  lists) — the grammar sections I haven't fully cross-checked yet
- Anything using the built-in Rexx-class string methods, or Java
  interop beyond simple `System.out`-style calls
- Older or unusual NetRexx (pre-4.0, IBM-era) if you have it — I'd
  like to know if anything's changed in ways that matter to a lexer

Also useful, if anyone has it: pointers to other NetRexx source
collections I could pull from directly (a GitHub org, an old FTP
archive, Rosetta Code's NetRexx entries, etc.) — I'd rather work from
real, attributable code than write more synthetic samples.

Thanks,
Shmuel (Seymour J. Metz)
