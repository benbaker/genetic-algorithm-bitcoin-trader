
"""
mgws v0.01

MtGox Web Socket Interface

configuration loader

Copyright 2011 Brian Monkaba

This file is part of ga-bitbot.

    ga-bitbot is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ga-bitbot is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with ga-bitbot.  If not, see <http://www.gnu.org/licenses/>.
"""


import telnetlib
import json
from time import *

##get private channel API key
#API_client = Client('emfb','')
#r = API_client.get_key()
#print r
#sleep(5)




def _utf8(s):
    return s.encode('utf-8')


cs = "GET /mtgox HTTP/1.1\r\nUpgrade: WebSocket\r\nConnection: Upgrade\r\nHost: websocket.mtgox.com\r\nOrigin: null\r\n\r\n"



client = telnetlib.Telnet('websocket.mtgox.com',80)
client.write(cs)
print "Waiting for handshake..."
client.read_until("HTTP/1.1 101 Web Socket Protocol Handshake\r\nUpgrade: WebSocket\r\nConnection: Upgrade\r\nWebSocket-Origin: null\r\nWebSocket-Location: ws://websocket.mtgox.com/mtgox\r\nWebSocket-Protocol: *\r\n\r\n")
print "Handshake received, waiting for data"
reset_connection = False
stream_data = ""
stream_buffer = ""

while 1:
    df_d = {} #clear the data feed dictionary

    try:
        stream_data += client.read_very_eager()
    except:
        reset_connection = True
        stream_data = ""
        stream_buffer = ""

    #reset the connection if need be
    while reset_connection == True:
        try:
            print "Trying to reset connection..."
            client = telnetlib.Telnet('websocket.mtgox.com',80)
            client.write(cs)
            print "Waiting for handshake..."
            client.read_until("HTTP/1.1 101 Web Socket Protocol Handshake\r\nUpgrade: WebSocket\r\nConnection: Upgrade\r\nWebSocket-Origin: null\r\nWebSocket-Location: ws://websocket.mtgox.com/mtgox\r\nWebSocket-Protocol: *\r\n\r\n")
            stream_data = client.read_very_eager()
            reset_connection = False
        except:
            sleep(60)


    if len(stream_data) > 5:
        #print "-"*80
        #print "-"*80
        #print stream_data
        pass

    msg_cnt = 0
    while stream_data.find('{') >= 0:
        msg_found = False
        som = stream_data.find('{')
        #print "SOM found @",som
        nest = 0
        #scan until a whole message is found
        for i in range(som,len(stream_data)):
            if i > len(stream_data):
                msg_found == False
            else:
                c = stream_data[i]
                if c == '{':
                    nest += 1
                    #print "inc nest",nest
                if c == '}':
                    nest -= 1
                    #print "dec nest",nest
                    if nest == 0: #EOM
                        print "-"*80
                        print stream_data[som:i+1] #process_message(stream_data[som:i])
                        print "-"*80
                        stream_data = stream_data[i+1:]
                        msg_found = True
                        msg_cnt +=1
                        #print "::",msg_cnt
                        break
        if msg_found == False:
            break



