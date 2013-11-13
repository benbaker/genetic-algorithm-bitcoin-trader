
"""
bcfeed v0.01

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

def process(message):
    mdict = json.loads(message)
    return mdict['symbol'],mdict['price'],mdict['volume']

reset_connection = True
stream_buffer = ""
while 1:
    df_d = {} #clear the data feed dictionary

    #reset the connection if need be
    while reset_connection == True:
        try:
            print "bcfeed: Trying to reset connection..."
            client = telnetlib.Telnet('bitcoincharts.com',27007)
            stream_data = client.read_very_eager()
            reset_connection = False
        except:
            print "bcfeed: Connection reset failed. Wait to retry..."
            sleep(30)

    try:
        stream_data = client.read_very_eager()
    except:
        reset_connection = True
        stream_data = ""
        stream_buffer = ""


    #capture any available data from the feed
    if len(stream_data) > 0:
        stream_buffer += stream_data

    #see if a complete message has been received
    eom = stream_buffer.find('}')
    while  eom > -1:
        message = stream_buffer[:eom+1]
        stream_buffer = stream_buffer[eom+3:]
        symbol,price,volume = process(message)
        #capture the price volume data
        if price > 0:
            if df_d.has_key(symbol):
                df_d[symbol]['p'].append(price)
                df_d[symbol]['v'].append(volume)
            else:
                df_d.update({symbol:{'p':[price],'v':[volume]}})
        eom = stream_buffer.find('}')

    t = time()

    #calculate the weighted volume price if there were orders
    for symbol in df_d.keys():
        print df_d[symbol]
        wps = 0 #weighted price sum
        tv = 0  #total volume
        for i in range(len(df_d[symbol]['p'])):
            wps += df_d[symbol]['p'][i] * df_d[symbol]['v'][i]
            tv += df_d[symbol]['v'][i]
        if tv > 0:
            wp = wps/tv
            #add the weighted price and total volume
            df_d[symbol].update({'wp':wps/tv,'tv':tv})
            print "-"*40
            print "symbol :",symbol
            print "time   :",t
            print "price  :",wp
            print "volume :",tv

            f = open("./datafeed/bcfeed_%s_1min.csv"%symbol,'a')
            f.write(",".join((str(t),str(wp),str(tv))) + '\n')
            f.close()
    sleep(60)
