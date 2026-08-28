/*----------------------------------------------------------------------------
Real-world sample gathered for lexer validation (not written for this project).
This is CLASSIC Rexx, not ooRexx -- kept as a negative-test case for
OORexxLexer.analyse_text(): it must score 0.0 on this file (no OO markers)
so classic RexxLexer, not this lexer, is the one Pygments picks for it.
Source: https://github.com/RexxLA/rexx-repository/blob/master/Classic_Rexx/crx/CRX1999/Tools/KEYS.REX
Project: RexxLA rexx-repository (community-donated Rexx source/library
         archive maintained by the Rexx Language Association)
License: per the repository's own README, "all materials are donated
         under various open source licenses, or are in the public
         domain" -- no more specific per-file license notice was found
         in this file. Retained here under those stated terms as part
         of pygments-extensions' own real-world lexer validation
         corpus; see samples/oorexx/real-world/README.md.
----------------------------------------------------------------------------*/
/* Add a few lines to the table of keywords. */
  In = "is.kwa"
  Out = "keys.inc"
  "ERASE" Out
  call lineout Out,"$DoKeys:"
  call lineout Out,' db $UNTIL-KeysBase,5,"UNTIL"'
  call lineout Out,' db $WHILE-KeysBase,5,"WHILE"'
  do while lines(In)>0
    Line = linein(In)
    if left(Line,10)=" db $UNTIL" then
      call lineout Out,"$CondKeys:"
    if left(Line,9)=" db $WITH" then
      call lineout Out,"$WithKey:"
    if left(Line,9)=" db $THEN" then
      call lineout Out,"$ThenKey:"
    if Line<>'' then call lineout Out,Line
  end
