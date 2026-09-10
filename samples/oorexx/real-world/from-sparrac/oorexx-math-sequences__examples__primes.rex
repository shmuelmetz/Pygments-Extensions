/*----------------------------------------------------------------------------
Real-world sample gathered for lexer validation (not written for this project).
Source: https://github.com/sparrac/oorexx-math-sequences/blob/master/examples/primes.rex
Project: oorexx-math-sequences (Salvador Parra Camacho) -- a personal ooRexx library
         announced on the rexxla-members mailing list, 2026-09.
License: Apache License 2.0 (Apache-2.0) -- see the source repo's LICENSE.
         Retained here under those terms as part of pygments-extensions'
         own real-world lexer validation corpus; see
         samples/oorexx/real-world/README.md.
----------------------------------------------------------------------------*/
#!/usr/bin/env rexx

parse arg count

if count = '' then
  count = 100

primes = .PrimeSequence~new

say 'ℙ = {'primes~first(count)~makestring(, ', ')'...}'

exit

::requires 'Math/Sequences'
