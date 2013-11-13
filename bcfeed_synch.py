#converts bitcoincharts csv download into the
#1min format used by the genetic trade framework
from time import *
import urllib2
import sys


__app_version__ = "0.01a"
print "-"*80
print """
Bitcoin Data Feed Synchronizer v%s

\tConverts the data into a weighted price 1min data feed format

To automaticaly download and process the mtgox usd historic data run with the following option:
python bcfeed_synch -d

Without the -d switch the output will only be written to the datafeed_reboot folder
"""%(__app_version__)
print "-"*80

link = """http://bitcoincharts.com/t/trades.csv?symbol=mtgoxUSD&start={START_TIME}"""
start_time = 0      #don't change these variables - they are automaticaly configured
incremental_update = 0  #based on command line options
auto_move_output = 0    #

if len(sys.argv) >= 2:
    if sys.argv[1] == '-d':
        try:
            print "bcfeed_synch: Checking potential for incremental update..."
            for line in open('./datafeed/bcfeed_mtgoxUSD_1min.csv'):pass
            line = line.split(',')[0]
            line = line.split('.')[0]
            start_time = int(line) + 60
            incremental_update = 1
        except:
            print "bcfeed_synch: Incremental update not possible."
            pass
        print "bcfeed_synch: Downloading mtgox historic data..."
        link = link.replace('{START_TIME}',str(start_time))
        data = urllib2.urlopen(link).read()
        f = open("./datafeed_reboot/download_mtgoxUSD.csv",'w')
        f.write(data)
        f.close()
        auto_move_output = 1
        print "bcfeed_synch: Download complete."
    else:
        print "bcfeed_synch: Invalid argument",sys.argv[1]



f = open("./datafeed_reboot/download_mtgoxUSD.csv",'r')
d = f.readlines()
f.close()

print "bcfeed_synch: Processing input..."
one_min = []
accum_r = []
#exception handling to address issue #11 - unhandled exception when download or input file has no data
try:
    last_t = d[0].split(',')[0]
except:
    print "bcfeed_synch: No new data to process"
    sys.exit()

last_m = ctime(int(last_t)).split(':')[1]
for r in d:
    sr = r.replace('\n','').split(',')
    t,p,v = sr
    if (ctime(int(t)).split(':')[1] == last_m):
        accum_r.append(map(float,sr))
    else:
        tv = 0
        twp = 0
        for r in accum_r:
            #print r
            twp += (r[1] * r[2])
            tv += r[2]
        if tv > 0:
            wp = twp / tv
            one_min.append([last_t,wp,tv])
            #print last_t,wp,tv
        accum_r = [map(float,sr)]

    last_t = int(t)
    last_m = ctime(last_t).split(':')[1]

print "bcfeed_synch: Writing output file..."
if auto_move_output == 1 :
    print "bcfeed_synch: Updating the datafeed directory directly...no need to manualy move the output file"
    if incremental_update == 1:
        print "bcfeed_synch: Writing incremental update..."
        f = open('./datafeed/bcfeed_mtgoxUSD_1min.csv','a')
    else:
        f = open('./datafeed/bcfeed_mtgoxUSD_1min.csv','w')

else:
    f = open('./datafeed_reboot/bcfeed_mtgoxUSD_1min.csv','w')


for t,p,v in one_min:
    f.write(",".join(map(str,[t,p,v])) + '\n')
f.close()
print "bcfeed_synch: Done."

