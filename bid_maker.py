
"""
bid_maker v0.01

sets the bid prices

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

#
#   Generates GA trade simulation reports using the gene server
#   Also calculates & submits the next buy trigger
#

__appversion__ = "0.01a"
print "Genetic Bitcoin Bid Maker v%s"%__appversion__
# connect to the xml server
#
import traceback
import xmlrpclib
import json
import paths
import gene_server_config
import time
import os

__server__ = gene_server_config.__server__
__port__ = str(gene_server_config.__port__)

#make sure the port number matches the server.
server = xmlrpclib.Server('http://' + __server__ + ":" + __port__)

print "bid_maker: connected to",__server__,":",__port__


from load_config import *
import __main__

#the variable values below are superceded by the configuration loaded from the
#configuration file global_config.json
#!!!!!!!! to change the values edit the json configuration file NOT the variables below !!!!!!!!
max_length = 60 * 24 * 60
enable_flash_crash_protection = True
flash_crash_protection_delay = 180
chart_zoom_periods = 3000
chart_now_periods = 200
win_loss_gate_pct = 0.80
price_format = "%.3f"
chart_type = 0
datafeed_stale_after_n_seconds = 360
config_loaded = 0
#load config
try:
    __main__ = load_config_file_into_object('global_config.json',__main__)
except:
    print "bid_maker: error detected while loading the configuration. the application will now exit."
    import sys
    sys.exit()
else:
    if config_loaded == False:
        print "bid_maker: configuration failed to load. the application will now exit."
        import sys
        sys.exit()
    else:
        print "bid_maker: configuration loaded."


#define a utility function to find the age of a datafeed
def datafeed_age(filename):
    f = open(filename,'r')
    f.seek(0,os.SEEK_END)
    #back of from the end of the file far enought to ensure the last line will be captured
    f.seek(-128,os.SEEK_CUR)
    last = float(f.readlines()[-1].split(',')[0]) #read the time stamp from the last line
    f.close()
    now = time.time()
    return (now - last)

#enter the main loop
while 1:
    start_time = time.time()

    skip_sleep_delay = False #default to sleep delay mode between cycles
                #will be set to true (and skip the sleep delay) if target prices are found.

    #get the hash list of all the databases
    gdhl = json.loads(server.get_gene_def_hash_list())
    gdhl.remove('0db45d2a4141101bdfe48e3314cfbca3') #remove the undefined db
    #for each db
    for gdh in gdhl:
        time.sleep(5) #throttle the load to the client computer and the gene server.
        #register as a default client (this will allow remote dynamic configuration of the report generation)
        pid = "BID_MAKER"
        #gdh = json.loads(server.get_default_gene_def_hash())
        #load the gene def config
        gd = json.loads(server.get_gene_def(gdh))
        server.pid_register_client(pid,gdh)

        print "_" * 80
        print "bid_maker: " + time.ctime()
        print "bid_maker: finding target bid for",gdh


        #create the trade engine
        print "bid_maker: loading the fitness function"
        ff = None
        if gd.has_key('fitness_script'):
            ff = __import__(gd['fitness_script'])
        else:
            ff = __import__('bct')
        ff = reload(ff) #make sure we're not using a cached version of the module
        te = ff.trade_engine()
        #te.cache.disable() #dont use cached data for reporting
        te.cache_input = False  #dont use cached input data for reporting

        #apply global configs (can be overridden by the gene def config)
        te.max_length = max_length
        te.enable_flash_crash_protection = enable_flash_crash_protection
        te.flash_crash_protection_delay = flash_crash_protection_delay

        #load the gene def fitness config into the trade engine
        if gd.has_key('fitness_config'):
            te = load_config_into_object(gd['fitness_config'],te)
        quartile = te.initialize()
        #select the quartile to test
        te.test_quartile(quartile)

        #get the high score gene from the gene server
        try:
            ag = json.loads(server.get(60*60*24*7,quartile,pid))
        except Exception, err:
            print "bid_maker: warning: gene server error or no data available."
            print Exception, err
            #if the quartile is active set the buy to 0 to prevent old targets from remaining active
            #this is for fault protection as it should never normaly happen:
            if quartile == server.get_active_quartile():
                p = {'buy':-1.00,'bid_maker_time_stamp':time.time(),'gene_id':'none','score':0}
                server.put_target(json.dumps(p),pid)
        else: 
            if type(ag) == type([]):
                ag = ag[0]

            if not (ag == {}):

                #load the gene dictionary into the trade engine
                te = load_config_into_object({'set':ag},te)

                #print ag
                print "_" * 40
                try:
                    print "bid_maker: quartile:",quartile, "(%.4f)"%ag['score'],"+active"
                except:
                    print ag

                server.put_active_quartile(quartile,pid)

                #run the trade engine
                try:
                    te.run()
                except:
                    print "bid_maker: gene fault"
                else:
                    datafeed_is_stale = False
                    if datafeed_age(te.input_file_name) > datafeed_stale_after_n_seconds:
                        print "bid_maker: warning: stale datafeed detected - bidding disabled"
                        datafeed_is_stale = True

                    if len(te.positions) == 0 or datafeed_is_stale:
                        if datafeed_is_stale:
                            print "bid_maker: stale datafeed, order cleared"
                        else:
                            print "bid_maker: no positions, order cleared"
                        p = {'buy':-1.00,'bid_maker_time_stamp':time.time(),'gene_id':ag['id'],'score':0}
                        server.put_target(json.dumps(p),pid)
                        te.cache_output(gdh + '/' + ag['id'],periods=60000)

                    # Calc the next buy trigger point
                    else:   #if len(te.positions) > 0:
                        #get the target trigger price
                        target = te.get_target()
                        print "bid_maker: inverse MACD result (target): ",target

                        if target > te.history[1]:
                            target = te.history[1]

                        #first check to see if the tested input triggered a buy:
                        if te.positions[-1]['buy_period'] == te.period - 1:
                            p = te.positions[-1]
                            target = p['buy']
                        else:
                            print "bid_maker: last buy order was", te.period - te.positions[-1]['buy_period'],"periods ago."
                            #if not try to calculate the trigger point to get the buy orders in early...
                            #print "Trying to trigger with: ",target
                            st = time.time()
                            te.input(st,target)
                            p = te.positions[-1].copy()
                            if p['buy'] != target:
                                #print "Order not triggered @",target
                                p['buy'] = 0.00
                                p['target'] = 0.00

                        score = te.score()
                        print "bid_maker: score: ",score
                        #time stamp the bid and capture the gene id
                        p.update({'bid_maker_time_stamp':time.time(),'gene_id':ag['id'],'score':score})

                        #te.chart("./report/chart.templ",gdh + '/' + ag['id'] + '.html',chart_zoom_periods,basic_chart=chart_type,write_cache_only=True)
                        te.cache_output(gdh + '/' + ag['id'],periods=150000)

                        #print "Evaluating target price"
                        if ((target >= p['buy']) or (abs(target - p['buy']) < 0.01)) and p['buy'] != 0: #submit the order at or below target
                            #format the orders
                            p['buy'] = float(price_format%(p['buy'] - 0.01))
                            p['target'] = float(price_format%p['target'])
                            p.update({'stop_age':(60 * te.stop_age)})
                            if float(te.wins / float(te.wins + te.loss + 0.000001)) > win_loss_gate_pct:
                                #only submit an order if the win/loss ratio is greater than x%
                                print "bid_maker: sending target buy order to server @ $" + str(p['buy'])
                                server.put_target(json.dumps(p),pid)
                                skip_sleep_delay = True #if target buy orders are active skip the sleep delay
                            else:
                                print "bid_maker: underperforming trade strategy, no order"
                                p['buy'] = 0.00
                                p['target'] = 0.00
                                server.put_target(json.dumps(p),pid)
                            print "-" * 40
                            print "bid_maker: trigger criteria met, bid set."
                            #print "\tQuartile     :",quartile
                            print "\tBuy        :$", p['buy']
                            print "\tTarget     :$",p['target']
                            print "\tWin Ratio    :","%.3f"%((te.wins / float(te.wins + te.loss + 0.000001)) * 100),"%"
                            print "-" * 40
                        else:
                            print "-" * 40
                            print "bid_maker: trigger criteria not met, no bid set."
                            print "\tBuy        :$", p['buy']
                            print "\tTarget     :$",p['target']
                            print "\tInput Target :$",target
                            #print "\tMACD Log     : ",te.logs.get('macd')[-1][1]
                            #print "\tMACD Trip    : ",te.macd_buy_trip
                            print "-" * 40
                            p.update({'stop_age':(60 * te.stop_age)}) #DEBUG ONLY!! - delete when done.
                            p['buy'] = 0.00
                            p['target'] = 0.00
                            server.put_target(json.dumps(p),pid)


    while True:
        loop_time = time.time() - start_time
        if loop_time > 60:
            break
        time.sleep(60 - loop_time)
