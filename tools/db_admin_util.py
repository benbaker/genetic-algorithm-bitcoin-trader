
"""
db_admin_util v0.01

ga-bitbot database administration utility

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
print "ga-bitbot database admin tool v%s\n"%__appversion__

import json
import sys
# try to connect to the xml server
# to make sure it's not running.
import gene_server_config
import xmlrpclib

builtin_db_hash = '0db45d2a4141101bdfe48e3314cfbca3'

__server__ = gene_server_config.__server__
__port__ = str(gene_server_config.__port__)

gene_server_running = False
try:
    #make sure the port number matches the server.
    server = xmlrpclib.Server('http://' + __server__ + ":" + __port__)
    server.save()
    gene_server_running = True
except:
    pass

print 'enter h for help.'
status = "no changes to commit"


commit_enable = True
if gene_server_running == True:
    print "Warning: gene_server must not be running to use this utility."
    print "committing changes will be disabled for this session."
    status = "committing disabled"
    commit_enable = False
    #sys.exit()


#load the db
f = open('../config/gene_server_db_library.json','r')
d = f.read()
gene_library = json.loads(d)
f.close()

signed_package_library = {}
if gene_library.has_key('signed_package_library'):
    signed_package_library = gene_library.pop('signed_package_library')

while 1:
    ui = raw_input('\nstatus: ' + status + '\n'+'?:')
    if ui == 'h':
        print "commands"
        print "---------------------------------------"
        print "h  help"
        print "a  list all databases"
        #TODO: print "l  link UNDEFINED db to the local gene_def.json"
        print "d  select a database to delete"
        #TODO: print "o  open another library to merge from"
        #TODO: print "m  merge selected databases"
        print "c  commit changes"
        print "e  export gene_def"
        print "s  stats"
        print "r  raw library dump"
        print "zp delete all genes from the library"
        print "q  quit"
    elif ui == 'zp':
        print "deleting all records"
        for key in gene_library.keys():
            gene_library[key]['gene_best'] = [[],[],[],[]]
            gene_library[key]['gene_high_scores'] = [[],[],[],[]]
        status = "uncommited changes"
    elif ui == 'r':
        filename = '../report/gene_server_db_dump.csv'
        print "export raw library dump (csv format) to " + filename
        f = open(filename,'w')
        gkeys = gene_library[gene_library.keys()[0]]['gene_high_scores'][0][0].keys()
        header = 'library,type,' + ",".join(gkeys) + '\n'
        f.write(header)
        for key in gene_library.keys():
            for l in gene_library[key]['gene_best']:
                for d in l:
                    f.write(key + ',gene_best')
                    for agk in gkeys:
                        f.write("," + str(d[agk]))
                    f.write('\n')
            for l in gene_library[key]['gene_high_scores']:
                for d in l:
                    f.write(key + ',gene_high_scores')
                    for agk in gkeys:
                        f.write("," + str(d[agk]))
                    f.write('\n')

        f.close()
    elif ui == 's':
        print "stats: markup"
        print "-----"
        for key in gene_library.keys():
            print key
            #count the number of records
            record_count = 0
            total = 0
            mn = 999
            mx = -999
            for l in gene_library[key]['gene_best']:
                for d in l:
                    record_count += 1
                    total += d['markup']
                    if d['markup'] < mn:
                        mn = d['markup']
                    if d['markup'] > mx:
                        mx = d['markup']
            avg = float(total)/(record_count + 0.00001)
            print 'bob',mn,avg,mx,record_count
            record_count = 0
            total = 0
            mn = 999
            mx = -999
            for l in gene_library[key]['gene_high_scores']:
                for d in l:
                    record_count += 1
                    total += d['markup']
                    if d['markup'] < mn:
                        mn = d['markup']
                    if d['markup'] > mx:
                        mx = d['markup']
            avg = float(total)/(record_count + 0.00001)
            print 'hs ',mn,avg,mx,record_count
            print "-"*20


    elif ui == 'a' or ui == 'd' or ui == 'e':
        index = 0
        for key in gene_library.keys():
            #count the number of records
            record_count = 0
            for l in gene_library[key]['gene_best']:
                record_count += len(l)
            for l in gene_library[key]['gene_high_scores']:
                record_count += len(l)

            print "["+str(index)+"]","database:",key,"\trecord count:", record_count
            index += 1
            details = ""
            try:
                gd = json.loads(gene_library[key]['gene_def'])
                if 'version' in gd.keys():
                    details += "\t\tversion:" + str(gd['version'])
                if 'name' in gd.keys():
                    details += "    name: " + gd['name']
                if 'description' in gd.keys():
                    details += "\tdescription: " + gd['description']


            except:
                if gene_library[key]['gene_def'] == "UNDEFINED":
                    details += "## Built-in UNDEFINED gene_def database ##"
                else:
                    details += "Invalid gene_def :",gene_library[key]['gene_def'][:30],"..."
            print details
            print ""

        if ui == 'd' or ui == 'e':
            index = -999
            while not index in range(len(gene_library.keys())):
                print "Enter the database index number 0 ...",len(gene_library.keys()) - 1
                try:
                    index = int(raw_input('[n]?:'))
                except:
                    pass
            if ui == 'd':
                if builtin_db_hash != gene_library.keys()[index]:
                    print "deleting database ["+str(index)+"]",gene_library.keys()[index]
                    gene_library.pop(gene_library.keys()[index])
                    status = "uncommited changes"
                else:
                    print "can not delete built-in UNDEFINED database"
            if ui == 'e':
                print "exporting database gene_def ["+str(index)+"]",gene_library.keys()[index]
                filename = '../config/gene_def_'+gene_library.keys()[index]+'.json'
                print "writing file " + filename
                f = open(filename,'w')
                f.write(gene_library[gene_library.keys()[index]]['gene_def'])
                f.close()

    elif ui == 'c':
        if commit_enable == True:
            print "commiting changes"
            #save the db
            f = open('../config/gene_server_db_library.json','w')
            f.write(json.dumps(gene_library))
            f.close()
            status = "no changes to commit"
        else:
            print "commiting disabled for this session."

    elif ui == 'q':
        if status == "no changes to commit" or status == "committing disabled":
            sys.exit()
        else:
            print "changes have not been commited. quit without commiting?"
            confirm_exit = ""
            while confirm_exit != 'y' and confirm_exit != 'n':
                confirm_exit = raw_input('(y/n): ')
            if confirm_exit == 'y':
                sys.exit()

    else:
        print "unknown command"

        print "---------------------------------------"

