#!/usr/bin/env rexx
/*----------------------------------------------------------------------------
Real-world sample gathered for lexer validation (not written for this project).
Source: https://github.com/sparrac/eorexx/blob/master/examples/mean.rex
Project: eorexx (Salvador Parra Camacho) -- a personal ooRexx library
         announced on the rexxla-members mailing list, September 2026.
License: Common Public License v1.0 (CPL-1.0) -- see the source repo's LICENSE.
         Retained under those terms as part of pygments-extensions' own
         real-world lexer validation corpus; see
         samples/oorexx/real-world/README.md.
----------------------------------------------------------------------------*/

args = .SysCArgs

sum = 0
N   = args~items

do i = 1 to N
  sum += args[i]
end

if N <> 0 then
  say sum/N

exit
