"""
cache v0.01

simple object serializing cache wrapper and client side partitioner for redis

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

import cPickle
import json
import hashlib
import sys

# DEBUG
#
sys.path.append('/usr/local/lib/python2.7/dist-packages/')

try:
    import redis
    using_redis = True
    print "cache: redis module detected"
except:
    redis = None
    using_redis = False


#simple pickling cache wrapper for redis
#if the optional redis server isn't being used, all functions return None
class cache:
    def __init__(self):
        self.using_redis = using_redis
        self.serialize_with = 'JSON' #or 'cPickle' or 'None'
        self.partitions = 1 #default 1 (one redis instance)
                    #each additional instance assumes +1 to the last port number
        self.partition_history = {'0':0,'1':0,'2':0,'3':0,'4':0,'5':0,'6':0,'7':0}
        self.port = 6379
        self.r = None
        if self.using_redis:
            try:
                self.r = redis.StrictRedis(host='127.0.0.1',port=self.port,db=0)
                #self.r = redis.Redis(unix_socket_path='/tmp/redis.sock')
                self.r.get('testing connection')
            except:
                print "cache: can't connect to redis server, caching disabled"
                self.using_redis = False

    def select_partition(self,key):
        partition_index = int(hashlib.md5(key).hexdigest()[0],16)%self.partitions
        self.partition_history[str(partition_index)] += 1
        target_port  = partition_index + 6379
        try:
            del self.r
            self.r = redis.StrictRedis(host='127.0.0.1',port=target_port,db=0)
        except:
            print "cache: can't connect to redis server, caching disabled",target_port
            self.using_redis = False

    def set(self,key,value):
        if self.using_redis:
            if self.partitions > 1:
                self.select_partition(key)
            #print "cache: set",key
            if self.serialize_with == 'cPickle':
                return self.r.set(key,cPickle.dumps(value))
            elif self.serialize_with == 'JSON':
                return self.r.set(key,json.dumps(value))
            elif self.serialize_with == 'None':
                return self.r.set(key,value)
            else:
                raise Exception("Serializer not supported")
        else:
            return None

    def get(self,key):
        if self.using_redis:
            if self.partitions > 1:
                self.select_partition(key)
            #print "cache: get",key
            value = self.r.get(key)
            if value == None:
                return None
            else:
                if self.serialize_with == 'cPickle':
                    return cPickle.loads(value)
                elif self.serialize_with == 'JSON':
                    return json.loads(value)
                elif self.serialize_with == 'None':
                    return value
                else:
                    raise Exception("Serializer not supported")
        else:
            return None

    def expire(self,key,expiration):
        if self.using_redis:
            if self.partitions > 1:
                self.select_partition(key)
            print "cache: set expire",key
            return self.r.expire(key,expiration)
        return None

    def disable(self):
        print "cache: disabled"
        self.using_redis = False
        return




if __name__ == '__main__':

    import os
    import string
    import time
    import random
    #do some testing

    print 'building the data sets'
    #xlarge = os.urandom(100000000) #100MB
    #large = os.urandom(10000000)   #10MB
    #med = os.urandom(1000000)  #1MB
    #small = os.urandom(100000) #100KB

    xlarge = range(10000)   #1M
    large = range(1000) #1M
    med = range(100)    #100K
    small = range(10)   #10K

    key_set1 = []
    key_set2 = []
    key_set3 = []

    print 'generating the keys'
    for i in range(1000):
        key_set1.append(''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(10)))
        key_set2.append(''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(10)))
        key_set3.append(''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(10)))

    for serializer in ['cPickle','JSON','None']:
        c = cache()
        c.partitions = 1
        c.serialize_with = serializer
        for dataset in [xlarge,large,med,small]:
            #timer start
            start = time.time()
            for key_set in [key_set1,key_set2,key_set3]:
                for key in key_set:
                    c.set(key,dataset)
            #timer stop
            stop = time.time()
            print "Serializer:",serializer,", Keys:",len(key_set),", Value length:",len(dataset),", Total value length",(len(key_set) * len(dataset))/1000000.0,", Elapsed Time",stop-start
        print "-"*80

    print c.partition_history

