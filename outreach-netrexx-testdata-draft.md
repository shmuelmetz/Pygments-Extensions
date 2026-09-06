**Subject:** New Pygments lexers for ooRexx, PL/I, and NetRexx — looking for real-world NetRexx source

**Distribution:** netrexx@groups.io, main@rexxla-members.groups.io, IBM-MAIN (cross-posted — apologies to anyone on more than one of these lists)

**Body:**

Hi all,

I maintain [pygments-extensions](https://github.com/shmuelmetz/Pygments-Extensions), a set of Pygments (the Python syntax-highlighting library) lexers for languages it doesn't otherwise support. It now covers three: Open Object Rexx, PL/I, and, as of this week, NetRexx.

The ooRexx and PL/I lexers are real-world-validated against a combined corpus of over 150 files (official interpreter samples, Rosetta Code, and personal/legacy scripts), with 72 passing tests between them.

The NetRexx lexer is new and built independently against the actual NetRexx 4.02-GA Language Reference — not adapted from the classic-Rexx or ooRexx lexers already in the project, since NetRexx's Java-shaped class/method/type layer and dot-notation method calls (`v.mag()`, not ooRexx's `~` message-send) don't share enough structure with either. 104 tests currently pass, but all of them are hand-written against the Reference's own examples — it hasn't yet seen a single line of real NetRexx source.

That's what I'm asking for: real `.nrx` code to validate the lexer against. The ooRexx and PL/I lexers here both had genuine bugs surface only once real code was thrown at them, not from re-reading the spec harder, and I expect the same will be true here. Particularly useful:

- Real class hierarchies using `extends`/`implements`/`uses`
- Binary classes or methods (the `binary` keyword)
- `select`/`signal`/exception-handling code (catch/finally, signals lists)
- Anything exercising the built-in Rexx-class string methods, or Java interop beyond simple calls
- Code running under z/OS specifically — given zAAP's twenty-year history of making Java (and by extension NetRexx) workloads cost-attractive on the mainframe, and the current wave of COBOL-to-Java modernization, I'd particularly like to see real enterprise z/OS NetRexx if anyone has it
- Older or IBM-era NetRexx, if anything's changed in ways that matter to a lexer

Anything from a small utility to a full application is useful — I'll run it through the lexer and fix whatever it gets wrong. Pointers to other NetRexx source collections (a GitHub org, an archive, Rosetta Code entries) are just as welcome as code itself.

Thanks,
Shmuel (Seymour J. Metz)
