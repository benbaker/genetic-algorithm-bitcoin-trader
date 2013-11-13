
"""
ocl_gts v0.01

pyopencl genetic trade simulator

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




import pyopencl as cl
import numpy

# connect to the xml server
#

import xmlrpclib
import json
import gene_server_config
import time
import sys


__server__ = gene_server_config.__server__
__port__ = str(gene_server_config.__port__)

#make sure the port number matches the server.
server = xmlrpclib.Server('http://' + __server__ + ":" + __port__)

print "Connected to",__server__,":",__port__


from bct import *
from genetic import *
from load_config import *
import pdb
import time
import hashlib

if __name__ == "__main__":
    __appversion__ = "0.01a"
    print "OpenCL Genetic Bitcoin Trade Simulator v%s"%__appversion__


    deep_logging_enable = False;
    max_length = 120000
    load_throttle = 0 #go easy on cpu usage
    calibrate = 1   #set to one to adjust the population size to maintain a one min test cycle
    work_group_size = 6
    work_item_size = 128
    max_open_orders = 512   #MUST MATCH THE OPENCL KERNEL !!!!
    order_array_size = 16   #MUST MATCH THE OPENCL KERNEL !!!!
    #init pyopencl
    ctx = cl.create_some_context()
    queue = cl.CommandQueue(ctx)
    mf = cl.mem_flags
    #read in the OpenCL source file as a string
    #f = open("gkernel.cl", 'r')
    f = open("gkernel_macd.cl", 'r')
    fstr = "".join(f.readlines())
    #create the program
    ocl_program = cl.Program(ctx, fstr).build('-w') #'-g -O0 -cl-opt-disable -w'
    #kernel = ocl_program.fitness
    kernel = ocl_program.macd

    ocl_mb_wg_macd_pct = None
    input_len = 0

    def load():
        global ocl_mb_wg_macd_pct
        global input_len

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

        #allocate uninitalized buffer(s)
        input_len = numpy.uint32(len(input))
        buf_size = len(input) * work_group_size * work_item_size * 4 #float32 is four bytes
        print "#DEBUG# Buffer size: ",buf_size
        if ocl_mb_wg_macd_pct != None:
            ocl_mb_wg_macd_pct.release()
        ocl_mb_wg_macd_pct = cl.Buffer(ctx, mf.WRITE_ONLY, size=buf_size)
        print ocl_mb_wg_macd_pct.get_info(cl.mem_info.SIZE)
        queue.flush()
        return input

    #configure the gene pool
    g = genepool()
    g = load_config_into_object(load_config_from_file("gene_def.json"),g)

    #g.set_log("winners.txt")
    print "Creating the trade engine"
    te = trade_engine()
    te.score_only = True
    print "preprocessing the input data..."

    #load the inital data
    input = load()
    te.classify_market(input)
    wg_market_classification = [int(i[1] * 4) for i in te.market_class] #use the python based bct trade engine market classification
    wg_input = [i[1] for i in input]


    #process command line args
    quartile = ''
    bs = ''
    verbose = False
    print sys.argv
    if len(sys.argv) >= 3:
        # Convert the two arguments from strings into numbers
        quartile = sys.argv[1]
        bs = sys.argv[2]
        if len(sys.argv) == 4:
            if sys.argv[3] == 'v':
                verbose = True


    #which quartile group to test
    while not (quartile in ['1','2','3','4']):
        print "Which quartile group to test? (1,2,3,4):"
        quartile = raw_input()
    quartile = int(quartile)

    #bootstrap the population with the winners available from the gene_pool server
    while not(bs == 'y' or bs == 'n'):
        print "Bootstrap from the gene_server? (y/n)"
        bs = raw_input()
    if bs == 'y':
        bob_simulator = True
        g.local_optima_trigger = 10
        calibrate = 1
        bootstrap_bobs = json.loads(server.get_bobs(quartile))
        bootstrap_all = json.loads(server.get_all(quartile))
        if (type(bootstrap_bobs) == type([])) and (type(bootstrap_all) == type([])):
            g.seed()
            #g.pool = []
            g.insert_genedict_list(bootstrap_bobs)
            g.insert_genedict_list(bootstrap_all)
            g.reset_scores()
        else: #if no BOBS or high scores..seed with a new population
            print "no BOBs or high scores available...seeding new pool."
            g.seed()

        print "%s BOBs loaded"%len(bootstrap_bobs)
        print "%s high scores loaded"%len(bootstrap_all)

        print "Pool size: %s"%len(g.pool)

    else:
        bob_simulator = False
        g.local_optima_trigger = 5
        print "Seeding the initial population"
        g.seed()

    cycle_time = 60 * 1#time in seconds to test the entire population
    min_cycle_time = 50
    cycle_time_step = 1

    test_count = 0
    total_count = 0
    max_score = -10000
    max_score_id = -1
    start_time = time.time()
    print "Running the simulator"
    while 1:
        #periodicaly reload the data set
        test_count += work_group_size * work_item_size
        total_count += work_group_size * work_item_size
        if load_throttle == 1:
            time.sleep(0.35)

        if test_count > g.pool_size:
            test_count = 0
            #benchmark the cycle speed
            current_time = time.time()
            elapsed_time = current_time - start_time
            gps = total_count / (elapsed_time + 0.0001)
            if calibrate == 1:
                #print "Recalibrating pool size..."
                suggested_size = int(gps * cycle_time)
                cycle_time -= cycle_time_step
                if cycle_time < min_cycle_time:
                    cycle_time = min_cycle_time

                if (suggested_size - g.pool_size) > 1000:
                    g.pool_size += 100
                else:
                    g.pool_size = suggested_size

            print "%.2f"%gps,"G/S; ","%.2f"%((gps*len(input))/1000.0),"KS/S;","  Pool Size: ",g.pool_size,"  Total Processed: ",total_count, " Quartile: ",quartile
            #load the latest trade data
            print "Loading the lastest trade data..."
            te = trade_engine()
            te.score_only = True
            input = load()
            #preprocess input data
            te.classify_market(input)
            wg_market_classification = [int(i[1] * 4) for i in te.market_class] #use the python based bct trade engine market classification
            wg_input = [i[1] for i in input]

        if g.local_optima_reached:
            print '#'*10, " Local optima reached...sending bob to the gene_server ", '#'*10
            max_score = 0
            test_count = 0

            max_gene = g.get_by_id(max_score_id)
            if max_gene != None:
                print "--\tSubmit BOB for id:%s to server (%.2f)"%(str(max_gene['id']),max_gene['score'])
                server.put_bob(json.dumps(max_gene),quartile)
            else:
                print "--\tNo BOB to submit"
            if bob_simulator == True:
                bootstrap_bobs = json.loads(server.get_bobs(quartile))
                bootstrap_all = json.loads(server.get_all(quartile))
                if (type(bootstrap_bobs) == type([])) and (type(bootstrap_all) == type([])):
                    g.seed()
                    g.pool = []
                    g.insert_genedict_list(bootstrap_bobs)
                    g.insert_genedict_list(bootstrap_all)
                    g.reset_scores()
                    print "BOBs loaded...",len(g.pool)
                else: #if no BOBS or high scores..seed with a new population
                    print "no BOBs or high scores available...seeding new pool."
                    g.seed()
            else:
                g.seed()

            #automaticaly cycle through the four quartiles
            quartile += 1
            if quartile > 4:
                quartile = 1



        if test_count > (g.pool_size * 10):
            test_count = 0
            print "Reset scores to force retest of winners..."
            test_count = 0
            max_score = 0   #knock the high score down to prevent blocking
                    #latest scoring data which may fall due to
                    #the latest price data
            g.next_gen()
            g.reset_scores()


        #build the opencl workgroup
        wg_id = []
        wg_gene = []
        wg_shares = []
        wg_wll = []
        wg_wls = []
        wg_wls = []
        wg_buy_wait = []
        wg_markup = []
        wg_stop_loss = []
        wg_stop_age = []
        wg_macd_buy_trip = []
        wg_buy_wait_after_stop_loss = []
        wg_quartile = []
        #the following lists are only populated (elsewhere) when new data is loaded:
        #wg_market_classification = [int(i[1] * 4) for i in te.market_class] #use the python based bct trade engine market classification
        #wg_input = [i[1] for i in input]

        print "Batch processing",work_group_size * work_item_size,"genes from a pool of",len(g.pool), " and an input len of ",len(wg_input)
        for i in range(work_group_size * work_item_size):
            ag = g.get_next()

            wg_id.append(ag['id'])
            wg_gene.append(ag['gene'])
            #wg_shares.append(ag['shares'])
            wg_wll.append(ag['wll'] + ag['wls'] + 2)    #add the two together to make sure
                                    #the macd moving windows dont get inverted
            wg_wls.append(ag['wls'] + 1)
            #wg_buy_wait.append(ag['buy_wait'])
            #wg_markup.append(ag['markup'] + (te.commision * 3.0)) #+ 0.025
            #wg_stop_loss.append(ag['stop_loss'])
            #wg_stop_age.append(float(ag['stop_age']))
            #wg_macd_buy_trip.append(ag['macd_buy_trip'] * -1.0)
            #wg_buy_wait_after_stop_loss.append(ag['buy_wait_after_stop_loss'])
            #wg_quartile.append(quartile)

        print "Global Work Items: ",work_group_size * work_item_size
        #build the memory buffers
        #mb_wg_shares = numpy.array(wg_shares, dtype=numpy.float32)
        mb_wg_wll = numpy.array(wg_wll, dtype=numpy.uint32)
        mb_wg_wls = numpy.array(wg_wls, dtype=numpy.uint32)
        #mb_wg_buy_wait = numpy.array(wg_shares, dtype=numpy.uint32)
        #mb_wg_markup = numpy.array(wg_markup, dtype=numpy.float32)
        #mb_wg_stop_loss = numpy.array(wg_stop_loss, dtype=numpy.float32)
        #mb_wg_stop_age = numpy.array(wg_stop_age, dtype=numpy.float32)
        #mb_wg_macd_buy_trip = numpy.array(wg_macd_buy_trip, dtype=numpy.float32)
        #mb_wg_buy_wait_after_stop_loss = numpy.array(wg_buy_wait_after_stop_loss, dtype=numpy.uint32)
        #mb_wg_quartile = numpy.array(wg_quartile, dtype=numpy.uint32)
        #mb_wg_market_classification = numpy.array(wg_market_classification, dtype=numpy.uint32)
        mb_wg_input = numpy.array(wg_input, dtype=numpy.float32)
        #mb_wg_score = numpy.array(range(work_group_size), dtype=numpy.float32)
        #mb_wg_orders = numpy.array(range(work_group_size * max_open_orders * order_array_size), dtype=numpy.float32)
        #create OpenCL buffers

        #mapped - makes sure the data is completly loaded before processing begins
        #ocl_mb_wg_market_classification = cl.Buffer(ctx, mf.READ_ONLY | mf.ALLOC_HOST_PTR | mf.COPY_HOST_PTR, hostbuf=mb_wg_market_classification)
        ocl_mb_wg_input = cl.Buffer(ctx, mf.READ_ONLY | mf.ALLOC_HOST_PTR | mf.COPY_HOST_PTR, hostbuf=mb_wg_input)
        #ocl_mb_wg_orders = cl.Buffer(ctx, mf.READ_WRITE | mf.ALLOC_HOST_PTR | mf.COPY_HOST_PTR, hostbuf=mb_wg_orders)#mb_wg_orders.nbytes

        #unmapped - can be transferred on demand
        #ocl_mb_wg_quartile = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=mb_wg_quartile)
        #ocl_mb_wg_score = cl.Buffer(ctx, mf.READ_WRITE | mf.COPY_HOST_PTR, hostbuf=mb_wg_score)
        #ocl_mb_wg_shares = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=mb_wg_shares)
        ocl_mb_wg_wll = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=mb_wg_wll)
        ocl_mb_wg_wls = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=mb_wg_wls)
        #ocl_mb_wg_buy_wait = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=mb_wg_buy_wait)
        #ocl_mb_wg_markup = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=mb_wg_markup)
        #ocl_mb_wg_stop_loss = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=mb_wg_stop_loss)
        #ocl_mb_wg_stop_age = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=mb_wg_stop_age)
        #ocl_mb_wg_macd_buy_trip = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=mb_wg_macd_buy_trip)
        #ocl_mb_wg_buy_wait_after_stop_loss = cl.Buffer(ctx, mf.READ_ONLY | mf.COPY_HOST_PTR, hostbuf=mb_wg_buy_wait_after_stop_loss)

        #allocate uninitalized buffer(s)
        #input_len = numpy.uint32(len(input))
        #buf_size = len(input) * work_group_size * work_item_size * 4 #float32 is four bytes
        #print "#DEBUG# Buffer size: ",buf_size
        #ocl_mb_wg_macd_pct = cl.Buffer(ctx, mf.WRITE_ONLY, size=buf_size)
        #print ocl_mb_wg_macd_pct.get_info(cl.mem_info.SIZE)
        #queue.flush()


        #debug - used to make sure the datasets are constant (when input reloading is disabled)
        #m = hashlib.md5()
        #m.update(str(mb_wg_input))
        #m.update(str(mb_wg_market_classification))
        #print m.hexdigest()

        gkernel_args = """
        kernel.set_arg(0,ocl_mb_wg_shares)
        kernel.set_arg(1,ocl_mb_wg_wll)
        kernel.set_arg(2,ocl_mb_wg_wls)
        kernel.set_arg(3,ocl_mb_wg_buy_wait)
        kernel.set_arg(4,ocl_mb_wg_markup)
        kernel.set_arg(5,ocl_mb_wg_stop_loss)
        kernel.set_arg(6,ocl_mb_wg_stop_age)
        kernel.set_arg(7,ocl_mb_wg_macd_buy_trip)
        kernel.set_arg(8,ocl_mb_wg_buy_wait_after_stop_loss)
        kernel.set_arg(9,ocl_mb_wg_quartile)
        kernel.set_arg(10,ocl_mb_wg_market_classification)
        kernel.set_arg(11,ocl_mb_wg_input)
        kernel.set_arg(12,ocl_mb_wg_score)
        kernel.set_arg(13,ocl_mb_wg_orders)
        kernel.set_arg(14,input_len)
        """

        kernel.set_arg(0,ocl_mb_wg_macd_pct)
        kernel.set_arg(1,ocl_mb_wg_wll)
        kernel.set_arg(2,ocl_mb_wg_wls)
        kernel.set_arg(3,ocl_mb_wg_input)
        kernel.set_arg(4,input_len)

        #execute the workgroup
        print "executing the workgroup"
        event = cl.enqueue_nd_range_kernel(queue,kernel,mb_wg_wll.shape,(work_item_size,))
        event.wait()
        print "execution complete"
        #copy the result buffer (scores) back to the host
        #scores = numpy.empty_like(mb_wg_score)
        #cl.enqueue_read_buffer(queue, ocl_mb_wg_score, scores).wait()


        #time.sleep(0.01)

        #dumps the orders array - used for debug
        if deep_logging_enable == True:
            #write out the orders array
            orders = numpy.empty_like(mb_wg_orders)
            cl.enqueue_read_buffer(queue, ocl_mb_wg_orders, orders).wait()
            f = open('/tmp/orders/' + str(total_count),'w' )
            for i in range(0,len(orders),order_array_size):
                if int(abs(orders[i])) != i/(max_open_orders * order_array_size): #dont save untouched memory
                    f.write(wg_id[i/(max_open_orders * order_array_size)] + ':\t\t' + str(i/(max_open_orders * order_array_size))+': '+ "\t".join(map(str,(orders[i],orders[i+1],orders[i+2],orders[i+3],orders[i+4],orders[i+5],orders[i+6],orders[i+7],orders[i+8],orders[i+9],orders[i+10],orders[i+11],orders[i+12],orders[i+13],orders[i+14],orders[i+15]))))
                    f.write('\n')
            f.close()

        #release all the buffers
        #ocl_mb_wg_shares.release()
        ocl_mb_wg_wll.release()
        ocl_mb_wg_wls.release()
        #ocl_mb_wg_buy_wait.release()
        #ocl_mb_wg_markup.release()
        #ocl_mb_wg_stop_loss.release()
        #ocl_mb_wg_stop_age.release()
        #ocl_mb_wg_macd_buy_trip.release()
        #ocl_mb_wg_buy_wait_after_stop_loss.release()
        #ocl_mb_wg_quartile.release()
        #ocl_mb_wg_market_classification.release()
        ocl_mb_wg_input.release()
        #ocl_mb_wg_score.release()

        #process the results
        for i in range(work_group_size):
            #score = float(scores[i])
            score = -10000

            #dump the scores buffer to a file - used for debugging
            if deep_logging_enable == True:
                #write out the scores
                if score > 0.1 or 1:
                    f = open('/tmp/scores/' + str(wg_id[i]),'a' )
                    f.write(",".join(map(str,(time.ctime(),total_count,score, wg_gene[i], \
                        wg_shares[i], \
                        wg_wll[i], \
                        wg_wls[i], \
                        wg_buy_wait[i], \
                        wg_markup[i], \
                        wg_stop_loss[i], \
                        wg_stop_age[i], \
                        wg_macd_buy_trip[i], \
                        wg_buy_wait_after_stop_loss[i]
                    ))))

                    f.write('\n')
                    f.close()


            if verbose:
                indicator = ""
                if max_score <= score:
                    indicator = "<------------------"
                print wg_id[i],wg_gene[i],"\t".join(["%.5f"%max_score,"%.5f"%score]),indicator

            #submit the score to the gene pool
            g.set_score(wg_id[i],score)

            #if a new high score is found (or revisited) submit the gene to
            #the server
            if score > max_score and score > -1000.00:
                print "--\tSubmit high score for id:%s to server (%.2f)"%(str(wg_id[i]),score)
                max_score = score
                max_score_id = wg_id[i]
                max_gene = g.get_by_id(max_score_id)
                if max_gene != None:
                    server.put(json.dumps(max_gene),quartile)
                else:
                    print "MAX_GENE is None!!"

        #print "MAX_SCORE:",max_score,"MAX_SCORE_ID:",max_score_id,"OBJECT_TYPE:",type(g.get_by_id(max_score_id))
