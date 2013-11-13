
"""
gts v0.01

genetic test sequencer

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
import traceback
import xmlrpclib
import json
import gene_server_config
import time
import sys
import random
import subprocess
import __main__
import paths
from genetic import *
from load_config import *

random.seed(time.time())

if __name__ == "__main__":
    __appversion__ = "0.01a"
    print "Genetic Test Sequencer v%s"%__appversion__

    # connect to the xml server
    #
    __server__ = gene_server_config.__server__
    __port__ = str(gene_server_config.__port__)

    #make sure the port number matches the server.
    server = xmlrpclib.Server('http://' + __server__ + ":" + __port__)
    multicall = xmlrpclib.MultiCall(server)

    print "gts: connected to gene_server ",__server__,":",__port__


    #the variable values below are superceded by the configuration loaded from the
    #configuration file global_config.json
    #!!!!!!!! to change the values edit the json configuration file NOT the variables below !!!!!!!!
    max_length = 60 * 24 * 60
    load_throttle = 1 #go easy on cpu usage
    load_throttle_sleep_interval = 0.10#seconds
    calibrate = 1   #set to one to adjust the population size to maintain a one min test cycle
    cycle_time = 60 * 1#time in seconds to test the entire population
    min_cycle_time = 30
    cycle_time_step = 2
    pid_update_rate = 20 #reset watchdog after every n seconds
    enable_flash_crash_protection = False
    flash_crash_protection_delay = 60 * 3 #three hours
    trusted_keys_path = "./config/trusted_keys/"
    config_loaded = 0
    #!!!!!!!!!!!!!!!!end of loaded config values!!!!!!!!

    #define the module exit function
    profile = False
    def gts_exit(msg,pid=None):
        global profile
        if pid != None:
            server.pid_msg(pid,msg)
            server.pid_exit(pid)
        if profile == True:
            print "gts: profiler saving gts_call_graph.png to ./report/"
            pycallgraph.make_dot_graph('./report/gts_call_graph.png')
        print msg
        sys.exit()


    #load config
    try:
        __main__ = load_config_file_into_object('global_config.json',__main__)
    except:
        gts_exit("gts: error detected while loading the configuration. the application will now exit.")
    else:
        if config_loaded == False:
            gts_exit("gts: configuration failed to load. the application will now exit.")
        else:
            print "gts: configuration loaded."


    #internal variables
    quartile_cycle = False
    quartile = ''
    bs = ''
    verbose = False
    run_once = False
    get_config = False
    get_default_config = False
    score_only = False
    profile = False
    pid = None
    g = genepool()
    gd = "UNDEFINED"

    if len(sys.argv) >= 3:
        # Convert the two arguments from strings into numbers
        quartile = sys.argv[1]
        bs = sys.argv[2]
        if len(sys.argv) > 3:
            for i in range(3,len(sys.argv)):
                if sys.argv[i] == 'v':
                    verbose = True
                if sys.argv[i] == 'run_once':
                    #use with gal.py to auto reset (to address pypy memory leaks)
                    #exit after first local optima found
                    #or in the case of 'all' quartiles being tested, reset after once cycle through the quartiles
                    run_once = True
                if sys.argv[i] == 'get_default_config':
                    #if set the default gene_def config will be loaded from the server
                    get_default_config = True
                    get_config = True
                if sys.argv[i] == 'get_config':
                    #if set the gene_def config will be randomly loaded from the server
                    get_config = True
                if sys.argv[i] == 'score_only':
                    #if set the gene_def config will be randomly loaded from the server
                    score_only = True
                if sys.argv[i] == 'profile':
                    try:
                        import pycallgraph
                    except:
                        print "gts: pycallgraph module not installed. Profiling disabled."
                    else:
                        pycallgraph.start_trace()
                        profile = True
                        print "gts: running pycallgraph profiler"
                if sys.argv[i] == 'pid':
                    #set the pid from the command line
                    try:
                        pid = sys.argv[i + 1]
                    except:
                        pass
    if pid == None:
        #if the pid is not set from the command line then
        #use the genetic class object id
        pid = g.id

    #which quartile group to test
    while not (quartile in ['1','2','3','4','all']):
        print "Which quartile group to test? (1,2,3,4):"
        quartile = raw_input()
    if quartile != 'all':
        quartile = int(quartile)
    else:
        quartile = 1
        quartile_cycle = True
        update_all_scores = True

    if score_only:
        update_all_scores = True
    else:
        update_all_scores = False

    #configure the gene pool
    if get_config == True:
        print "gts: Loading gene_def from the server."
        while gd == "UNDEFINED" and get_config == True:
            #get the gene def config list from the server
            gdhl = json.loads(server.get_gene_def_hash_list())

            if get_default_config == True:
                    gdh = json.loads(server.get_default_gene_def_hash())
                    gdhl = [gdh,gdh,gdh]    #create a dummy list with the same (default) hash
            if len(gdhl) < 2:
                #the default config isn't defined
                #if there are less then two genes registered then switch to the local config.
                get_config = False
                break
            #pick one at random
            gdh = random.choice(gdhl)
            #get the gene_def
            gd = server.get_gene_def(gdh)
            #print gd
            if gd != "UNDEFINED":
                try:
                    gd = json.loads(gd)
                    #load the remote config
                    g = load_config_into_object(gd,g)
                    #only need to register the client with the existing gene_def hash
                    server.pid_register_client(pid,gdh)
                    print "gts: gene_def_hash:",gdh
                    print "gts: name",gd['name']
                    print "gts: description",gd['description']
                    print "gts: gene_def load complete."
                except:
                    print "gts: gene_def load error:",gd
                    gd = "UNDEFINED"
                    get_config = False #force load local gen_def.json config
            else:
                time.sleep(5) #default config is undefined so just wait and try again....
                                #the script will remain in this loop until the default config is set


    if get_config == False:
        gd = load_config_from_file("gene_def.json")
        g = load_config_into_object(gd,g)

        #register the gene_def file and link to this client using the gene pool id as the PID (GUID)
        f = open('./config/gene_def.json','r')
        gdc = f.read()
        f.close()
        gdh = server.pid_register_gene_def(pid,gdc)
        server.pid_register_client(pid,gdh)


    #reset the process watchdog
    server.pid_alive(pid)
    #send a copy of the command line args
    server.pid_msg(pid,str(sys.argv))

    ff = None
    if gd.has_key('fitness_script'):
        #check for an updated signed package on the gene_server
        #pypy probably wont have pycrypto installed - fall back to python in a subprocess to sync
        #fitness module names in the gene_def exclude the .py file extention 
        #but signed packages use the extention. check for extention, if none exists then add .py
        print "gts: synchronizing signed code"        
        if len(gd['fitness_script'].split('.')) == 1:
            sync_filename = gd['fitness_script'] + '.py'
        subprocess.call(('python','cpsu.py','get',sync_filename,trusted_keys_path))

        print "gts: loading the fitness module",gd['fitness_script']
        ff = __import__(gd['fitness_script'])
    else:
        print "gts: no fitness module defined, loading default (bct)"
        ff = __import__('bct')
    te = ff.trade_engine()

    #apply global configs
    te.max_length = max_length
    te.enable_flash_crash_protection = enable_flash_crash_protection
    te.flash_crash_protection_delay = flash_crash_protection_delay
    #load the gene_def fitness_config, if available
    if gd.has_key('fitness_config'):
        te = load_config_into_object(gd['fitness_config'],te)
    te.score_only = True
    print "gts: initializing the fitness function"
    te.initialize()

    #bootstrap the population with the winners available from the gene_pool server
    while not(bs == 'y' or bs == 'n'):
        print "Bootstrap from the gene_server? (y/n)"
        bs = raw_input()
    if bs == 'y':
        bob_simulator = True
        g.local_optima_trigger = 10
        bootstrap_bobs = json.loads(server.get_bobs(quartile,pid))
        bootstrap_all = json.loads(server.get_all(quartile,pid))
        if (type(bootstrap_bobs) == type([])) and (type(bootstrap_all) == type([])):
            g.seed()
            if len(bootstrap_all) > 100:
                g.pool = []
            g.insert_genedict_list(bootstrap_bobs)
            g.insert_genedict_list(bootstrap_all)
            g.pool_size = len(g.pool)
            if update_all_scores == True:
                #reset the scores for retesting
                g.reset_scores()
            else:
                #mate the genes before testing
                g.next_gen()
        else: #if no BOBS or high scores..seed with a new population
            print "gts: no BOBs or high scores available...seeding new pool."
            g.seed()

        print "gts: Update all scores:",update_all_scores
        print "gts: %s BOBs loaded"%len(bootstrap_bobs)
        print "gts: %s high scores loaded"%len(bootstrap_all)

        print "gts: Pool size: %s"%len(g.pool)

    else:
        bob_simulator = False
        #update_all_scores = False
        g.local_optima_trigger = 5
        print "gts: Seeding the initial population"
        g.seed()

    #the counters are all incremented at the same time but are reset by different events:
    test_count = 0  #used to reset the pool after so many loop cycles
    total_count = 0 #used to calculate overall performance
    loop_count = 0  # used to trigger pool size calibration and data reload

    max_score = -100000
    max_score_id = -1
    max_gene = None
    multicall_count = 0
    start_time = time.time()
    watchdog_reset_time = time.time()
    server.pid_alive(pid)
    print "gts: running the test sequencer"
    while 1:
        test_count += 1
        total_count += 1
        loop_count += 1
        if load_throttle == 1:
            time.sleep(load_throttle_sleep_interval)

        if (time.time() - watchdog_reset_time) >= pid_update_rate: #total_count%pid_update_rate == 0:
            #periodicaly reset the watchdog monitor
            print "gts: resetting watchdog timer"
            watchdog_reset_time = time.time()
            server.pid_alive(pid)

        if loop_count > g.pool_size:
            if score_only: #quartile_cycle == True and bob_simulator == True:
                #force a state jump to load the next quartile to retest the genes
                #in this mode the only function of the client is to cycle through the quartiles to retest existing genes
                g.local_optima_reached = True

            #update_all_scores = False  #on the first pass only, bob clients need to resubmit updated scores for every gene
            loop_count = 0
            #reset the watchdog monitor
            #server.pid_alive(pid)
            #benchmark the cycle speed
            current_time = time.time()
            elapsed_time = current_time - start_time
            gps = total_count / elapsed_time
            #pid_update_rate = int(gps * 40)
            if calibrate == 1:
                print "gts: recalibrating pool size..."
                g.pool_size = int(gps * cycle_time)
                cycle_time -= cycle_time_step
                if cycle_time < min_cycle_time:
                    cycle_time = min_cycle_time
                if g.pool_size > 10000:
                    g.pool_size = 10000
            kss = (gps*te.input_data_length)/1000.0
            performance_metrics = "gts: ","%.2f"%gps,"G/S; ","%.2f"%kss,"KS/S;","  Pool Size: ",g.pool_size,"  Total Processed: ",total_count
            performance_metrics = " ".join(map(str,performance_metrics))
            print performance_metrics
            pmd = {'channel':'gts_metric','gps':gps,'kss':kss,'pool':g.pool_size,'total':total_count}
            server.pid_msg(pid,json.dumps(pmd))

        if g.local_optima_reached:
            test_count = 0

            #initialize fitness function (load updated data)
            te.initialize()

            if score_only: #quartile_cycle == True and bob_simulator == True:
                #jump to the next quartile and skip the bob submission
                update_all_scores = True
                quartile += 1
                if quartile > 4:
                    quartile = 1
                    if run_once:
                        print "gts: flushing xmlrpc multicall buffer."
                        multicall() #send any batched calls to the server
                        print "gts: run once done."
                        gts_exit("gts: run once done.",pid)

            elif max_gene != None:
                #debug
                print "gts: ",max_gene
                #end debug
                print "gts: submit BOB for id:%s to server (%.2f)"%(str(max_gene['id']),max_gene['score'])
                server.put_bob(json.dumps(max_gene),quartile,pid)
                if quartile_cycle == True:
                    #if cycling is enabled then
                    #the client will cycle through the quartiles as local optimas are found
                    #jump to the next quartile
                    quartile += 1
                    if quartile > 4:
                        quartile = 1
                        if run_once:
                            gts_exit("gts: run once done.",pid)
            else:
                if max_score > -1000:
                    print "gts: **WARNING** MAX_GENE is gone.: ID",max_score_id
                    print "*"*80
                    print "gts: GENE DUMP:"
                    for ag in g.pool:
                        print ag['id'],ag['score']
                    print "*"*80
                    gts_exit("gts: HALTED.",pid)

            max_gene = None #clear the max gene
            max_score = -100000 #reset the high score

            if quartile_cycle == False and run_once:
                print "gts: flushing xmlrpc multicall buffer."
                multicall() #send any batched calls to the server
                print "gts: run once done."
                gts_exit("gts: run once done.",pid)

            if bob_simulator:
                #update_all_scores = True   #on the first pass only, bob clients need to resubmit updated scores for every gene
                bootstrap_bobs = json.loads(server.get_bobs(quartile,pid))
                bootstrap_all = json.loads(server.get_all(quartile,pid))
                g.pool_size = len(g.pool)
                if (type(bootstrap_bobs) == type([])) and (type(bootstrap_all) == type([])):
                    g.seed()
                    g.pool = []
                    g.insert_genedict_list(bootstrap_bobs)
                    g.insert_genedict_list(bootstrap_all)
                    if quartile_cycle == True:
                        #reset the scores for retesting
                        g.reset_scores()
                    else:
                        #mate the genes before testing
                        g.next_gen()

                else: #if no BOBS or high scores..seed with a new population
                    #print "no BOBs or high scores available...seeding new pool."
                    g.seed()
            else:
                g.seed()

        if test_count > (g.pool_size * 10):
            test_count = 0
            print "gts: reseting scores to force retest of winners..."
            test_count = 0
            max_score = 0   #knock the high score down to prevent blocking
                    #latest scoring data which may fall due to
                    #the latest price data
            g.next_gen()
            g.reset_scores()

        #create/reset the trade engine
        te.reset()

        #get the next gene
        ag = g.get_next()

        #configure the trade engine
        te = load_config_into_object({'set':ag},te)

        #set the quartile to test
        te.test_quartile(quartile)

        #run the fitness function
        try:
            te.run()
        except Exception, err:
            #kill off any genes that crash the trade engine (div by 0 errors for instance)
            print "gts: ***** GENE FAULT *****"
            print Exception,err
            print traceback.format_exc()
            print "gts: ***** END GENE FAULT *****"
            g.set_score(ag['id'],g.kill_score)
        else:
            #return the score to the gene pool
            try:
                score = te.score()
            except Exception, err:
                #kill off any genes that crash the trade engine (div by 0 errors for instance)
                print "gts: ***** GENE SCORE FAULT *****"
                print Exception,err
                print traceback.format_exc()
                print "gts: ***** END GENE SCORE FAULT *****"
                g.set_score(ag['id'],g.kill_score)
            else:
                if verbose:
                    print "gts: ",ag['gene'],"\t".join(["%.5f"%max_score,"%.5f"%score,"%.3f"%g.prune_threshold])
                g.set_score(ag['id'],score)
                #g.set_message(ag['id'],"Balance: " + str(te.balance) +"; Wins: " + str(te.wins)+ "; Loss:" + str(te.loss) +  "; Positions: " + str(len(te.positions)))
                g.set_message(ag['id'],te.text_summary)

                if score > 1000 and profile == True:
                    gts_exit("gts: profiling complete")

                #if a new high score is found submit the gene to the server
                if score > max_score and update_all_scores == False:
                    print "gts: submit high score for quartile:%s id:%s to server (%.5f)"%(str(quartile),str(ag['id']),score)
                    max_score = score
                    max_score_id = ag['id']
                    max_gene = ag.copy() #g.get_by_id(max_score_id)
                    if max_gene != None:
                        server.put(json.dumps(max_gene),quartile,pid)
                    else:
                        print "gts: MAX_GENE is None!!"
        if update_all_scores == True:
            print "gts: updating score for quartile:%s id:%s to server, multicall deffered (%.5f)"%(str(quartile),str(ag['id']),score)
            agene = g.get_by_id(ag['id'])
            if agene != None:
                multicall_count += 1
                multicall.mc_put(json.dumps(agene),quartile,pid)
                if multicall_count > 40:
                    multicall_count = 0
                    print "gts: flushing xmlrpc multicall buffer."
                    multicall()
            else:
                print "gts: updating gene error: gene is missing!!"


