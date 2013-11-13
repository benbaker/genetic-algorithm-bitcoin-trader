
"""
logs v0.01

simple keyed dictionary log

Copyright 2012 Brian Monkaba

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

import json

class logs:
    def __init__(self):
        self._log = {}
        self._metacontent = {} #data about data content

    def addkey(self,key):
        if self._log.has_key(key):
            return
        else:
            self._log.update({key:[]})
            self._metacontent.update({key:{}})
        return

    def append(self,key,value):
        if self._log.has_key(key):
            self._log[key].append(value)
        else:
            self._log.update({key:[value]})
            self._metacontent.update({key:{}})
        return

    def get(self,key):
        if self._log.has_key(key):
            return self._log[key]
        else:
            return None

    def get_metacontent(self,key):
        #gets the metacontent dictionary for a given key
        if self._metacontent.has_key(key):
            return self._metacontent[key]
        else:
            return None

    def set_metacontent(self,key,meta):
        #sets the metacontent dictionary for a given key
        if self._metacontent.has_key(key):
            self._metacontent[key] = meta
        else:
            self._log.update({key:[]})
            self._metacontent.update({key:meta})

    def reset(self):
        self._log = {}
        self._metacontent = {}

    def json(self):
        return json.dumps({'content':self._log,'metacontent':self._metacontent})

    def compress_logs(self,exclude_keys=[],lossless_compression = True, max_lossy_length = 4000):
        for key in self._log.keys():
            if not (key in exclude_keys):
                self.compress_log(key,lossless_compression, max_lossy_length)
        return

    def compress_log(self,key,lossless_compression = True, max_lossy_length = 4000):
        #time series compression
        #removes records with no change in value, before and after record n
        #clamps floats to three decimal points
        #data must be in the format of [time_stamp,...]
        compressible = True
        while compressible:
            compressible = False
            ret_log = []
            for i in xrange(len(self._log[key])):
                if type(self._log[key][i][1]) == float:
                    self._log[key][i][1] = float("%.3f"%self._log[key][i][1])
                if i >= 1 and i < len(self._log[key]) - 1:
                    if self._log[key][i-1][1] == self._log[key][i][1] and self._log[key][i+1][1] == self._log[key][i][1]:
                        compressible = True #no change in value before or after, omit record
                    else:
                        ret_log.append(self._log[key][i])
                else:
                    ret_log.append(self._log[key][i])
            self._log[key] = ret_log

        if lossless_compression == True:
            return ret_log

        #lossy compression
        while len(self._log[key]) > max_lossy_length:
            avg = self._log[key][0][1]  #take the initial value as starting average
            ret_log = [self._log[key][0]]   #capture the first record
            for i in xrange(1,len(self._log[key]),2):
                #find which sample that deviates the most from the average
                a = abs(self._log[key][i][1] - avg)
                b = abs(self._log[key][i-1][1] - avg)
                if a > b:
                    ret_log.append(self._log[key][i])
                else:
                    ret_log.append(self._log[key][i-1])
                #update the moving average
                avg = (self._log[key][i-1][1] - avg) * 0.2 + avg
                avg = (self._log[key][i][1] - avg) * 0.2 + avg
            ret_log.append(self._log[key][len(self._log[key])-1])   #make sure the last record is captured
            self._log[key] = ret_log
        return ret_log


    def prune_logs(self,start_time,exclude_keys=[]):
        #prunes all logs data to after start_time
        #data must be in the format of [time_stamp,...]
        for key in self._log.keys():
            if not (key in exclude_keys):
                pruned = []
                for i in xrange(len(self._log[key])):
                    if self._log[key][i][0] >= start_time:
                        pruned.append(self._log[key][i])
                self._log[key] = pruned
        return



if __name__ == "__main__":
    log = logs()
    log.append('alog',0)
    log.append('alog',1)
    log.append('alog',2)
    log.append('alog',3)
    log.append('alog',4)
    log.append('alog',5)

    log.append('blog','a')
    log.append('blog','b')
    log.append('blog','c')
    log.append('blog','d')
    log.append('blog','e')
    log.append('blog','f')

    log.append('list',[0,1,2])
    log.append('list',[3,4,5])
    log.append('list',[6,7,8])

    log.addkey('empty')

    print log.get('alog')
    print log.get('blog')
    print log.get('list')

    log.set_metacontent('alog',{'type':'int','description':'data description'})
    print log.get_metacontent('alog')

    print log.json()
    log.reset()

    print log.get('alog')
    print log.get('blog')
    print log.get('list')

    #test time series compression
    import math

    for i in range(3600):
        value = math.sin(i/10.0 * (math.pi/180))
        if value <= 0.0:
            value = 0
        log.append('time_series',[i,value])
        log.append('time_series2',[i,value])
        log.append('time_series3',[i,value])

    uncompressed = log.get('time_series')
    compressed = log.compress_log('time_series',lossless_compression = False, max_lossy_length = 16)

    print "3600 sample half wave rectified sin function compression test to 16 samples"
    print "uncompressed length",len(uncompressed)
    print "compressed length",len(compressed)
    print "compression ratio",(1.0 - (len(compressed)/float(len(uncompressed)))) * 100

    for item in compressed:
        print item[0],',',item[1]



    print "testing compress logs with exclusion list"

    log.compress_logs(exclude_keys=['alog','blog','list','empty','time_series2'],lossless_compression = True, max_lossy_length = 4000)

    print "excluded series len:"
    print len(log._log['time_series2'])
    print "non-excluded series len:"
    print len(log._log['time_series3'])


    print "testing pruning"
    log.prune_logs(900,exclude_keys=['alog','blog','list','empty','time_series','time_series3'])
    print len(log._log['time_series2'])



