/*----------------------------------------------------------------------------
Real-world sample gathered for lexer validation (not written for this project).
Source: https://github.com/sparrac/oorexx-gnuplot/blob/master/examples/session_explicit_multiplot.rex
Project: oorexx-gnuplot (Salvador Parra Camacho) -- a personal ooRexx library
         announced on the rexxla-members mailing list, 2026-09.
License: Apache License 2.0 (Apache-2.0) -- see the source repo's LICENSE.
         Retained here under those terms as part of pygments-extensions'
         own real-world lexer validation corpus; see
         samples/oorexx/real-world/README.md.
----------------------------------------------------------------------------*/
#!/usr/bin/env rexx
-- session_explicit_multiplot.rex
-- Creates a multiplot

g = .GnuplotSession~new
g~open

g~set('xrange [-5:5]')
g~set('yrange [-5:5]')
g~set('multiplot layout 2,2 title "Powers of x"')
g~set('grid')
g~set('size square')

colors = ('red', 'blue', 'green', 'orange')

do i = 1 to 4
  g~set('title "f(x) = x^'i'"')
  g~plot('x**' || i 't "x^'i'" lw 2 lc "'colors[i]'"')
end

g~unset('multiplot')

g~close


::requires 'GnuplotSession'
