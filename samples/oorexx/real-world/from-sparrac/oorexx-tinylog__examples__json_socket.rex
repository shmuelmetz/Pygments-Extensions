#!/usr/bin/env rexx
/*----------------------------------------------------------------------------
Real-world sample gathered for lexer validation (not written for this project).
Source: https://github.com/sparrac/oorexx-tinylog/blob/master/examples/json_socket.rex
Project: oorexx-tinylog (Salvador Parra Camacho) -- a personal ooRexx library
         announced on the rexxla-members mailing list, September 2026.
License: Apache License 2.0 (Apache-2.0) -- see the source repo's LICENSE.
         Retained under those terms as part of pygments-extensions' own
         real-world lexer validation corpus; see
         samples/oorexx/real-world/README.md.
----------------------------------------------------------------------------*/
-- json_socket.rex
-- Send structured JSON logs over a TCP socket.
-- Before running this example:
--   nc -l 8888

log = .Logger~new()

-- The formatter returns JSON
log~formatter = .routines['JSONFORMATTER']

-- The output goes to a socket
so = .StreamSocket~new('localhost', '8888')
log~output = so

log~info("This is simple information.")
log~error("This is an error.")
  
exit

::requires 'TinyLog'
::requires 'JSON.cls'
::requires 'streamsocket.cls'

::routine JSONFormatter
  use arg record

  -- Remove non-serializable objects.
  record~remove('CONTEXT')
  
  return .JSON~toJSON(record)
