/*----------------------------------------------------------------------------
Real-world sample gathered for lexer validation (not written for this project).
Source: https://github.com/sparrac/oorexx-mpd/blob/master/MPD.rex
Project: oorexx-mpd (Salvador Parra Camacho) -- a personal ooRexx library
         announced on the rexxla-members mailing list, September 2026.
License: Apache License 2.0 (Apache-2.0) -- see the source repo's LICENSE.
         Retained under those terms as part of pygments-extensions' own
         real-world lexer validation corpus; see
         samples/oorexx/real-world/README.md.
----------------------------------------------------------------------------*/
/*

  MPD.rex
  
  MPD (Music Player Daemon) client library for Open Object Rexx.
  
  Copyright (c) 2026 Salvador Parra Camacho
  
  License: Apache License 2.0
  Version: 0.1.0

 */

::requires 'socket.cls'

::method unknown
  parse arg index

  do i over self
  	if index~lower = i~lower then
  		return self~at(i)
  end

  return .nil

::class MPD public

::method hostname attribute
::method port attribute
::method desc attribute
::method password attribute
::method timeout attribute
::method retry attribute
::attribute protocol get
::attribute protocol set private

::method init

  use arg settings = .nil

  -- Default settings
  self~hostname = 'localhost'
  self~port     = 6600
  self~desc     = self~hostname
  self~password = ''
  self~timeout  = 1
  self~retry    = 60

  self~protocol = ''
  
  if settings <> .nil then do
    if settings~hasentry('hostname') then
      self~hostname = settings['hostname']
    if settings~hasentry('port') then
      self~port = settings['port']
    if settings~hasentry('desc') then
      self~desc = settings['desc']
    if settings~hasentry('password') then
      self~password = settings['password']
    if settings~hasentry('timeout') then
      self~timeout = settings['timeout']
    if settings~hasentry('retry') then
      self~retry = settings['retry']
  end

::method connect
	expose socket

	socket = SockSocket('AF_INET', 'SOCK_STREAM', '0')

  call SockGetHostByName self~hostname, 'host.!'

  host.!family = 'AF_INET'
  host.!port   = self~port

  ret = SockConnect(socket, 'host.!')

  response = SockRecv(socket, 'data', 24)
  parse var data . . version '0a'x
  self~protocol = version

  return ret

::method disconnect
  expose socket
  call SockShutDown socket, 2
  return SockClose(socket)

::method send
  expose socket
  use arg action

  call SockSend socket, action || '0a'x

  mpd_ok   = 'OK' || '0a'x
  mpd_ack  = 'ACK'
  response = ''

  do forever
    datasize = SockRecv(socket, 'data', 1024)
    if datasize <= 0 then leave
    response = response || data
    if pos(mpd_ok, response) <> 0 | pos(mpd_ack, response) = 1 then leave
  end

  return response~makearray

::method clear
  return self~send("clear")
  
::method status
	resp = self~send("status")
	return self~get_directory(resp)

::method stats
  resp = self~send("stats")
  return self~get_directory(resp)

::method next
  return self~send("next")

::method previous
  return self~send("previous")

::method stop
  return self~send("stop")

::method pause
  use arg opt
  return self~send("pause" opt)

::method play
  use strict arg songpos = ''
  return self~send('play' songpos)

::method playid
  use strict arg songid = ''
  return self~send('playid' songid)

::method seek
  use arg songpos, time
  return self~send('seek' songpos time)  

::method seekid
  use arg songid, time
  return self~send('seekid' songid time)

::method seekcur
  use arg time
  return self~send('seekcur' time)

::method 'consume='
  use arg state
  self~send("consume" state)

::method consume
  return self~status~consume

::method 'random='
  use arg state
  self~send("random" state)

::method random
  return self~status~random

::method 'repeat='
  use arg state
  self~send("repeat" state)

::method repeat
  return self~status~repeat

::method 'single='
  use arg state
  self~send("single" state)

::method single
  return self~status~single

::method 'volume='
  use arg vol
  self~send("setvol" vol)

::method volume
  return self~status~volume

::method 'replay_gain='
  use arg mode
  valid_modes = .Array~of('off', 'track', 'album', 'auto')
  if valid_modes~hasitem(mode) then do
    self~send("replay_gain_mode" mode)
  end

::method replay_gain
  resp = self~send("replay_gain_status")
  return self~get_directory(resp)~replay_gain_mode

::method currentsong
  resp = self~send("currentsong") 
  return self~get_directory(resp)

::method playlist
	resp = self~send("playlistinfo")
  playlist_array = .Array~new

  starts = 1

  do i = 1 to resp~items
    if resp[i]~pos('file: ') = 1 then do
      playlist_array~append(self~get_directory(resp~section(starts, i - starts)))
      
      starts = i
    end
  end

  return playlist_array

::method search
  use arg string
  resp = self~send("search" string)
  return resp~makestring

::method toggle
  use arg opt
  valid_opts = .Array~of('consume', 'repeat', 'random', 'single')
  
  if \ valid_opts~hasitem(opt) then return

  if self~status~at(opt) = 1 then
    self~send(opt 0)
  else
    self~send(opt 1)

::method get_directory private
  use arg array
  
  dir = .Directory~new
  dir~setMethod('UNKNOWN', .methods['UNKNOWN'])

  do line over array
    if pos('OK', line) = 1 then iterate
    parse var line opt ': ' val
    dir~put(val, opt)
  end

  return dir
