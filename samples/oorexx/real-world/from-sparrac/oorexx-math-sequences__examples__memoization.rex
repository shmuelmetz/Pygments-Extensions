/*----------------------------------------------------------------------------
Real-world sample gathered for lexer validation (not written for this project).
Source: https://github.com/sparrac/oorexx-math-sequences/blob/master/examples/memoization.rex
Project: oorexx-math-sequences (Salvador Parra Camacho) -- a personal ooRexx library
         announced on the rexxla-members mailing list, 2026-09.
License: Apache License 2.0 (Apache-2.0) -- see the source repo's LICENSE.
         Retained here under those terms as part of pygments-extensions'
         own real-world lexer validation corpus; see
         samples/oorexx/real-world/README.md.
----------------------------------------------------------------------------*/
#!/usr/bin/env rexx

m = .MemoizedSequence~new(.CoolSequence~new(1, 1))

say m~first(10)~makestring(, ', ')

exit

::requires 'Math/Sequences'

::class CoolSequence subclass Sequence

::method init
  expose a1 a2
  use arg a1, a2
  
::method '[]'
  expose a1 a2
  use arg n
  
  if n = 1 then
    return a1
  if n = 2 then
    return a2
    
  return self[n - 1] + self[n - 2]
  
