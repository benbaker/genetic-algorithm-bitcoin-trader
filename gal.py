
"""
gal v0.01

ga-bitbot application / system launcher

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

__appversion__ = "0.01a"
print "ga-bitbot application system launcher v%s"%__appversion__

import atexit
import sys
from subprocess import check_output as call, Popen, PIPE
import shlex
from os import environ
import os
from time import *
import hashlib
import random
import __main__
import paths
from load_config import *
import gene_server_config
import xmlrpclib
import json
import gc

def make_pid():
    #simple function which spits out a random hex code
    #which are used to set globaly unique process ids to spawned clients
    md = hashlib.md5()
    md.update(str(time()) + str(random.random() * 1000000))
    return md.hexdigest()[0:16]


print "-"*80
print "\n\tCommand line options:\n\t\tserver\t\tlaunches only the server components\n\t\tclient\t\tlaunches only the client components\n\t\tall\t\tlaunches all components"
print "\n\tThe default configuration is 'all'"
print "-"*80

run_client = 1
run_server = 1
mode = ""
if len(sys.argv) >= 2:
    if sys.argv[1] == 'all':
        mode = 'all'
        run_client = 1
        run_server = 1
        print "gal: launching all components"
    if sys.argv[1] == 'client':
        mode = 'client'
        run_client = 1
        run_server = 0
        print "gal: launching client components only"
    if sys.argv[1] == 'xlclient':
        mode = 'xlclient'
        run_client = 1
        run_server = 0
        print "gal: launching xlclient components only"
    if sys.argv[1] == 'server':
        mode = 'server'
        run_client = 0
        run_server = 1
        print "gal: launching server components only"
else:
    mode = 'all'
    print "gal: launching all components"
    sleep(3)

#the variable values below are superceded by the configuration loaded from the
#configuration file global_config.json
#!!!!!!!! to change the values edit the json configuration file NOT the variables below !!!!!!!!
WATCHDOG_TIMEOUT = 60 #seconds
MONITORED_PROCESS_LAUNCH_TIMEOUT = 20 #seconds
GENE_SERVER_STDERR_FILE = "/dev/null"
BCFEED_STDERR_FILE = "/dev/null"
WC_SERVER_STDERR_FILE = "/dev/null"
REPORT_GEN_STDERR_FILE = "/dev/null"
GTS_STDERR_FILE = "/dev/null"
config_loaded = False
#load config
try:
    __main__ = load_config_file_into_object('global_config.json',__main__)
except:
    print "gal: Error detected while loading the configuration. The application will now exit."
    import sys
    sys.exit()
else:
    if config_loaded == False:
        print "gal: Configuration failed to load. The application will now exit."
        import sys
        sys.exit()
    else:
        print "gal: Configuration loaded."

#open a null file to redirect stdout/stderr from the launched subprocesses
fnull = open(os.devnull,'w')

if GENE_SERVER_STDERR_FILE == "/dev/null":
    GENE_SERVER_STDERR_FILE = fnull
else:
    GENE_SERVER_STDERR_FILE = open(GENE_SERVER_STDERR_FILE,'a')

if BCFEED_STDERR_FILE == "/dev/null":
    BCFEED_STDERR_FILE = fnull
else:
    BCFEED_STDERR_FILE = open(BCFEED_STDERR_FILE,'a')

if WC_SERVER_STDERR_FILE == "/dev/null":
    WC_SERVER_STDERR_FILE = fnull
else:
    WC_SERVER_STDERR_FILE = open(WC_SERVER_STDERR_FILE,'a')

if REPORT_GEN_STDERR_FILE == "/dev/null":
    REPORT_GEN_STDERR_FILE = fnull
else:
    REPORT_GEN_STDERR_FILE = open(REPORT_GEN_STDERR_FILE,'a')

if GTS_STDERR_FILE == "/dev/null":
    GTS_STDERR_FILE = fnull
else:
    GTS_STDERR_FILE = open(GTS_STDERR_FILE,'a')

#configure gts clients based on the mode of operation (all,server or client)
#
# all - balanced
# server - focused on updating scores
# client - focused on finding new genes
#
# At least one gts instance in each mode should not run with the get_config option
# to make sure any new gene_def.json configs get loaded into the db.
#

all_monitored_launch = ['pypy gts.py all n run_once pid ',\
'pypy gts.py 3 n run_once get_config pid ',\
'pypy gts.py 3 y run_once get_config pid ',\
'pypy gts.py 4 n run_once get_config pid ',\
'pypy gts.py 4 y run_once get_config pid ',\
'pypy gts.py all y run_once get_config score_only pid ',\
'pypy gts.py all y run_once get_config pid ']


server_monitored_launch = ['pypy gts.py all y run_once pid ',\
'pypy gts.py 1 y run_once get_config score_only pid ',\
'pypy gts.py 2 y run_once get_config score_only pid ',\
'pypy gts.py 3 y run_once get_config score_only pid ',\
'pypy gts.py 3 y run_once get_config score_only pid ',\
'pypy gts.py 4 y run_once get_config score_only pid ',\
'pypy gts.py 4 y run_once get_config score_only pid ']


client_monitored_launch = ['pypy gts.py all n run_once pid ',\
'pypy gts.py 1 n run_once get_config pid ',\
'pypy gts.py 2 n run_once get_config pid ',\
'pypy gts.py 3 n run_once get_config pid ',\
'pypy gts.py 3 y run_once get_config pid ',\
'pypy gts.py 4 n run_once get_config pid ',\
'pypy gts.py 4 y run_once get_config pid ',\
'pypy gts.py all y run_once get_config pid ']

xlclient_monitored_launch = ['pypy gts.py all n run_once pid ',\
'pypy gts.py 1 n run_once get_config pid ',\
'pypy gts.py 2 n run_once get_config pid ',\
'pypy gts.py 3 n run_once get_config pid ',\
'pypy gts.py 3 n run_once get_config pid ',\
'pypy gts.py 4 n run_once get_config pid ',\
'pypy gts.py 4 n run_once get_config pid ',\
'pypy gts.py 3 y run_once get_config pid ',\
'pypy gts.py 3 y run_once get_config pid ',\
'pypy gts.py 4 y run_once get_config pid ',\
'pypy gts.py 4 y run_once get_config pid ',\
'pypy gts.py 1 n run_once get_config pid ',\
'pypy gts.py 2 n run_once get_config pid ',\
'pypy gts.py 3 n run_once get_config pid ',\
'pypy gts.py 3 n run_once get_config pid ',\
'pypy gts.py 4 n run_once get_config pid ',\
'pypy gts.py 4 n run_once get_config pid ',\
'pypy gts.py 3 y run_once get_config pid ',\
'pypy gts.py 3 y run_once get_config pid ',\
'pypy gts.py 4 y run_once get_config pid ',\
'pypy gts.py 4 y run_once get_config pid ',\
'pypy gts.py all y run_once get_config pid ']



if mode == 'all':
    monitored_launch = all_monitored_launch
if mode == 'server':
    monitored_launch = server_monitored_launch
if mode == 'client':
    monitored_launch = client_monitored_launch
if mode == 'xlclient':
    monitored_launch = xlclient_monitored_launch



unmonitored_launch = ['pypy wc_server.py','pypy report_gen.py']

monitor = {}    #variables to track monitored/unmonitored processes
no_monitor = []

def terminate_process(process):
    if sys.platform == 'win32':
        import ctypes
        PROCESS_TERMINATE = 1
        pid = process.pid
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
        ctypes.windll.kernel32.TerminateProcess(handle, -1)
        ctypes.windll.kernel32.CloseHandle(handle)
    else:
        if process.poll() == None:
            process.terminate()
            process.wait()

# create and register callback function to do a clean shutdown of the system on exit.
def shutdown():
    global monitor
    global no_monitor
    global run_server

    for p in no_monitor:
        terminate_process(p)

    for pid in monitor.keys():
        terminate_process(monitor[pid]['process'])
    sys.stderr = fnull
    if run_server:
        server.shutdown()

atexit.register(shutdown)


#capture the price feeds regardless of client or server mode
#servers need it for reporting and clients need it for processing

#update the dataset
print "gal: Synching the local datafeed..."
Popen(shlex.split('python bcfeed_synch.py -d')).wait()

#launch the bcfeed script to collect data from the live feed
print "gal: Starting the live datafeed capture script..."
p = Popen(shlex.split('python bcfeed.py'),stdin=fnull, stdout=fnull, stderr=BCFEED_STDERR_FILE)
no_monitor.append(p)

if run_server:
    print "gal: Launching the xmlrpc server..."
    Popen(shlex.split('pypy gene_server.py'),stdin=fnull, stdout=fnull, stderr=GENE_SERVER_STDERR_FILE)
    sleep(5) #give the server time to start


# connect to the xml server
#
__server__ = gene_server_config.__server__
__port__ = str(gene_server_config.__port__)
server = xmlrpclib.Server('http://' + __server__ + ":" + __port__)
print "gal: connected to gene server ",__server__,":",__port__


if mode == 'all' or mode == 'server':
    print "gal: gene server db restore: ",server.reload()


print "gal: Launching GA Clients..."

#collect system process PIDS for monitoring.
#(not the same as system OS PIDs -- They are more like GUIDs as this is a multiclient distributed system)
epl = json.loads(server.pid_list()) #get the existing pid list

#start the monitored processes
for cmd_line in monitored_launch:
    new_pid = make_pid()
    p = Popen(shlex.split(cmd_line + new_pid),stdin=fnull, stdout=fnull, stderr=GTS_STDERR_FILE)
    retry = MONITORED_PROCESS_LAUNCH_TIMEOUT
    while retry > 0:
        sleep(1)
        cpl = json.loads(server.pid_list()) #get the current pid list
        npl = list(set(epl) ^ set(cpl))     #find the new pid(s)
        epl = cpl               #update the existing pid list
        if new_pid in npl:
            monitor.update({new_pid:{'cmd':cmd_line,'process':p}})  #store the pid/cmd_line/process
            print "gal: Monitored Process Launched (PID:",new_pid,"CMD:",cmd_line,")"
            break
        else:
            retry -= 1
    if retry == 0:
        print "gal: ERROR: Monitored Process Failed to Launch","(CMD:",cmd_line,")"

if run_server:
    #start unmonitored processes
    for cmd_line in unmonitored_launch:
        p = Popen(shlex.split(cmd_line),stdin=fnull, stdout=fnull, stderr=fnull)
        print "gal: Unmonitored Process Launched (CMD:",cmd_line,")"
        no_monitor.append(p)    #store the popen instance
        sleep(1) #wait a while before starting the report_gen script


print "\ngal: Monitoring Processes..."
count = 0
while 1:
    gc.collect()
    if run_server:
        count += 1
        #periodicaly tell the server to save the gene db
        if count == 50:
            count = 0
            server.save()
        if run_client == 0:
            sleep(30)

    #process monitor loop
    for pid in monitor.keys():
        sleep(5) #check one pid every n seconds.
        if server.pid_check(pid,WATCHDOG_TIMEOUT) == "NOK":
            #watchdog timed out
            print "gal: WATCHDOG: PID",pid,"EXPIRED"
            #remove the expired PID
            server.pid_remove(pid)
            epl = json.loads(server.pid_list()) #get the current pid list
            cmd_line = monitor[pid]['cmd']
            #terminate the process
            terminate_process(monitor[pid]['process'])
            monitor.pop(pid)
            #launch new process
            launching = 1
            while launching == 1:
                new_pid = make_pid()
                p = Popen(shlex.split(cmd_line + new_pid),stdin=fnull, stdout=fnull, stderr=GTS_STDERR_FILE)
                retry = MONITORED_PROCESS_LAUNCH_TIMEOUT
                while retry > 0:
                    sleep(1)
                    cpl = json.loads(server.pid_list()) #get the current pid list
                    npl = list(set(epl) ^ set(cpl))     #find the new pid(s)
                    epl = cpl               #update the existing pid list
                    if new_pid in npl:
                        monitor.update({new_pid:{'cmd':cmd_line,'process':p}})  #store the pid/cmd_line/process
                        print "gal: Monitored Process Launched (PID:",new_pid,"CMD:",cmd_line,")"
                        launching = 0
                        break
                    else:
                        retry -= 1
                if retry == 0:
                    print "gal: ERROR: Monitored Process Failed to Launch","(CMD:",cmd_line,")"

fnull.close()
