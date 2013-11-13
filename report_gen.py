
"""
report_gen v0.01

report generator

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
print "Genetic Bitcoin Report Generator v%s"%__appversion__
# connect to the xml server
#

import xmlrpclib
import json
import paths
import gene_server_config
import time


__server__ = gene_server_config.__server__
__port__ = str(gene_server_config.__port__)

#make sure the port number matches the server.
server = xmlrpclib.Server('http://' + __server__ + ":" + __port__)

print "Connected to",__server__,":",__port__


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
config_loaded = 0
#load config
try:
    __main__ = load_config_file_into_object('global_config.json',__main__)
except:
    print "Error detected while loading the configuration. The application will now exit."
    import sys
    sys.exit()
else:
    if config_loaded == False:
        print "Configuration failed to load. The application will now exit."
        import sys
        sys.exit()
    else:
        print "Configuration loaded."

def generate_empty_charts(quartile):
    print "creating empty charts..."
    f = open("./report/chart.templ",'r')
    templ = f.read()
    f.close()

    templ = templ.replace('{LAST_UPDATE}','<b>NO ORDERS TO REPORT</b>')
    templ = templ.replace('{METRICS_REPORT}','')
    templ = templ.replace('{ORDERS_REPORT}','')


    f = open("./report/chart_test_%s.html"%str(quartile),'w')
    f.write(templ)
    f.close()

    f = open("./report/chart_test_zoom_%s.html"%str(quartile),'w')
    f.write(templ)
    f.close()

def load():
    #open the history file
    #print "loading the data set"
    f = open("./datafeed/bcfeed_mtgoxUSD_1min.csv",'r')
    #f = open("./datafeed/test_data.csv",'r')
    d = f.readlines()
    f.close()

    if len(d) > max_length:
        #truncate the dataset
        d = d[max_length * -1:]

    #load the backtest dataset
    input = []
    for row in d[1:]:
        r = row.split(',')[1] #last price
        t = row.split(',')[0] #time
        input.append([int(float(t)),float(r)])
    #print "done loading:", str(len(input)),"records."
    return input



while 1:
    skip_sleep_delay = False #default to sleep delay mode between cycles
                #will be set to true (and skip the sleep delay) if target prices are found.

    #register as a default client (this will allow remote dynamic configuration of the report generation)
    pid = "REPORT_GEN"
    gdh = json.loads(server.get_default_gene_def_hash())
    print gdh
    #load the gene def config
    gd = json.loads(server.get_gene_def(gdh))
    server.pid_register_client(pid,gdh)

    print "_" * 80
    print time.ctime()
    #load the data set
    input = load()

    buys = []
    targets = []
    for quartile in [4,3,2,1]:

        #get the high score gene from the gene server
        try:
            ag = json.loads(server.get(60*60*24*7,quartile,pid))
        except:
            print "warning: gene server error or no data available."
            #if the quartile is active set the buy to 0 to prevent old targets from remaining active
            #this is for fault protection as it should never normaly happen:
            if quartile == server.get_active_quartile():
                p = {'buy':0.00}
                server.put_target(json.dumps(p),pid)
            #generate empty charts to prevent old data from being reported.
            generate_empty_charts(quartile)
        else:

            if type(ag) == type([]):
                ag = ag[0]

            #create the trade engine
            print "report: loading the fitness function"
            ff = None
            if gd.has_key('fitness_script'):
                ff = __import__(gd['fitness_script'])
            else:
                ff = __import__('bct')
            ff = reload(ff) #make sure we're not using a cached version of the module
            te = ff.trade_engine()
            te.cache.disable()  #dont use cached data for reporting

            #apply global configs
            te.max_length = max_length
            te.enable_flash_crash_protection = enable_flash_crash_protection
            te.flash_crash_protection_delay = flash_crash_protection_delay
            #load the gene dictionary into the trade engine
            te = load_config_into_object({'set':ag},te)
            #load the gene def fitness config into the trade engine
            if gd.has_key('fitness_config'):
                te = load_config_into_object(gd['fitness_config'],te)

            #preprocess the data
            #current_quartile = te.classify_market(input)
            current_quartile = te.initialize()
            #update the gene server with the current market quartile
            server.put_active_quartile(current_quartile,pid)
            #select the quartile to test
            te.test_quartile(quartile)

            print "_" * 40
            if current_quartile == quartile:
                print "Quartile:",quartile, "(%.4f)"%ag['score'],"+active"
            else:
                print "Quartile:",quartile, "(%.4f)"%ag['score']

            #feed the input through the trade engine
            try:
                #for i in input:
                #   te.input(i[0],i[1])
                te.run()
            except:
                print "Gene Fault"
            else:
                if len(te.positions) == 0:
                    #no data to report but the chart reports need to be created to prevent stale data reports or 404 errors.
                    generate_empty_charts(quartile)
                    if current_quartile == quartile:
                        print "no positions, order not submitted"
                        p = {'buy':0.00}
                        server.put_target(json.dumps(p),pid)

                # Calc the next buy trigger point
                elif len(te.positions) > 0:
                    #get the target trigger price
                    target = te.get_target()
                    print "Inverse MACD Result (target): ",target

                    #if target > te.input_log[-1][1]:
                    #   target = te.input_log[-1][1]

                    if target > te.history[1]:
                        target = te.history[1]

                    #first check to see if the tested input triggered a buy:
                    if te.positions[-1]['buy_period'] == te.period - 1:
                        p = te.positions[-1]
                        target = p['buy']
                    else:
                        print "Last buy order was", te.period - te.positions[-1]['buy_period'],"periods ago."
                        #if not try to calculate the trigger point to get the buy orders in early...
                        #print "Trying to trigger with: ",target
                        print "Score: ",te.score()
                        st = input[-1][0] + 2000
                        te.input(st,target)
                        p = te.positions[-1].copy()
                        if p['buy'] != target:
                            #print "Order not triggered @",target
                            p['buy'] = 0.00
                            p['target'] = 0.00

                    #te.classify_market(input)
                    print "creating charts..."
                    te.chart("./report/chart.templ","./report/chart_test_%s.html"%str(quartile),basic_chart=chart_type)
                    te.chart("./report/chart.templ","./report/chart_test_zoom_%s.html"%str(quartile),chart_zoom_periods,basic_chart=chart_type)
#                   te.chart("./report/chart.templ","./report/chart_test_now_%s.html"%str(quartile),chart_now_periods,basic_chart=chart_type)
                    #print "Evaluating target price"
                    if current_quartile == quartile:
                        if ((target >= p['buy']) or (abs(target - p['buy']) < 0.01)) and p['buy'] != 0: #submit the order at or below target
                            #format the orders
                            p['buy'] = float(price_format%(p['buy'] - 0.01))
                            p['target'] = float(price_format%p['target'])
                            p.update({'stop_age':(60 * te.stop_age)})
                            if float(te.wins / float(te.wins + te.loss)) > win_loss_gate_pct:
                                #only submit an order if the win/loss ratio is greater than x%
                                print "sending target buy order to server @ $" + str(p['buy'])
                                server.put_target(json.dumps(p),pid)
                                skip_sleep_delay = True #if target buy orders are active skip the sleep delay
                            else:
                                print "underperforming trade strategy, order not submitted"
                                p['buy'] = 0.00
                                p['target'] = 0.00
                                server.put_target(json.dumps(p),pid)
                            print "-" * 40
                            print "Quartile     :",quartile
                            print "Buy      :$", p['buy']
                            print "Target       :$",p['target']
                            print "Win Ratio    :","%.3f"%((te.wins / float(te.wins + te.loss)) * 100),"%"
                            print "-" * 40
                        else:
                            print "Trigger criteria not met, no order set."
                            print "Buy      :$", p['buy']
                            print "Target       :$",p['target']
                            print "Input Target :$",target
                            print "Last Price   :$",input[-1][1]
                            print "MACD Log     : ",te.logs.get('macd')[-1][1]
                            print "MACD Trip    : ",te.macd_buy_trip
                            p.update({'stop_age':(60 * te.stop_age)}) #DEBUG ONLY!! - delete when done.
                            p['buy'] = 0.00
                            p['target'] = 0.00
                            server.put_target(json.dumps(p),pid)

                        buys.append(p['buy'])
                        targets.append(p['target'])
    #log the orders
    #f = open("./report/rg_buys.csv",'a')
    #f.write(",".join(map(str,buys)) + ",")
    #f.write(",".join(map(str,targets)) + "\n")
    #f.close()

    #create the gene visualizer report
    print "creating the gene visualizer report..."
    f = open('./report/gene.templ','r')
    template = f.read()
    f.close()

    for quartile in [1,2,3,4]:
        band_l = []
        gl = json.loads(server.get_bobs(quartile,pid))
        if len(gl) > 0:
            #place a band (a small list of gene set to all 1's) in the data to highlight the break between the bobs and high scores
            band = "1" * len(gl[0]['gene'])
            for i in xrange(3):
                band_l.append({'gene':band})
        gl += band_l
        gl += json.loads(server.get_all(quartile,pid))
        l = []
        for ag in gl:
            l.append(ag['gene'])
        qs = '{Q%s}'%str(quartile)
        template = template.replace(qs,str(l).replace('u',''))

    template = template.replace('{LAST_UPDATE}',time.ctime())
    f = open('./report/gene_visualizer.html','w')
    f.write(template)
    f.close()

    if skip_sleep_delay == False:
        print "sleeping..."
        print "_" * 80
        print "\n"
        time.sleep(600) #generate a report every n seconds
    else:
        time.sleep(600)
        print "skipping sleep state due to active trigger prices..."
        print "_" * 80
        print "\n"
