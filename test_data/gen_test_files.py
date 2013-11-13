from time import *
from math import sin

t = time()

print t

f1 = 0.05
f2 = 1.3
f3 = 3.4
f4 = 11.7
offset = 15

f = open("test_data.csv",'w')
for i in xrange(2500):
    t += 60
    j = i / 100.0
    signal = sum(map(sin,[f1*j,f2*j,f3*j,f4*j])) + offset
    print t,signal
    f.write(",".join(map(str,(t,signal,1))) + '\n')
f.close()

