/*----------------------------------------------------------------------------
Real-world sample gathered for lexer validation (not written for this project).
This is CLASSIC Rexx, not ooRexx -- kept as a negative-test case for
OORexxLexer.analyse_text(): it must score 0.0 on this file (no OO markers)
so classic RexxLexer, not this lexer, is the one Pygments picks for it.
Source: https://github.com/RexxLA/rexx-repository/blob/master/Classic_Rexx/crx/CRX1999/TESTS/40/MK40.REX
Project: RexxLA rexx-repository (community-donated Rexx source/library
         archive maintained by the Rexx Language Association)
License: per the repository's own README, "all materials are donated
         under various open source licenses, or are in the public
         domain" -- no more specific per-file license notice was found
         in this file. Retained here under those stated terms as part
         of pygments-extensions' own real-world lexer validation
         corpus; see samples/oorexx/real-world/README.md.
----------------------------------------------------------------------------*/
/* A little rexx program to ease testcase making. */
Restart:
 p1='3';p2='1';p3='A'
 fn='9P'p1'P'p2||p3'.RX'
Cycle:
 prevfn=fn
 fn='9P'p1'P'p2||p3'.RX'
 if stream(fn,'C',"QUERY EXISTS")='' then "copy" prevfn fn
 "mye" fn
What:
 say "A bumps letter,B bumps right number,C bumps groupno, R restart, X exit"
 pull User
 if User='A' then do
   p3=d2c(c2d(p3)+1)
   signal Cycle
   end
 if User='B' then do
   p2=p2+1; p3='A'
   signal Cycle
   end
 if User='C' then do
   p1=p1+1; p2=1; p3='A'
   signal Cycle
   end
 if User='R' then signal Restart
 if User='X' then exit
 signal What
