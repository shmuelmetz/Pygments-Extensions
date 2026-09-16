# Draft reply to Jeff Hennick (2nd message)

Status: draft for review — not sent. Jeff's reply: positive ("looking
very good"), but he's **out of town for a few weeks** and can't run
the code yet. He answered Q4 fully — the `\C`/`\B`/`\P`/`\S`/`\L`/`\M`
family is on **p.50 of the Pipelines Guide and Reference**, the
`compare`-stage substitution escapes. He also mentioned an **HTML
stage-documentation file** (used to generate the paper version, not in
the distribution) he'd send when home.

---

**Subject:** Re: [rexxla-members] New Pygments lexers for ooRexx, PL/I, and NetRexx

Jeff,

Perfect — thank you. That's exactly what I needed. I've added the
`\C`/`\B`/`\P`/`\S`/`\L`/`\M` family (and lowercase) as `String.Escape`
in DStrings, in both the doubled-backslash form the files actually use
and the bare form. Re-ran it against all 232 `.njp` files: still no
tokenizing errors, and about 6,600 escape sequences now highlight.
It's pushed.

The DString's *own* escapes — the `\n` in `/Less:\nActual:\n.../` — I'm
still leaving as plain text, since I haven't found the DString escape
set in the Guide yet. If you happen to know the page, I'll model those
too; otherwise it'll wait.

No hurry at all on the other three questions (per-stage option grammar,
the stage-name filter, the `--` reading) — whenever you're back and can
put the real thing through its paces. And yes, I'd be very glad of that
HTML stage-documentation file when you're home; it sounds like the
right source for the per-stage option shapes, which is the one place
this lexer is deliberately shallow right now.

Safe travels.

Shmuel (Seymour J.) Metz
