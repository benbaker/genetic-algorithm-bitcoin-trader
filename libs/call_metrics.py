
"""
call_metrics v0.01

a class function decorator which collects metrics (number of calls and total execution time)

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

from functools import wraps
import time

_metrics = {}

#decorator which can be used on class methods
#inserts a _metrics dictionary into the object
def class_call_metrics(func):
    @wraps(func)
    def _decorator(self, *args, **kwargs):
        if not hasattr(self, '_metrics'):
            self._metrics = {}
        start = time.time()
        result = func(self, *args, **kwargs)
        finish = time.time()
        if not self._metrics.has_key(func.__name__):
            self._metrics.update({func.__name__:{'total_time':0,'calls':0}})
        self._metrics[func.__name__]['total_time'] += finish - start
        self._metrics[func.__name__]['calls'] += 1
        return result
    return _decorator

#decorator which can be used on funcitons
#uses the global _metrics dictionary
def call_metrics(func):
    @wraps(func)
    def _decorator(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        finish = time.time()
        if not _metrics.has_key(func.__name__):
            _metrics.update({func.__name__:{'total_time':0,'calls':0}})
        _metrics[func.__name__]['total_time'] += finish - start
        _metrics[func.__name__]['calls'] += 1
        return result
    return _decorator


def get_metrics():
    return _metrics


if __name__ == '__main__':
    class test():
        @class_call_metrics
        def test(self,data):
            """test method doc string"""
            z = 0
            for i in range(9999):
                for x in range(9999):
                    z += 1

            print "data:",data
            return 1


    @call_metrics
    def function_test(data):
        print "data",data
        return 2

    t = test()
    for i in range(10):
        print t.test(i)

    print t._metrics
    print t.test.__doc__

    print function_test('funciton test input')
    print get_metrics()



