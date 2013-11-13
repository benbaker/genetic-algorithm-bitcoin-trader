
"""
gene_server_dump v0.01

gene server dump

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
#   Dumps the stored gene data from the server to a local file
#

__appversion__ = "0.01a"
print "Genetic Bitcoin Gene Server Dump v%s"%__appversion__
# connect to the xml server
#
import gene_server_config
import xmlrpclib
import json
import time

__server__ = gene_server_config.__server__
__port__ = str(gene_server_config.__port__)

#make sure the port number matches the server.
server = xmlrpclib.Server('http://' + __server__ + ":" + __port__)

print "Connected to",__server__,":",__port__

def ppdict(d):
    #pretty print a dict
    print "-"*40
    try:
        for key in d.keys():
            print key,':',d[key]
    except:
        print d
    return d

def pwdict(d,filename):
    #pretty write a dict
    f = open(filename,'w')
    try:
        for key in d.keys():
            f.write(key + " : " + str(d[key]) + "\n")
    except:
        pass
    f.write('\n' + '-'*80 + '\n')
    f.write(str(d))
    f.close()
    return d

for quartile in [1,2,3,4]:
    try:
        print "-"*80
        print "Quartile:",quartile
        ag = json.loads(server.get(60*360,quartile))
        #ppdict(ag)
        print "gene last updated",time.time() - ag['time'],"seconds ago.", "SCORE:",ag['score']
        pwdict(ag,'./test_data/gene_high_score_' + str(quartile))
    except:
        pass

print "-"*80
print "PID STATUS:"
pid_status = json.loads(server.get_pids())
#ppdict(pid_status)
pwdict(pid_status,'./test_data/pid_status')

print "-"*80
print "PID Watchdog Check (90 sec): "
for pid in pid_status.keys():
    print pid,server.pid_check(pid,90)

#save all genes
for quartile in [1,2,3,4]:
    gd = {'bobs':[],'high_scores':[]}
    gd['high_scores'] = json.loads(server.get_all(quartile))
    gd['bobs'] = json.loads(server.get_bobs(quartile))
    f = open('./config/gene_server_db_backup_quartile' + str(quartile) + '.json','w')
    f.write(json.dumps(gd))
    f.close()



#print server.shutdown()

