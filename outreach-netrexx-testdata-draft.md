**Venue:** groups.io/g/netrexx (NetRexx Forum), posting address
netrexx@groups.io, cross-posted to main@rexxla-members.groups.io and
IBM-MAIN. IBM-MAIN is not a
mismatch here despite NetRexx being JVM-based -- zAAP (introduced
2004, explicitly for Java/XML workloads under z/OS, folded into zIIP
from z13 in 2015 onward) has given mainframe shops a real, cost-driven
incentive to run Java -- and therefore NetRexx -- directly on z/OS for
two decades, a live topic there even now via COBOL-to-Java
modernization work. That's a genuinely different, and arguably more
valuable, population than the NetRexx/RexxLA forums: real enterprise
z/OS NetRexx source, not hobbyist samples. Frame the IBM-MAIN post
around that angle specifically rather than reusing the NetRexx-forum
text verbatim (see the alternate opening below).

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

---

**Alternate opening for the IBM-MAIN cross-post** (same body from "The
lexer is built independently..." onward, swap the intro paragraph):

Hi all,

I maintain a set of Pygments (Python syntax-highlighting library)
lexers, already covering Open Object Rexx and PL/I, and have just
added one for NetRexx. Given zAAP/zIIP's long history of making Java
workloads (and by extension NetRexx, which compiles to Java/JVM
bytecode) cost-attractive to run directly on z/OS, I'm hoping some of
you have real NetRexx source running under z/OS I could validate the
lexer against -- old or current, small utility or full application.
