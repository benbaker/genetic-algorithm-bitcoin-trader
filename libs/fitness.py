
"""
fitness v0.01

- implements a fitness function base class


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
import time
from operator import itemgetter
from math import exp
import sys
from logs import *
from cache import *
import logging

logging.basicConfig(level=logging.WARNING)
#logger = logging.getLogger(__name__)
logger = logging

class Fitness:
    def __init__(self):
        self.cache = cache()
        self.cache_input = True
        self.cache_results = False
        self.cache_chart = False
        self.logs = logs()
        self.input_file_name = ""
        self.text_summary = ""   #text summary of the results
        self.input_data = []
        self.classification = []
        self.input_data_length = 0
        self.current_quartile = 0
        self.period = 0
        self.positions = []
        self.score_only = False     #set to true to only calculate what is required for scoring a strategy
                                    #to speed up performance.
        self.max_length = 10000000
        self.enable_flash_crash_protection = False
        self.flash_crash_protection_delay = False
        self.reset()
        return


    def reset(self):
        self.logs.reset()
        self.score_balance = 0
        self.period = 0
        return

    def load_input_data(self):
        #base class provides a csv format input loader
        #format of "N,value" , where N can be a index or timestamp
        logger.info("loading data (csv format)")
        self.input_data = None
        if self.cache_input == True:
            cache_label = self.input_file_name +'::'+str(self.max_length)
            self.input_data = self.cache.get(cache_label)
        if self.input_data == None:
            f = open(self.input_file_name,'r')
            d = f.readlines()
            f.close()

            if len(d) > self.max_length:
                d = d[self.max_length * -1:]

            self.input_data = []
            for row in d[1:]:
                v = row.split(',')[2] #volume
                r = row.split(',')[1] #price
                t = row.split(',')[0] #time
                self.input_data.append([int(float(t)),float(r),float(v)])
            logger.info("input data loaded from file-----")
            if self.cache_input == True:
                self.cache.set(cache_label,self.input_data)
                self.cache.expire(cache_label,60*10)
        else:
            logger.info("cached data found: " + cache_label)
        self.input_data_length = len(self.input_data)
        logger.info("loaded data len:" + str(self.input_data_length))
        return

    def initialize(self):
        #
        # !!! WARNING !!!
        #
        # If the gene_def config can influence the classification make sure the cache label has a unique name!!! 
        self.classification_cache_label = str(hash(self)) + '::'+__name__+'_classification::'+str(self.max_length)

        logger.info("initializing")
        self.load_input_data()
        if self.cache_input == False:
            self.classify(self.input_data)
        else:
            cm = self.cache.get(self.classification_cache_label)
            if cm == None:
                logger.info("classifying input data")
                self.classify(self.input_data)
                if self.cache_input == True:
                    self.cache.set(self.classification_cache_label,self.classification)
                    self.cache.expire(self.classification_cache_label,60*15)
            else:
                logger.info("cached classification data found: " + self.classification_cache_label)
                self.market_class = cm
                self.classified_market_data = True
        return self.current_quartile



    def run(self):
        logger.info("run")
        #this function simply pushes the loaded data through the input function
        for i in self.input_data:
            self.input(i)
        return

    def test_quartile(self,quartile):
        #valid inputs are 1-4
        #tells the fitness function which quartile to test
        #again the definition of what a quartile represents is left to the developer
  
        #can be used to maintain four independant populations using the exact same fitness evaluation      
        #if classification is not used and the set quartile is ignored.
        self.quartile = quartile

    def classify(self,input_list):
        #returns self.current_quartile which represents one of four possible states with a value of 0-3.
        #classification preprocessor can split the input data into four quartiles
        #every input must be binned to a quartile and added to the classification list
        self.classification = []
        self.classified_data = True
        self.current_quartile = 0
        return self.current_quartile

    def score(self):
        #scoring function
        return self.score_balance

    def get_target(self):
        #used to return a target 
        target = 0
        return target

    def input(self,input_record):
        self.period += 1    #increment the period counter

        #example input logging:
        #if not self.score_only:
        #    self.time = int(time_stamp * 1000)
        #    self.logs.append('price',[self.time,record])

        return

    def compress_log(self,log,lossless_compression = False, lossy_max_length = 2000):
        #utility function to provide data compression
        #lossless compression removes records with no change in value, before and after record n
        #lossy compression selects the sample which deviates most from a moving average
        #returns a compressed log
        #compresses on index 1 of a list (ex. [time_stamp,value] )
        compressible = True
        while compressible:
            compressible = False
            ret_log = []
            for i in xrange(len(log)):
                if type(log[i][1]) == float:
                    log[i][1] = float("%.3f"%log[i][1])
                if i >= 1 and i < len(log) - 1:
                    if log[i-1][1] == log[i][1] and log[i+1][1] == log[i][1]:
                        compressible = True #no change in value before or after, omit record
                    else:
                        ret_log.append(log[i])
                else:
                    ret_log.append(log[i])
            log = ret_log

        if lossless_compression == True:
            return ret_log

        while len(log) > lossy_max_length:
            avg = log[0][1]
            avg = (log[0][1] - avg) * 0.2 + avg
            ret_log = [log[0]]  #capture the first record
            for i in xrange(1,len(log),2):
                #find which sample that deviates the most from the average
                a = abs(log[i][1] - avg)
                b = abs(log[i-1][1] - avg)
                if a > b:
                    ret_log.append(log[i])
                else:
                    ret_log.append(log[i-1])
                #update the moving average
                avg = (log[i-1][1] - avg) * 0.2 + avg
                avg = (log[i][1] - avg) * 0.2 + avg
            ret_log.append(log[len(log)-1]) #make sure the last record is captured
            log = ret_log

        return ret_log

    def cache_output(self,cache_name,periods=80000):
        #it's up to the developer what output data to cache
        #example implementation:
        #
        #p = self.logs.get('price')
        #if len(p) > periods:
        #    self.logs.prune_logs(p[-1*periods][0])

        #self.logs.compress_logs(exclude_keys=['buy','sell','stop','trigger'],lossless_compression = False, max_lossy_length = 10000)
        #self.cache.set(cache_name,self.logs.json())
        return


def test():
    te = Fitness()
    te.input_file_name = "./datafeed/bcfeed_mtgoxUSD_1min.csv"
    te.initialize()
    te.test_quartile(1)
    te.run()
    return te

if __name__ == "__main__":
    import pdb
    import hotshot,hotshot.stats
    print "fitness base class profile "

    print " -- this is a test script to profile the performance of the fitness funciton base class"
    print "Profiling...(This is going to take a while)"

    class trade_engine(Fitness):
        def __init__(self):
            Fitness.__init__(self)


    prof = hotshot.Profile("fitness.prof")
    te = prof.runcall(test)
    prof.close()
    stats = hotshot.stats.load("fitness.prof")
    stats.strip_dirs()
    stats.sort_stats('time','calls')
    stats.print_stats(20)

    te = trade_engine()

    print "Score:",te.score()
    print "Done."
