
"""
bcbookie v0.01

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


import pdb
import pickle
from operator import itemgetter
from time import *
import paths
import MtGoxHMAC

# connect to the xml server
#

import xmlrpclib
#import json
import json

import gene_server_config
import pdb

__server__ = gene_server_config.__server__
__port__ = str(gene_server_config.__port__)

#make sure the port number matches the server.
server = xmlrpclib.Server('http://' + __server__ + ":" + __port__)

print "Connected to",__server__,":",__port__

class bookie:
    def __init__(self,enable_text_messaging=False,enable_flash_crash_protection=False,flash_crash_protection_delay=0):
        self.client = MtGoxHMAC.Client()
        #flash crash protection delays stop loss orders by three hours - hopefully enough time to for the market to stabilize
        self.__enable_flash_crash_protection = enable_flash_crash_protection
        self.__flash_crash_protection_delay = flash_crash_protection_delay * 60 #convert min to seconds
        self.__enable_text_messaging = enable_text_messaging
        if self.__enable_text_messaging==True:
            import AWS_SNS
            self.aws_client = AWS_SNS.Client()
            #send the system startup message
            self.aws_client.send('bcbookie started on %s'%(ctime()))
            print "Amazon SNS enabled."

        if self.__enable_flash_crash_protection == True:
            print "Flash crash protection enabled (%s sec delay)"%(str(self.__flash_crash_protection_delay))

        #These variables update automaticaly - do not modify
        self.client_info = None
        self.client_commission = 0
        self.orders = []
        self.records = []
        self.balance = 0
        self.balance_committed = 0
        self.usds = 0
        self.btcs = 0
        self.btc_price = 0
        self.load_records()
        self.active_quartile = 0

    def report(self):
        #get all the keys available in the list of dicts
        merge = {}
        for r in self.records:
            merge.update(r)
        keys = merge.keys()
        keys.sort()

        #load the html template
        f = open('./report/book.templ','r')
        template = f.read()
        f.close()

        account_value = float(self.usds) + float(self.btcs) * float(self.btc_price)
        info = "Last Report Update: %s <br> Current Market Price: $%.3f  || Total Account Value: $%.4f || "%(ctime(),self.btc_price, account_value)
        info += "Holdings:  BTC: %.3f  USD: $%.3f<br>"%(float(self.btcs), float(self.usds))
        info += "Funds Committed: $%.3f || Funds Available: $%.3f<br>"%(self.balance_committed, self.usds - self.balance_committed)

        #dump the records into a table structure
        if len(self.records) > 0:
            export = sorted(self.records, key=itemgetter('priority'),reverse=True)

            output = '<table border="1" id="dtable" class="imgtbl">\n'
            #write the header
            output += '\t<thead>><tr>\n'
            for key in keys:
                output +='\t\t<th>\n'
                output +='\t\t\t'+key + '\n'
                output +='\t\t</th>\n'
            output +='\t</tr></thead><tbody>\n'

            #write the row records
            count = 0
            for r in export:
                count += 1
                if (r['book'].find('buy_cancel:max_wait') == -1):
                    if count%2 == 1:
                        output +='\t<tr>\n'
                    else:
                        output +='\t<tr class="odd">\n'
                    for key in keys:
                        s = ""
                        if key == 'localtime':
                            s = str(ctime(r[key]))
                        if key == 'type':
                            if r[key] == 1:
                                s = 'ask'
                            if r[key] == 2:
                                s = 'bid'

                        try:
                            if s == "" and type(1.0) == type(r[key]):
                                s = "%.8f"%r[key]
                        except:
                            s = '-' #key doesn't exist for this record
                        else:
                            if s == "":
                                s = str(r[key])
                        if key == 'book':
                            if r[key] == 'open':
                                output +='\t\t<td class="y">\n'
                            elif r[key] == 'held':
                                output +='\t\t<td class="o">\n'
                            elif r[key] == 'sold':
                                output +='\t\t<td class="g">\n'
                            elif r[key] == 'closed:commit':
                                output +='\t\t<td class="b">\n'
                            else:
                                output +='\t\t<td>\n'
                        else:
                            output +='\t\t<td>\n'
                        output +='\t\t\t'+ s + '\n'
                        output +='\t\t</td>\n'
                    output +='\t</tr>\n'
            output +='</tbody></table>\n'
        else:
            output = "No records to report."

        template = template.replace('{ORDER_TABLE}',output)
        template = template.replace('{INFO}',info)
        f = open('./report/book.html','w')
        f.write(template)
        f.close()
        return

    def get_info(self):
        while 1:
            try:
                self.client_info = self.client.get_info()
                self.client_commission = float(self.client_info['Trade_Fee'])
                return self.client_info
            except:
                print "get_info: client error..retrying @ " + ctime()


    def get_price(self):
        while 1:
            try:
                self.btc_price = self.client.get_ticker()['last']
                return self.btc_price
            except:
                print "get_price: client error..retrying @ " + ctime()

    def load_orders(self):
        while 1:
            try:
                self.orders = self.client.get_orders()['orders']
                return
            except:
                print "load_orders: client error..retrying @ " + ctime()

    def load_records(self):
        #load records from local file
        try:
            f = open("./report/bookie_records.pkl",'r')
            pd = f.read()
            f.close()
            self.records = pickle.loads(pd)
        except:
            print "load_records: no records to load"
        self.record_synch()

    def save_records(self):
        #save records to local file
        f = open("./report/bookie_records.pkl",'w')
        f.write(pickle.dumps(self.records))
        f.close()

    def add_record(self,record):
        self.records.append(record)
        self.save_records()

    def get_last_order(self):
        #the last order will be the one with the largest date stamp
        self.load_orders()
        max_date = 0
        last_order = self.orders[0]
        for o in self.orders:
            if o['date'] > last_order['date']:
                last_order = o
        return last_order

    def find_order(self,qty,price):
        self.load_orders()
        for o in self.orders:
            if str(o['amount']) == str(qty):
                if str(o['price']) == str(price):
                    return o
        return None

    def find_buy_order_by_price(self,price):
        self.load_orders()
        for o in self.orders:
            if str(o['type']) == 2:
                if str(o['price']) == str(price):
                    return o
        return None

    def funds(self):
        while 1:
            try:
                self.balance = self.client.get_balance()
                self.usds = float(self.balance['usds'])
                self.btcs = float(self.balance['btcs'])
                return self.usds
            except:
                print "funds: client error..retrying @ " + ctime()

    def sell(self, amount, price,parent_oid = "none"):
        price = float("%.8f"%price)
        print "sell: selling position: qty,price: ",amount,price
        if price < self.btc_price:
            price = self.btc_price - 0.01
            print "sell: price adjustment: qty,price: ",amount,price

        retry = 5
        while retry > 0:
            retry -= 1
            try:
                order = self.client.sell_btc(amount, price)
                order.update({'commission':self.client_commission,'parent_oid':parent_oid,'localtime':time(),'pending_counter':10,'book':'open','commit':price,'target':price,'stop':price,'max_wait':999999,'max_hold':999999})
            except:
                print "sell: client error..retrying @ " + ctime()
            else:
                self.add_record(order)
                return
        print "sell: client error..max retry reached @ " + ctime()

    def validate_buy(self,buy_price,target_price):
        if (buy_price * 1.00013) >= target_price:
            print "validate_buy: target too low %.2f, order (%.2f) not submitted",target_price,buy_price
            return False
        for r in self.records:
            if r.has_key('book'):
                if r['book'] == 'open':
                    if str(r['price']) == str(buy_price):
                        return False
        return True

    def buy(self,qty,buy_price,commit_price,target_price,stop_loss,max_wait,max_hold):
        buy_price = float(price_format%buy_price)
        target_price = float(price_format%target_price)
        commit_price = float(price_format%commit_price)

        if commit_price > target_price:
            print "buy: order validation failed, commit price higher than target"
            return False

        #verify that the order doesn't already exist at the price point
        if self.validate_buy(buy_price,target_price) == False:
            dupe_order = self.find_buy_order_by_price(buy_price)
            if dupe_order == None:
                print "buy: order validation failed @ $%.2f , target ($%.2f) too low)"%(buy_price,target_price)
            else:
                print "buy: order validation failed @ $%.2f , target ($%.2f) duplicate order)"%(buy_price,target_price)
            return False
        else:
            print "buy: order validated"

        #check available funds
        cost = qty * buy_price
        if (self.funds() - self.balance_committed) > cost and qty >= 0.01:
            last_btc_balance = self.btcs #used for verifying off book orders
            #make sure the order is lower than the current price
            if buy_price > self.btc_price:
                buy_price = self.btc_price - 0.02

            while 1:
                try:
                    order = self.client.buy_btc(qty,buy_price)
                    break
                except:
                    print "buy: client error..retrying @ " + ctime()

            if order == None:
                print 'buy: first level order verification failed'
                order = self.find_order(qty,buy_price)

            if order == None:
                print 'buy: second level order verification failed'
                self.funds()
                if self.btcs > last_btc_balance:
                    print 'buy: instant order verified'
                    order = {'commission':self.client_commission,'parent_oid':'none','price':buy_price,'oid':'none','localtime':time(),'pending_counter':10,'book':'held','commit':commit_price,'target':target_price,'stop':stop_loss,'max_wait':max_wait,'max_hold':max_hold}
                else:
                    print 'buy: third level order verification failed'
                    order = {'commission':self.client_commission,'parent_oid':'none','price':buy_price,'oid':'none','localtime':time(),'pending_counter':10,'book':'closed: order not acknowledged','commit':commit_price,'target':target_price,'stop':stop_loss,'max_wait':max_wait,'max_hold':max_hold}
                self.add_record(order)
                #print 'buy: posting instant order for sale @ target (off book)'
                #self.sell(qty, target_price)


            elif order['status'] == 2 and order['real_status'] != 'pending':
                self.cancel_buy_order(order['oid'])
                print 'buy: insuf funds'
                order.update({'commission':self.client_commission,'parent_oid':'none','localtime':time(),'pending_counter':10,'book':'closed:insuf','commit':commit_price,'target':target_price,'stop':stop_loss,'max_wait':max_wait,'max_hold':max_hold})
                self.add_record(order)
                return False
            else:
                order.update({'commission':self.client_commission,'parent_oid':'none','localtime':time(),'pending_counter':10,'book':'open','commit':commit_price,'target':target_price,'stop':stop_loss,'max_wait':max_wait,'max_hold':max_hold})
                self.add_record(order)
                print "buy: order confirmed : %s BTC @ $%s"%(str(order['amount']),str(order['price']))
                return True

        else:
            print "buy: lack of funds or min qty not met, order not submitted:"
            print "\tqty",qty
            print "\tcost",cost
            print "\tfunds",self.usds
            return False

    def cancel_buy_order(self,oid):
        print "cancel_buy_order: canceling"
        while 1:
            try:
                self.client.cancel_buy_order(oid)
                self.save_records()
                return
            except:
                print "cancel_buy_order: client error..retrying @ " + ctime()

    def record_synch(self):
        #find out which orders have been filled
        #tag buy orders as held
        #tag sell orders as sold
        self.load_orders()
        print "-"*80
        #print "record_synch: synching records:"
        for r in self.records:
            if r['book'].find("open") >= 0:
                found = 0
                #print "record_synch: searching for OID:",r['oid']
                for o in self.orders:
                    if o['oid'] == r['oid']:
                        found = 1
                        print "\trecord_synch: OID:",r['oid'], " active"
                        #update with the current order status
                        r['status'] = o['status']
                        r['real_status'] = o['real_status']
                        r.update({'amount_remaining':o['amount']})

                if found == 0:
                    print "\trecord_synch: OID:",r['oid'], " not active"
                    if r['type'] == 1:
                        #the order was filled
                        r['book'] = "sold"
                        r.update({'trade_id': ",".join(self.client.get_ask_tids(r['oid']))})
                        print "\t\trecord_synch: OID:",r['oid'], " tag as sold"
                        if self.__enable_text_messaging==True:
                            msg = 'Sold %sBTC @ $%s\n'%(str(r['amount']),str(r['target']))
                            msg += 'Account Balance: (%sBTC , $%s) Total Value: $%s'%(str(self.btcs),str(self.usds),str(float(self.usds) + float(self.btcs) * float(self.btc_price)))
                            self.aws_client.send(msg)
                    if r['type'] == 2:
                        r.update({'trade_id': ",".join(self.client.get_bid_tids(r['oid']))})
                        if len(r['trade_id']) > 0:
                            #the order was filled
                            r['book'] = "held"
                            print "\t\trecord_synch: OID:",r['oid'], " tag as held"
                            if self.__enable_text_messaging==True:
                                msg = 'Bought %sBTC @ $%s'%(str(r['amount']),str(r['price']))
                                msg += 'Account Balance: (%sBTC , $%s) Total Value: $%s'%(str(self.btcs),str(self.usds),str(float(self.usds) + float(self.btcs) * float(self.btc_price)))
                                self.aws_client.send(msg)
                        #these last two states should never be reached:
                        elif r['status'] == 2 and r['real_status'] == "pending":
                            print "\t\trecord_synch: OID:",r['oid'], " remaining open (real_status:pending)"
                        else:
                            r['book'] = "error: insuf funds"
                            print "\t\trecord_synch: OID:",r['oid'], " tag as error: insuf funds"

        #print "record_synch: error check:"
        error_found = 0
        for o in self.orders:
            order_found = 0
            for r in self.records:
                if o['oid'] == r['oid']:
                    order_found = 1
                    if r['book'] != "open":
                        error_found = 1
                        print "\trecord_synch: record error found, canceling order"
                        self.cancel_buy_order(r['oid'])
                        r['book'] += ": error"
            if order_found == 0:
                print "!!!!!!! record_synch: orphaned or manual order found:","TYPE:",o['type'],"AMOUNT:",o['amount'],"PRICE:",o['price']

        if error_found > 0:
            print "record_synch: order error(s) found and canceled"

        self.save_records()



    def update(self):
        #periodicaly call this function to process open orders
        # -automates sells,stop loss, etc...
        #print "update: checking positions"
        current_price = self.get_price()
        account_value = float(self.usds) + float(self.btcs) * current_price
        print "update: current price: %.3f  account market value: %.4f @ %s"%(current_price, account_value, ctime())

        self.get_info() #get_info updates the commision rate
        #first synch the local records...
        self.record_synch()
        self.balance_committed = 0
        print "-" * 80
        print "checking open orders"
        print "-" * 80
        for r in self.records:
            #check open orders first...
            if r['book'] == "open":
                if r['type'] == 1: #sell
                    print "\tupdate: OID:",r['oid'], " sell order active"
                    pass    #sell orders stand until completed.
                elif r['type'] == 2: #buy
                    self.balance_committed += float(r['price']) * float(r['amount'])
                    dt = time() - r['localtime']
                    print "\tupdate: OID:",r['oid'], " buy order active @",r['price']," - time left (seconds):","%.0f"%(r['max_wait'] - dt)
                    #kill any buy orders where there are not enough funds
                    if r['status'] == 2 and r['real_status'] == "pending":
                        r['pending_counter'] -= 1
                        if r['pending_counter'] == 0:
                            print "\t\tupdate: canceling pending order (insuf funds?) (OID):",r['oid']
                            self.cancel_buy_order(r['oid'])
                            r['book'] = "buy_cancel: pending state (insuf funds?)"
                    elif r['status'] == 1 and r['real_status'] == "pending":
                        #update the 'real status' - pending order has gone active
                        r['real_status'] = "open"
                    elif r['status'] == 2:
                        print "\t\tupdate: canceling order due to a lack of funds (OID):",r['oid']
                        self.cancel_buy_order(r['oid'])
                        r['book'] = "buy_cancel:insuf funds"
                    elif dt > r['max_wait']:
                        print "\t\tupdate: canceling order due to timeout (OID):",r['oid']
                        self.cancel_buy_order(r['oid'])
                        self.balance_committed -= float(r['price']) * float(r['amount'])
                        #after the order is canceled check to make sure there was no partial order fill
                        r.update({'trade_id': ",".join(self.client.get_bid_tids(r['oid']))})
                        if len(r['trade_id']) > 0:
                            #The order was partialy or completly filled , adjust the amount
                            #and leave the order in the open state...the next update will
                            #detect a filled order and the 'round trip' will continue.
                            try:
                                history = self.client.get_bid_history(r['oid'])
                            except:
                                pass #this state should never happen
                            else:
                                total_amount = history['return']['total_amount']['value']
                                #only need to adjust the amount. leave the order in an open state
                                print "\t\tupdate: detected partial order fill, will enter held state with adjusted amount (OID):",r['oid']
                                r['amount'] = total_amount
                        else:
                            r['book'] = "buy_cancel:max_wait"

        print "-" * 80
        print "checking held positions"
        print "-" * 80
        for r in self.records:
            #check held positions
            put_for_sale = 0
            if r['book'] == "held":
                dt = time() - r['localtime']
                #check commit price
                if current_price >= r['commit']:
                    print "\t+++ update: selling position: price commit target met: (OID):",r['oid']
                    self.sell(float(r['amount']) - (float(r['amount']) * (r['commission'] / 100.0)),r['target'],parent_oid = r['oid'])
                    r['book'] = "closed:commit"
                    put_for_sale = 1
                #check max age
                elif dt > r['max_hold'] and put_for_sale == 0:
                    #dump the position
                    print "\t-+- update: selling position: target timeout: (OID):",r['oid']
                    self.sell(float(r['amount']) - (float(r['amount']) * (r['commission'] / 100.0)),current_price - 0.001,parent_oid = r['oid'])
                    r['book'] = "closed:max_hold"
                    put_for_sale = 1
                #check stop loss
                elif current_price <= r['stop'] and put_for_sale == 0:
                    if self.__enable_flash_crash_protection == True: #and self.active_quartile == 4:
                        print "\t--- update: flash crash protection triggered: (OID):",r['oid']
                        r['stop'] = 0.0
                        r['max_hold'] = (time() - r['localtime']) + self.__flash_crash_protection_delay
                    else:
                        print "\t--- update: selling position: stop loss: (OID):",r['oid']
                        self.sell(float(r['amount']) - (float(r['amount']) * (r['commission'] / 100.0)),current_price - 0.001,parent_oid = r['oid'])
                        r['book'] = "closed:stop"
                        put_for_sale = 1
                elif put_for_sale == 0:
                    oid = r['oid']
                    time_left = str(int((r['max_hold'] - dt)/60.0))
                    stop_delta = "%.2f"%(current_price - r['stop'])
                    delta_target = "%.2f"%(r['target'] - current_price)
                    print "update: sell order OID:%s time left: %s stop_delta: %s delta_target: %s"%(oid,time_left,stop_delta,delta_target)

        #save the updated records
        self.save_records()
        #return the account balance
        self.funds()
        return self.usds,self.btcs




if __name__ == "__main__":
    import __main__
    from load_config import *

    #the variable values below are superceded by the configuration loaded from the
    #configuration file global_config.json
    #!!!!!!!! to change the values edit the json configuration file NOT the variables below !!!!!!!!
    monitor_mode = False
    bid_counter = 0
    bid_counter_trip = 1
    order_qty = 0.5
    commit_pct_to_target = 0.8
    sleep_state_seconds = 60
    buy_order_wait = 90 #seconds
    min_bid_price = 1.0
    max_bid_price = 20.00
    enable_flash_crash_protection = False
    flash_crash_protection_delay = 60 * 3 #three hours
    enable_underbids = True
    enable_text_messaging = False
    price_format = "%.3f"
    enable_constant_bid = 0
    constant_bid_discount = 0.20
    constant_bid_qty = 0.1
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

    print "Note: The Amazon SNS text messaging service can be enabled/disabled by modifying the bcbookie_main.json configuration file"

    b = bookie(enable_text_messaging=enable_text_messaging,enable_flash_crash_protection=enable_flash_crash_protection,flash_crash_protection_delay=flash_crash_protection_delay)


    print "main: generating inital report"
    b.report()

    print "main: entering main loop"
    while 1:

        print "_"*80
        print "main: Availble Funds (USDS,BTCS) :" + str(b.update())

        #get info from the gene_server
        t = {}
        try:

            #register as a default client (this will allow remote dynamic configuration of the report generation)
            pid = "BCBOOKIE"
            #gdh = json.loads(server.get_default_gene_def_hash())
            #print "using gene_def_hash",gdh
            #server.pid_register_client(pid,gdh)

            #get the current quartile
            #b.active_quartile = server.get_active_quartile(pid)
            #t = json.loads(server.get_target(pid))
            print "scanning for active bids by priority"
            sdbl = json.loads(server.get_db_stripped())
            target_list = []
            for key in sdbl.keys():
                if 1 == sdbl[key]['trade_enabled']:
                    target_list.append(sdbl[key])
            target_list = sorted(target_list, key=itemgetter('trade_priority'),reverse = False)

            for item in target_list:
                t = json.loads(item['g_trgt'])
                try:
                    target_discount = ((b.btc_price - t['buy'])/b.btc_price)
                except:
                    target_discount = 1.0
                print item['gene_def_hash'],'priority:',item['trade_priority'],'enabled:',item['trade_enabled'],"target:","$"+str(t['buy']),"discount:",target_discount * 100
                if target_discount <= 0.05 or b.btc_price < t['buy']:
                    print "active bid received"
                    break
        except:
            print "error: gene_server connection issue"

        bid_counter += 1
        if bid_counter == bid_counter_trip:
            bid_counter = 0
            "main: Submitting GA Order: "

            #bug fix for issue #12 - verify target order returned from gene server
            target_order_validated = False
            if t.has_key('target') and t.has_key('buy') and t.has_key('stop') and t.has_key('stop_age'):
                if type(t['target']) == float and type(t['buy']) == float:
                    if type(t['stop']) == float and (type(t['stop_age']) == int or type(t['stop_age']) == float):
                        #patch to cover for a bug in genetic where ints were being generated as floats
                        #the type cast is so user databases don't get broken.
                        #this is temporary, the db's will self heal over time -- need to verify before removing.
                        t['stop_age'] = int(t['stop_age'])
                        target_order_validated = True
                    else:
                        print "main: warning - ignoring invalid target order:"
                        print str(t)
            else:
                print "main: warning - ignoring invalid target order:"
                print str(t)

            if monitor_mode == False and enable_constant_bid == True and b.btc_price > 0.0:# and target_order_validated == False:
                #If there are no bids AND enable constant bid is true then place an order at the constant bid discount
                b.buy(constant_bid_qty,b.btc_price * ( 1 - constant_bid_discount),b.btc_price * ( 1 - (constant_bid_discount / 1.4)),b.btc_price * ( 1 - (constant_bid_discount / 1.4)),b.btc_price * ( 1 - (constant_bid_discount * 2)),buy_order_wait,7000)

            if monitor_mode == False and target_order_validated == True:
                commit = ((t['target'] - t['buy']) * commit_pct_to_target) + t['buy'] #commit sell order at n% to target
                if t['buy'] > min_bid_price and t['buy'] < max_bid_price:
                    order_initiated = True
                    #buy(qty,buy_price,commit_price,target_price,stop_loss_price,max_wait,max_hold)
                    b.buy(order_qty,t['buy'],commit,t['target'],t['stop'],buy_order_wait,t['stop_age'])
                    if enable_underbids == True:
                        #maintain underbid orders
                        #calc stop %
                        stop_pct = (t['stop'] / t['buy'])
                        u_bids = 10
                        for u_bid in range(2,u_bids,2):
                            bid_modifier = 1 - (u_bid/250.0)
                            buy_price = t['buy'] * bid_modifier
                            stop_price = buy_price * stop_pct
                            b.buy(order_qty * u_bid,buy_price,commit,t['target'],stop_price,buy_order_wait,t['stop_age'])
                else:
                    print "main: No GA order available."
            else:
                print "main: monitor mode or target order not validated."
        #update the report
        b.report()
        print "sleeping..."
        print "_"*80
        print "\n\n"
        sleep(sleep_state_seconds)
