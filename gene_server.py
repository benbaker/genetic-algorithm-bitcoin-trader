#!/usr/bin/python

"""
gene_server v0.01 

- a xmlrpc server providing a storage/query service for the GA trade system

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
#   gene server
#   - a xmlrpc server providing a storage/query/configuration/monitoring service for the GA trade system
#

import gene_server_config
__server__ = gene_server_config.__server__
__port__ = gene_server_config.__port__
__path__ = "/gene"




import sys
import time
import json
import hashlib
import socket
import SocketServer
from SimpleXMLRPCServer import SimpleXMLRPCServer
from SimpleXMLRPCServer import SimpleXMLRPCRequestHandler
from operator import itemgetter, attrgetter
from copy import deepcopy
import threading
from Queue import Queue
import gc

import paths
import call_metrics

quit = 0
MAX_PID_MESSAGE_BUFFER_SIZE = 255
AUTO_BACKUP_AFTER_N_SAVES = 60
max_len = 600
max_bobs = 1000

# The default group is set by the first client connection.
g_default_group_set = False
g_undefined_gene_def_hash = '0db45d2a4141101bdfe48e3314cfbca3' #precalculated md5 hash of the UNDEFINED gene_def config.
g_default_group_gene_def_hash = g_undefined_gene_def_hash

g_gene_conf = {'gene_def_hash':g_undefined_gene_def_hash,'gene_def':'UNDEFINED','gene_high_scores':[[],[],[],[]],'gene_best':[[],[],[],[]],'g_trgt':json.dumps({'buy':0}),'g_active_quartile':0,'trade_enabled':0,'trade_priority':0}
g_gene_library = {'0db45d2a4141101bdfe48e3314cfbca3':deepcopy(g_gene_conf)} #default library starts with the default UNDEFINED group.
g_signed_package_library = {} 

g_save_counter = 0
g_trgt = json.dumps({'buy':0})
g_active_quartile = 0
g_d = [[],[],[],[]] #default group high scores - quartiles 1-4
g_bobs = [[],[],[],[]]  #default group best of the best - quartiles 1-4
g_pids = {}

def echo(msg):
    return msg

@call_metrics.call_metrics
def put_signed_package(package):
    global g_signed_package_library
    try:
        package = json.loads(package)
    except:
        return "NOK"
    g_signed_package_library.update({package['package_name']:package})
    return "OK"


@call_metrics.call_metrics
def get_signed_package(package_name):
    global g_signed_package_library
    if g_signed_package_library.has_key(package_name):
        return json.dumps(g_signed_package_library[package_name])
    return "NOK"


@call_metrics.call_metrics
def check_signed_package(package_name,MD5):
    """
    used by clients to check that local packages 
    are in synch with the signed package library
    """
    global g_signed_package_library
    if g_signed_package_library.has_key(package_name):
        if g_signed_package_library[package_name]['MD5'] == MD5:
            return "OK"
        return "NOK"
    return "NA"

@call_metrics.call_metrics
def trade_enable(state,gdh):
    """
    sets the trade_enable state
    state = 0, disable trading
    state = 1, enable trading
    """
    global g_gene_library
    try:
        state = int(state)
    except:
        return "NOK : state",state
    if not (state==1 or state==0):
        return "NOK : val"
    if not g_gene_library.has_key(gdh):
        return "NOK : gdh",gdh
    g_gene_library[gdh]['trade_enabled'] = state
    return "OK"

@call_metrics.call_metrics
def trade_priority(priority,gdh):
    """
    sets the trade priority
    priority = 0, highest priority
    .
    .
    priority = 9, lowest priority
    """
    global g_gene_library
    try:
        priority = int(priority)
    except:
        return "NOK:priority",priority
    if (priority < 0 or priority > 9):
        return "NOK:val",priority
    if not g_gene_library.has_key(gdh):
        return "NOK:gdh",gdh
    g_gene_library[gdh]['trade_priority'] = priority
    return "OK"

@call_metrics.call_metrics
def put_target(target,pid=None):
    global g_trgt
    global g_gene_library
    gdh = get_pid_gene_def_hash(pid)
    g_gene_library[gdh]['g_trgt'] = target
    return "OK"

@call_metrics.call_metrics
def get_target(pid=None):
    global g_trgt
    global g_gene_library
    gdh = get_pid_gene_def_hash(pid)
    return g_gene_library[gdh]['g_trgt']

@call_metrics.call_metrics
def put_active_quartile(quartile,pid=None):
    global g_active_quartile
    global g_gene_library
    g_active_quartile = quartile
    gdh = get_pid_gene_def_hash(pid)
    g_gene_library[gdh]['g_active_quartile'] = quartile
    if gdh == g_default_group_gene_def_hash:
        g_active_quartile = quartile
    return "OK"

@call_metrics.call_metrics
def get_active_quartile(pid=None):
    global g_active_quartile
    global g_gene_library
    gdh = get_pid_gene_def_hash(pid)
    #return g_gene_library[gdh]['g_active_quartile']
    return g_active_quartile

@call_metrics.call_metrics 
def get_gene(n_sec,quartile,pid = None):
    global g_d
    global g_bobs
    global g_gene_library
    gdh = get_pid_gene_def_hash(pid)

    t = time.time() - n_sec
    #get the highest score calculated within the last n seconds
    #or return the latest if none are found.
    r = []
    #collect the high scoring records
    for a_d in g_gene_library[gdh]['gene_high_scores'][quartile - 1]:
        if a_d['time'] > t:
            r.append(a_d)

    #collect the bob records
    for a_d in g_gene_library[gdh]['gene_best'][quartile - 1]:
        if a_d['time'] > t:
            r.append(a_d)

    #if no records found, grab the most recent
    if len(r) == 0 and len(g_gene_library[gdh]['gene_high_scores'][quartile - 1]) > 0:
        r = sorted(g_gene_library[gdh]['gene_high_scores'][quartile - 1], key=itemgetter('time'),reverse = True)[0]
        print "get",r['time'],r['score']
    elif len(r) > 1:
        #if more than one record found find the highest scoring one
        r = sorted(r, key=itemgetter('score'),reverse = True)[0]
        print "get",r['time'],r['score']
    else:
        r = {}
        
    return json.dumps(r)

@call_metrics.call_metrics
def get_all_genes(quartile,pid = None):
    global g_d
    global g_gene_library
    gdh = get_pid_gene_def_hash(pid)
    return json.dumps(sorted(g_gene_library[gdh]['gene_high_scores'][quartile - 1], key=itemgetter('score')))
    #return json.dumps(sorted(g_d[quartile - 1], key=itemgetter('score')))

@call_metrics.call_metrics
def get_bobs(quartile,pid = None):
    global g_bobs
    global g_gene_library
    gdh = get_pid_gene_def_hash(pid)
    return json.dumps(sorted(g_gene_library[gdh]['gene_best'][quartile - 1], key=itemgetter('score')))
    #return json.dumps(sorted(g_bobs[quartile - 1], key=itemgetter('score')))

@call_metrics.call_metrics
def put_gene(d,quartile,pid = None):
    global g_d
    global g_bobs
    global g_gene_library
    gdh = get_pid_gene_def_hash(pid)
    #dictionary must have two key values, time & score
    #add the record and sort the dictionary list
    d = json.loads(d)

    if any(adict['gene'] == d['gene'] for adict in g_gene_library[gdh]['gene_high_scores'][quartile - 1]):
        print "put_gene: duplicate gene detected"
        for i in xrange(len(g_gene_library[gdh]['gene_high_scores'][quartile - 1])):
            if g_gene_library[gdh]['gene_high_scores'][quartile - 1][i]['gene'] == d['gene']:
                print "put_gene: removing previous record"
                g_gene_library[gdh]['gene_high_scores'][quartile - 1].pop(i)
                break

    if d['score'] != -987654321.12346:  
        #timestamp the gene submission
        d['time'] = time.time()

        g_gene_library[gdh]['gene_high_scores'][quartile - 1].append(d)
        g_gene_library[gdh]['gene_high_scores'][quartile - 1] = sorted(g_gene_library[gdh]['gene_high_scores'][quartile - 1], key=itemgetter('score'),reverse = True)
    
        print "put",d['time'],d['score']
        #prune the dictionary list
        if len(g_gene_library[gdh]['gene_high_scores'][quartile - 1]) > max_len:
            g_gene_library[gdh]['gene_high_scores'][quartile - 1] = g_gene_library[gdh]['gene_high_scores'][quartile - 1][:max_len]

    #update the bob dict if needed.
    if any(adict['gene'] == d['gene'] for adict in g_gene_library[gdh]['gene_best'][quartile - 1]):
        print "put_gene: BOB gene detected"
        #update the gene
        put_bob(json.dumps(d),quartile,pid)


    return "OK"

@call_metrics.call_metrics
def put_gene_buffered(d_buffer,quartile,pid = None):
    for d in d_buffer:
        put_gene(d,quartile,pid)
    return "OK"

@call_metrics.call_metrics
def put_bob(d,quartile,pid = None):
    global g_bobs
    global g_gene_library
    gdh = get_pid_gene_def_hash(pid)
    #dictionary must have two key values, time & score
    #add the record and sort the dictionary list
    d = json.loads(d)

    if any(adict['gene'] == d['gene'] for adict in g_gene_library[gdh]['gene_best'][quartile - 1]):
        print "put_bob: duplicate gene detected"
        for i in xrange(len(g_gene_library[gdh]['gene_best'][quartile - 1])):
            if g_gene_library[gdh]['gene_best'][quartile - 1][i]['gene'] == d['gene']:
                print "put_bob: removing previous record"
                g_gene_library[gdh]['gene_best'][quartile - 1].pop(i)
                break

    if d['score'] != -987654321.12346:
        #timestamp the gene submission
        d['time'] = time.time()

        g_gene_library[gdh]['gene_best'][quartile - 1].append(d)
        g_gene_library[gdh]['gene_best'][quartile - 1] = sorted(g_gene_library[gdh]['gene_best'][quartile - 1], key=itemgetter('score'),reverse = True)
    
        print "put bob",d['time'],d['score']
        #prune the dictionary list
        if len(g_gene_library[gdh]['gene_best'][quartile - 1]) > max_bobs:
            g_gene_library[gdh]['gene_best'][quartile - 1] = g_gene_library[gdh]['gene_best'][quartile - 1][:max_bobs]
    return "OK"

#remote process services 
@call_metrics.call_metrics
def pid_register_gene_def(pid,gene_def):
    global g_pids
    global g_gene_library
    global g_gene_conf
    #calc the hash of gene_def
    conf_hash = hashlib.md5(gene_def).hexdigest()
    if conf_hash in g_gene_library.keys():
        #gene_def already exists
        pass
    else:
        gc = deepcopy(g_gene_conf)
        gc['gene_def_hash'] = conf_hash
        gc['gene_def'] = gene_def
        g_gene_library.update({conf_hash:gc})

    pid_register_client(pid,conf_hash)
    return conf_hash

@call_metrics.call_metrics
def pid_register_client(pid,gene_def_hash):
    global g_pids
    global g_gene_library
    global g_default_group_gene_def_hash
    global g_default_group_set
    print pid,gene_def_hash

    if gene_def_hash in g_gene_library.keys():
        #the first registered client sets the default group
        if g_default_group_set == False:
            g_default_group_set = True
            g_default_group_gene_def_hash = gene_def_hash
        pid_alive(pid)      
        g_pids[pid].update({'gene_def_hash':gene_def_hash})     
        return "OK"
    return "NOK:HASH NOT FOUND:"+gene_def_hash

@call_metrics.call_metrics
def pid_alive(pid):
    global g_pids
    global g_undefined_gene_def_hash
    global g_default_group_gene_def_hash
    global g_default_group_set
    #pid ping (watchdog reset)
    if pid in g_pids.keys(): #existing pid
        g_pids[pid]['watchdog_reset'] = time.time()
    else: #new pid
        g_pids.update({pid:{'watchdog_reset':time.time(),'msg_buffer':[],'gene_def_hash':None}})
        pid_register_gene_def(pid,"UNDEFINED") #g_undefined_gene_def_hash
        if g_default_group_set == False:
            g_default_group_set = True
            g_default_group_gene_def_hash = g_undefined_gene_def_hash
    return "OK"

@call_metrics.call_metrics
def pid_check(pid,time_out):
    global g_pids
    #check for PID watchdog timeout (seconds)
    if pid in g_pids.keys():
        dt = time.time() - g_pids[pid]['watchdog_reset']
        if dt > time_out:
            return "NOK"
        else:
            return "OK"
    else:
        return "NOK"

@call_metrics.call_metrics
def pid_remove(pid):
    global g_pids
    try:
        g_pids.pop(pid)
    except:
        pass
    return "OK"

@call_metrics.call_metrics
def pid_msg(pid,msg):
    global g_pids
    #append a message to the PID buffer
    if pid in g_pids.keys(): #existing pid
        g_pids[pid]['msg_buffer'].insert(0,msg)
        #limit the message buffer size
        if len(g_pids[pid]['msg_buffer']) > MAX_PID_MESSAGE_BUFFER_SIZE:
            g_pids[pid]['msg_buffer'] = g_pids[pid]['msg_buffer'][:-1]
        return "OK"
    else:
        return "NOK"

@call_metrics.call_metrics
def pid_list(ping_seconds=9999999):
    global g_pids
    pids = []
    for pid in g_pids.keys():
        if pid_check(pid,ping_seconds) == "OK":
            pids.append(pid)
    return json.dumps(pids)

@call_metrics.call_metrics
def get_pids():
    global g_pids
    js_pids = json.dumps(g_pids)
    #clear the message buffers
    #for pid in g_pids.keys():
    #   g_pids[pid]['msg_buffer'] = ''
    return js_pids


def get_pid_gene_def_hash(pid):
    global g_pids
    global g_undefined_gene_def_hash
    if pid == None:
        return g_undefined_gene_def_hash
    elif pid in g_pids.keys():
        return g_pids[pid]['gene_def_hash']
    else:
        return "NOK:PID_NOT_FOUND"

@call_metrics.call_metrics
def get_default_gene_def_hash():
    global g_default_group_gene_def_hash
    return json.dumps(g_default_group_gene_def_hash)

@call_metrics.call_metrics
def get_gene_def_hash_list():
    global g_gene_library
    return json.dumps(g_gene_library.keys())

@call_metrics.call_metrics
def get_gene_def(gene_def_hash):
    global g_gene_library
    if gene_def_hash in g_gene_library.keys():
        return g_gene_library[gene_def_hash]['gene_def']
    return json.dumps('NOK:NOT_FOUND')

@call_metrics.call_metrics
def set_default_gene_def_hash(gd_hash):
    global g_default_group_gene_def_hash
    if get_gene_def(gd_hash).find('NOK:') < 0:
        g_default_group_set = True
        g_default_group_gene_def_hash = gd_hash
        return json.dumps(gd_hash)

#system services
def shutdown():
    global quit
    quit = 1
    save_db()
    return 1

@call_metrics.call_metrics
def get_db():
    global g_gene_library
    return json.dumps(g_gene_library)

@call_metrics.call_metrics
def get_db_stripped():
    global g_gene_library
    #sdb = deepcopy(g_gene_library)
    #for key in sdb:
    #   sdb[key].pop('gene_def')
    #   sdb[key].pop('gene_high_scores')
    #   sdb[key].pop('gene_best')
    #return json.dumps(sdb)
    strip_list = ['gene_def','gene_high_scores','gene_best']
    sdbl = {}
    for db_key in g_gene_library:
        sdb = {}
        for item_key in g_gene_library[db_key]:
            if not item_key in strip_list:
                sdb.update({item_key:g_gene_library[db_key][item_key]})
        sdbl.update({db_key:sdb})
    return json.dumps(sdbl)

@call_metrics.call_metrics
def save_db():
    global AUTO_BACKUP_AFTER_N_SAVES
    global g_save_counter
    global g_gene_library
    global g_signed_package_library

    g_save_counter += 1
    if g_save_counter == AUTO_BACKUP_AFTER_N_SAVES:
        g_save_counter = 0
        backup = True
    else:
        backup = False

    #embed the signed package library into the gene library
    g_gene_library.update({'signed_package_library':g_signed_package_library})

    if backup:
        f = open('./config/gene_server_db_library.json.bak','w')
        f.write(json.dumps(g_gene_library))
        f.close()

    f = open('./config/gene_server_db_library.json','w')
    f.write(json.dumps(g_gene_library))
    #pop the signed package library back out of the gene library
    g_gene_library.pop('signed_package_library')
    #call the python garbage collector - improve long running process memory useage when using pypy
    gc.collect()
    return 'OK'

@call_metrics.call_metrics
def reload_db():
    global g_gene_library
    global g_signed_package_library
    import os
    reload_error = False
    #save the gene db before shut down
    print "reloading stored gene data into server..."
    
    #
    # migrate any old style db archives from old db format into the new format...delete the old files once migrated
    #   
    for quartile in [1,2,3,4]:
        try:
            f = open('./config/gene_server_db_backup_quartile' + str(quartile) + '.json','r')
            d = json.loads(f.read())
            f.close()

            for g in d['bobs']:
                put_bob(json.dumps(g),quartile)
            for g in d['high_scores']:
                put_gene(json.dumps(g),quartile)
            reload_error = True #force load the backup too
            save_db() #save using the new format
            #delete the old format files once loaded.
            os.remove('./config/gene_server_db_backup_quartile' + str(quartile) + '.json')  
        except:
            reload_error = True
    #migrate the backups too...
    if reload_error == True:
        for quartile in [1,2,3,4]:
            try:
                f = open('./config/gene_server_db_backup_quartile' + str(quartile) + '.json.bak','r')
                d = json.loads(f.read())
                f.close()

                for g in d['bobs']:
                    put_bob(json.dumps(g),quartile)
                for g in d['high_scores']:
                    put_gene(json.dumps(g),quartile)
                save_db() #save using the new format
                #delete the old format files once loaded.
                os.remove('./config/gene_server_db_backup_quartile' + str(quartile) + '.json.bak')
            except:
                reload_error = True
                pass

    #try to load new db archive format
    try:
        f = open('./config/gene_server_db_library.json','r')
        g_gene_library = json.loads(f.read())
        f.close()
        reload_error = False
    except:
        reload_error = True

    if reload_error == True:
        try:
            f = open('./config/gene_server_db_library.json.bak','r')
            g_gene_library = json.loads(f.read())
            f.close()
            reload_error = False
        except:
            reload_error = True

    if reload_error == True:
        return "NOK"

    #extract the signed code library if one's available
    if g_gene_library.has_key('signed_package_library'):
        g_signed_package_library = g_gene_library.pop('signed_package_library')

    #upgrade old db format to include new records
    for key in g_gene_library.keys():
        if g_gene_library[key].has_key('trade_enabled') == False:
            g_gene_library[key].update({'trade_enabled':0})
        if g_gene_library[key].has_key('trade_priority') == False:
            g_gene_library[key].update({'trade_priority':0})

    return "OK"


def get_gene_server_metrics():
    return json.dumps(call_metrics.get_metrics())

#set the service url
class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/gene','/RPC2')


#create the server
#the type of server is defined in gene_server_config.py
if gene_server_config.__type__ == "single_threaded":
    server = SimpleXMLRPCServer((__server__, __port__),requestHandler = RequestHandler,logRequests = False, allow_none = True)

elif gene_server_config.__type__ == "thread_pool":
    class ThreadPoolMixIn(SocketServer.ThreadingMixIn):
        def __init__(self):
            self.num_threads = gene_server_config.__poolsize__
            self.allow_reuse_address = True  #fix socket.error on server restart
            self.lock = threading.Lock()
            self.requests = Queue(self.num_threads)

            for x in range(self.num_threads):
                t = threading.Thread(target = self.process_request_thread)
                t.daemon = True
                t.start()

        def serve_forever(self):
            while True:
                self.handle_request()
            self.server_close()

        def process_request_thread(self):
            while True:
                got = self.requests.get()
                self.lock.acquire()
                SocketServer.ThreadingMixIn.process_request_thread(self, *got)
                self.lock.release()
        
        def handle_request(self):
            try:
                request, client_address = self.get_request()
            except socket.error:
                return
            if self.verify_request(request, client_address):
                self.requests.put((request, client_address))

    class AsyncXMLRPCServer(ThreadPoolMixIn,SimpleXMLRPCServer):
        def __init__(self, *args, **kwargs):
            SimpleXMLRPCServer.__init__(self, *args, **kwargs)
            ThreadPoolMixIn.__init__(self)

    #create the server
    server = AsyncXMLRPCServer((__server__, __port__),requestHandler = RequestHandler,logRequests = False, allow_none = True)

elif gene_server_config.__type__ == "threaded":
    # Threaded mix-in
    class AsyncXMLRPCServer(SocketServer.ThreadingMixIn,SimpleXMLRPCServer):
        def __init__(self, *args, **kwargs):
            SimpleXMLRPCServer.__init__(self, *args, **kwargs)
            self.lock = threading.Lock()

        def process_request_thread(self, request, client_address):
            # Blatant copy of SocketServer.ThreadingMixIn, but we need a single threaded handling of the request
            self.lock.acquire()
            try:
                self.finish_request(request, client_address)
                self.shutdown_request(request)
            except:
                self.handle_error(request, client_address)
                self.shutdown_request(request)
            finally:
                self.lock.release()

    #create the server
    server = AsyncXMLRPCServer((__server__, __port__),requestHandler = RequestHandler,logRequests = False, allow_none = True)
else:
    print "Invalid server type defined: ",gene_server_config.__type__
    sys.exit()    


#register the functions
#client services
server.register_function(put_signed_package,'put_signed_package')
server.register_function(get_signed_package,'get_signed_package')
server.register_function(check_signed_package,'check_signed_package')

server.register_function(trade_enable,'trade_enable')
server.register_function(trade_priority,'trade_priority')

server.register_function(get_target,'get_target')
server.register_function(put_target,'put_target')
server.register_function(get_active_quartile,'get_active_quartile')
server.register_function(put_active_quartile,'put_active_quartile')
server.register_function(get_gene,'get')
server.register_function(get_all_genes,'get_all')
server.register_function(put_gene,'put')

server.register_function(put_bob,'put_bob')
server.register_function(get_bobs,'get_bobs')
server.register_function(get_gene_def_hash_list,'get_gene_def_hash_list')
server.register_function(get_default_gene_def_hash,'get_default_gene_def_hash')
server.register_function(get_gene_def,'get_gene_def')
server.register_function(get_pid_gene_def_hash,'get_pid_gene_def_hash')
server.register_function(set_default_gene_def_hash,'set_default_gene_def_hash')

#process & monitoring services
server.register_function(pid_register_gene_def,'pid_register_gene_def')
server.register_function(pid_register_client,'pid_register_client')
server.register_function(pid_alive,'pid_alive')
server.register_function(pid_check,'pid_check')
server.register_function(pid_remove,'pid_remove')
server.register_function(pid_remove,'pid_exit')
server.register_function(pid_msg,'pid_msg')
server.register_function(get_pids,'get_pids')
server.register_function(pid_list,'pid_list')
#debug services
server.register_function(echo,'echo')
#system services
server.register_function(shutdown,'shutdown')
server.register_function(reload_db,'reload')
server.register_function(save_db,'save')
server.register_function(get_db,'get_db')
server.register_function(get_db_stripped,'get_db_stripped')
server.register_function(get_gene_server_metrics,'get_gene_server_metrics')

server.register_multicall_functions()
server.register_function(put_gene,'mc_put')

server.register_introspection_functions()

if __name__ == "__main__":
    print "gene_server: running "+ gene_server_config.__type__ +" server on port " + str(__port__)
    reload_db()
    while not quit:
        server.handle_request()

