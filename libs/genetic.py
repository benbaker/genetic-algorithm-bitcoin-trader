
"""
genetic v0.01

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

import random
import time
from operator import itemgetter
import pdb
import hashlib

#seed the random number generator
random.seed(time.time())

def zero(a):
    return 0

#create a gene pool
class genepool:
    def __init__(self):
        #generate a unique gene pool id
        self.md = hashlib.md5()
        self.md.update(str(time.time()) + str(random.random() * 1000000))
        self.id = self.md.hexdigest()[0:16]
        self.prune_threshold = 0.30 #score threshold - percentile (top n%)
        self.max_prune_threshold = 0.20 #score threshold - percentile (top n%)
        self.min_prune_threshold = 0.03 #score threshold - percentile (top n%)
        self.step_prune_threshold_rate = 0.03#score threshold - step down increment

        self.mutate = 0.10      #mutation rate
        self.max_mutate = 0.20      #max/min mutation rates
        self.min_mutate = 0.00      #adds support for adaptive mutation rates
        self.step_mutate_rate = 0.0001      #step down increment

        self.splice_on_boundry = True   #only splice genes on variable boundries
        self.multiple_parent = 0.05 #multiple parent rate
        self.max_multiple_parents = 7   #maximum number of multi parent merge (per parent)
        self.enable_niche_filter = True
        self.niche_trigger = 3      #trigger niche filter when n bits or less don't match
        self.niche_threshold = 0.95 #(calculated!) niche filter threshold for fitering similar genes
        self.niche_min_iteration = 7    #min iteration before the niche filter starts
        self.bit_sweep_rate = 0.99  #rate at which to execute a bit sweep across the best gene (bit level hill climbing)
        self.bit_sweep_min_iteration = 3#min iteration before a bit sweep can happen
        self.pool_size = 1000       #min pool size (working size may be larger)
        self.pool_family_ratio = 0.99   #pct of the pool to be filled w/ offspring
        self.pool_max_survivor_ratio = 0.3  #max survivor pool ratio
        self.kill_score = -100000
        self.pool= []           #gene pool
        self.contains = []      #gene data config
        self.genelen = 0        #calculated gene length
        self.iteration = 0      #current iteration
        self.max_iteration = 300        #max iteration before kill off
        self.log_enable = False
        self.log_filename = ""
        self.local_optima_reached = False   #flag to indicate when a local optima has been reached
        self.local_optima_trigger = 10      #number of iterations with no increase in score required to trigger
        self.local_optima_buffer = []       #the local optima flag. The buffer maintains the last high scores

        self.next_index = 0     #get next index (needed for opencl batch processing)
        self.id_index = 10000

    def step_prune(self):
        """
        Steps down the pruning threshold by step_prune_threshold_rate.
        Automaticaly cycles through the range max_prune_threshold to min_prune_threshold

        The prune_threshold is the top precentage of genes to be selected for populating the next generation

        Args: none
        Returns: none
        """
        if self.prune_threshold > self.min_prune_threshold:
            self.prune_threshold -= self.step_prune_threshold_rate
            if self.prune_threshold <= 0:
                self.prune_threshold = self.max_prune_threshold
        else:
            self.prune_threshold = self.max_prune_threshold

    def step_mutate(self):
        """
        Steps down mutate by step_mutate_rate.
        Automaticaly cycles through the range max_mutate to min_mutate

        The muate class variable is the precentage of probability for gene mutations

        Args: none
        Returns: none
        """
        if self.mutate > self.min_mutate:
            self.mutate -= self.step_mutate_rate
        else:
            self.mutate = self.max_mutate


    def set_log(self,filename):
        self.log_enable = True
        self.log_filename = filename

    def log_dict(self,msg):
        try:
            msg.keys()
        except:
            #empty dict - nothing to log
            return
        if self.log_enable == True:
            f = open(self.log_filename,'a')
            f.write(str(msg) + '\n')
            f.close()

    def reset_scores(self):
        """
        Resets all scores in the gene pool

        Args: none
        Returns: none
        """
        #Reset the scores in the gene pool
        for i in range(len(self.pool)):
            self.pool[i]['score'] = None
            self.pool[i]['time'] = None

    def mutate_gene(self,gene):
        """
        Mutates a gene

        Args:
            gene: A string representation of a binary gene

        Returns: A string representation of the mutated binary gene
        """
        self.step_mutate()

        m = ""
        for bit in gene:
            if random.random() > (1 - self.mutate):
                bit = str(int(bool(int(bit)) ^ bool(1))) #xor
            m += bit

        return m

    def bit_sweep(self,gene):
        """
        Bit sweep hill climb


        Args:
            gene: A string representation of a binary gene

        Returns: A list containing the bit sweeped genes
        """
        bsl = []
        for j in xrange(len(gene)):
            ng = ""
            for k in xrange(len(gene)):
                if j == k:
                    ng += str(int(bool(int(gene[k])) ^ bool(1))) #xor
                else:
                    ng += gene[k]
            bsl.append(ng)
        return bsl

    def niche_filter(self,pool):
        """
        Filters out similar genes to the highest scoring gene

        Object Config:
            self.niche_trigger: filter when n bits or less don't match

        Args:
            pool: A gene population list

        Returns:
            A filtered list
        """
        #filter out similar genes to the winner
        #to maintain population diversity
        if len(pool) < 2:   #only run the filter if there are genes available
            return pool
        #calculate the niche_threshold
        self.niche_threshold = (self.genelen - self.niche_trigger) / float(self.genelen)

        winner = pool[0]['gene']
        ret_pool = [pool[0]]
        for i in range(1,len(pool)):
            match = 0
            for j in range(self.genelen):
                if pool[i]['gene'][j] == winner[j]:
                    match += 1
            if match / float(self.genelen) >= self.niche_threshold:
                #gene is similar - filter it out
                #print "filtered similar gene",pool[i]['gene']
                pass
            else:
                ret_pool.append(pool[i])
        return ret_pool


    def merge_multi(self,gene_list):
        """
        Merge multiple genes by majority vote

        Requires at least three genes

        Args:
            gene_list: A gene list to merge

        Returns:
            A merged gene
        """
        #adds support for arb number of multiple parents
        #merge by majority vote
        # - need at least three to merge (duh!)
        # - and should be an odd number (no tied votes)
        if len(gene_list) < 3:
            print "genetic: need at least three genes to merge"
        n = len(gene_list[0])
        half_n = n/2.0
        sums = map(zero,range(n))
        for item in gene_list:
            for i in range(len(item)):
                if item[i] == '1':
                    sums[i] += 1
        #build the merged gene
        g = ""
        for asum in sums:
            if asum >= half_n:
                g += "1"
            else:
                g += "0"
        return g

    def mate(self,a,b):
        """
        Create offspring gene

        - Some will be mated, some will be mated and mutated and some will be mutated but not mated. @ 33%/33%/33%

        Args:
            a: parent gene a
            b: parent gene b

        Returns:
            offspring gene
        """
        # To create diveristy in the population..
        # Some will be mated, some will be mated and mutated and some will be
        # mutated but not mated. @ 33%/33%/33%

        #splice two genes (66% probablility)
        if random.random() >= 0.33:
            if self.splice_on_boundry == False:
                #splice anywhere
                l = len(a)
                splice = int(random.random() * l)

            else:
                #splice on a variable boundary
                l = len(self.contains)
                splice = 0
                splice_at = int(random.random() * l)
                for i in range(0,splice_at):
                    splice += self.contains[i][1] #var length

            c = a[:splice] + b[splice:]

            #mutate the children (50% probability)
            if random.random() > 0.5:
                c = self.mutate_gene(c)
        else:
            #select one of the parents (50% probability)
            #and mutate it (33% probability)
            if random.random() > 0.5:
                c = a
            else:
                c = b
            c = self.mutate_gene(c)

        return c

    def next_gen(self):
        """
        Create the next generation from the current population

        - test for local optima
        - remove survivor twins
        - apply the threshold
        - apply the niche filter (if enabled)
        - filter out the kill_score genes
        - generate offspring
        - bit sweep (if triggered)
        - if max iterations have been reached repopulate the gene pool

        Args: none
        Returns: none
        """
        #populate the pool with the next generation
        self.iteration += 1
        self.next_index = 0
        scores = []
        max_score = -99999
        winning_gene = ""

        #sort the genes by score
        self.pool = sorted(self.pool, key=itemgetter('score'),reverse=True)
        if len(self.pool) < 2:
            self.seed()

        #DEBUG
        c = 0
        print "genetic: Top 10:" + "-" * 73
        for g in self.pool:
            c += 1
            if c > 10:
                break
            print "genetic: ",g['score'],g['id']

        print "genetic: ","-" * 80

        winning_gene = self.pool[0]
        print "genetic: Pool Length: ",len(self.pool)
        print "genetic: HIGH SCORE: ",winning_gene['id']
        max_score = winning_gene['score']
        self.log_dict(winning_gene)

        #test for local optima
        if max_score != None:
            self.local_optima_buffer.append(max_score)
        if len(self.local_optima_buffer) > self.local_optima_trigger:
            self.local_optima_buffer = self.local_optima_buffer[1:]

        if len(self.local_optima_buffer) == self.local_optima_trigger:
            if abs((sum(self.local_optima_buffer) / self.local_optima_trigger) - max_score) < 0.001:
                #local optima reached
                print "genetic: ","#"*25,"local optima reached","#"*25
                self.local_optima_reached = True

        #remove survivor twins
        gen = self.pool
        filtered_gen = []
        tlist = []
        for i in range(len(gen)):
            if gen[i]['gene'] in tlist:
                #twin found ignore
                pass
            else:
                tlist.append(gen[i]['gene'])
                filtered_gen.append(gen[i])
        gen = filtered_gen

        #apply the threshold
        self.step_prune()   #calculate the variable pruning threshold
        threshold = int(len(gen) * self.prune_threshold)
        gen = gen[:threshold]

        #apply the niche filter
        if self.enable_niche_filter == True:
            if self.iteration > self.niche_min_iteration:
                gen = self.niche_filter(gen)


        #filter out the kill_score genes
        tgen = []
        for i in range(len(gen)):
            if gen[i]['score'] > self.kill_score or gen[i]['score'] == None:
                tgen.append(gen[i])
        gen = tgen

        #make sure there are at least three genes available (even if they're twins)
        if len(gen) < 3:
            gen = self.pool[0:3]

        #generate offspring
        os = []
        if len(gen) > 1:
            for i in range(int(self.pool_size * self.pool_family_ratio)  - len(gen)):
                if random.random() < self.multiple_parent:
                    n_merge = int(random.random() * self.max_multiple_parents)
                    if n_merge < 3: #make sure the min number of samples are taken
                        n_merge = 3
                    if n_merge%2 == 0: #make sure there are an odd number of samples
                        n_merge += 1
                    #collect the samples
                    m_l = []
                    f_l = []
                    max_m = 0
                    for j in range(n_merge):
                        m = int(random.random() * len(gen))
                        f = int(random.random() * len(gen))
                        m_l.append(gen[m]['gene'])
                        f_l.append(gen[f]['gene'])
                        if m > max_m:
                            max_m = m
                    m = max_m #transfer the oldest generation id from the sample to the offspring
                    mm = self.merge_multi(m_l)  #multi parent merge - male
                    mf = self.merge_multi(f_l)  #multi parent merge - female
                    new_g = self.mate(mm,mf)
                else:
                    m = int(random.random() * len(gen))
                    f = int(random.random() * len(gen))
                    new_g = self.mate(gen[m]['gene'],gen[f]['gene'])
                gdict = {"gene":new_g,"score":None,"time":None,"generation":gen[m]["generation"] + 1,"id":self.create_id(),"msg":""}
                os.append(gdict)

        #bit sweep (bit level hill climbing)
        if random.random() <= self.bit_sweep_rate and self.iteration > self.bit_sweep_min_iteration:
            print "genetic: running hill climb bit sweep"
            #random gene
            i = int(random.random() * (len(gen) - 1))
            bsl = self.bit_sweep(gen[i]['gene'])
            for new_g in bsl:
                gdict = {"gene":new_g,"score":None,"time":None,"generation":gen[i]["generation"] + 1,"id":self.create_id(),"msg":""}
                os.append(gdict)
            #current high scoring gene (xor)
            bsl = self.bit_sweep(winning_gene['gene'])
            for new_g in bsl:
                gdict = {"gene":new_g,"score":None,"time":None,"generation":winning_gene["generation"] + 1,"id":self.create_id(),"msg":""}
                os.append(gdict)

        #if max iterations have been reached repopulate
        #the gene pool
        if self.iteration >= self.max_iteration:
            self.iteration = 0
            winning_gene['score'] = 0 #reset the score
            gen = [winning_gene]
            os = []
            print "genetic: ","*"*10,"NEW POPULATION (saving only the winning gene)","*"*10


        self.pool = gen + os
        print "genetic: post filter HIGH SCORE:", self.pool[0]['id']
        #create some fresh genes if pool space is available
        new_gene_count = 0
        while len(self.pool) < self.pool_size:
            new_gene_count += 1
            self.pool.append(self.create_gene())

        #DEBUG
        #self.pool = sorted(self.pool, key=itemgetter('score'))
        #for some reason the top list item is getting deleted ????
        #for now just insert a new gene at the top of the list...
        #self.pool.insert(0,self.create_gene())

        #decode the genes
        self.decode()

        print "genetic: Survivors",len(gen)
        print "genetic: Offspring",len(os)
        print "genetic: New",new_gene_count
        print "genetic: Pool Size:",len(self.pool)
        print "genetic: Threshold:",self.prune_threshold
        print "genetic: Mutate:",self.mutate
        print "genetic: Local Optima Buffer:",self.local_optima_buffer
        print "genetic:", "-" * 72

    def get_next(self):
        """
        Returns the next available gene to be scored.
        If all genes have been scored then next_gen is called

        Args: none
        Returns: a gene
        """
        #get the next available unscored gene
        #if none are available then create the
        #next generation
        if self.next_index >= len(self.pool) - 1:
            self.next_index = 0

        index = self.next_index + 1
        get_next_gen = 0
        while not get_next_gen and len(self.pool) > 0:
            if self.pool[index]['score'] == None:
                self.next_index = index
                return self.pool[index]
            if index == self.next_index:
                self.next_index = 0
                get_next_gen = 1
            index += 1
            if index >= len(self.pool):
                index = 0

        print "genetic: NEXT GEN " + "#"*80
        self.next_gen()
        return self.get_next()

    def get_by_id(self,id):
        """
        Returns the gene with the given id.

        Args: id: gene identification
        Returns: a gene
        """
        for g in self.pool:
            if g['id'] == id:
                return g
        return None

    def set_score(self,id,score):
        """
        Sets the gene score for the given id

        Args:
            id: gene identification
            score: float
        Returns: none
        """
        #set the score for a gene
        for g in self.pool:
            if g['id'] == id:
                g['score'] = score
                g['time'] = time.time()
                return

    def set_message(self,id,msg):
        """
        Sets a message to a gene with the given id

        Args:
            id: gene identification
            msg: string message
        Returns: none
        """
        #set the message for a gene (basicaly tag a note on the gene)
        for g in self.pool:
            if g['id'] == id:
                g['msg'] = msg
                return

    def add_numvar(self,name,bits,decimal_places,offset=0,mult=1):
        """
        Adds a numerical variable to the gene definition.

        Used to define the contents of the gene and provide the translation configuration

        Args:
            name: name of the variable
            bits: int: number of bits
            decimal_places: int: shifts decimal point n places to the left
            offset: int/float offset
            multi: float multiplier
        Returns: none
        """
        #add a variable to the gene
        self.contains.append([name,bits,decimal_places,offset,mult])

    def rbit(self):
        """
        Generates a random bit

        Args: none
        Returns: "1" or "0" (string)
        """
        #generate a random bit
        if random.random() > 0.5:
            return "1"
        else:
            return "0"

    def calc_genelen(self):
        """
        calculate the gene length

        Args: none
        Returns: int gene length
        """
        #calculate the gene length (bits)
        self.genelen = 0
        for item in self.contains:
            self.genelen += item[1]
        return self.genelen

    def decode(self):
        """
        decodes the gene pool

        Args: none
        Returns: none
        """
        #decode the gene pool into key:value dictionarys
        for g in self.pool:
            offset = 0
            for v in self.contains:
                name = v[0]
                var_len = v[1]
                var_offset = v[3]
                var_mult = v[4]
                var = g['gene'][offset:offset+var_len]
                offset += var_len
                n = int(var,2)
                if v[2] > 0:
                    n = ((n * 1.0) / pow(10,v[2]))
                g[name] = (n + var_offset) * var_mult

    def decode_gene_dict(self,gene):
        """
        decodes a gene

        Args: gene dictionary
        Returns: gene dictionary
        """
        offset = 0
        for v in self.contains:
            name = v[0]
            var_len = v[1]
            var_offset = v[3]
            var_mult = v[4]
            var = gene['gene'][offset:offset+var_len]
            offset += var_len
            n = int(var,2)
            if v[2] > 0:
                n = ((n * 1.0) / pow(10,v[2]))
            gene[name] = (n + var_offset) * var_mult
        return gene

    def create_id(self):
        """
        generates a random id

        Args: none
        Returns: string id
        """
        self.id_index += 1
        if self.id_index > 99999:
            self.id_index = 9999
        #return str(int(time.time())).replace('.','')[4:] + str(self.id_index) + '-' + self.id
        self.md.update(str(int(time.time()))+str(self.id_index) + '-' + self.id)
        return self.md.hexdigest()[0:16] +'-'+self.id

    def create_gene(self):
        """
        generates a random gene

        Args: none
        Returns: a gene dictionary
        """
        gene = ""
        for j in range(self.genelen):
            gene += self.rbit()
        gdict = {"gene":gene,"score":None,"time":None,"generation":1,"id":self.create_id(),"msg":""}
        for v in self.contains:
            gdict.update({v[0]:0})
        return gdict

    def insert_genedict(self,gene_dict):
        """
        inserts a gene dictionary into the gene pool

        Args: gene_dict: gene dictionary
        Returns: none
        """
        gene_dict['score'] = None
        self.pool.append(gene_dict)
        return

    def insert_genedict_list(self,gene_dict_list):
        """
        inserts a list of gene dictionaries into the gene pool

        Args: gene_dict_list: gene dictionary list
        Returns: none
        """
        #print "inserting gene dicts..."
        for g_d in gene_dict_list:
            #print g_d['id'],g_d['score']
            g_d['score'] = None
            self.pool.append(g_d)
        self.decode()
        #print "done."
        return


    def insert_genestr(self,gene):
        """
        inserts a gene string into the gene pool

        Args: gene: a gene string
        Returns: none
        """
        g_d = self.create_gene()
        g_d['gene'] = gene
        g_d = self.decode_gene_dict(g_d)
        self.pool.append(g_d)
        return g_d

    def insert_genestr_list(self,gene_list):
        """
        inserts a gene string into the gene pool

        Args: gene_list: a list of gene strings
        Returns: none
        """
        for gene in gene_list:
            self.insert_genestr(gene)
        return

    def seed(self):
        """
        seeds the gene pool with random genes

        Args: none
        Returns: none
        """
        self.pool = []
        self.iteration = 0
        self.next_index = 0
        self.mutate = self.max_mutate
        self.prune_threshold = self.max_prune_threshold
        self.local_optima_reached = False
        self.local_optima_buffer = []
        self.calc_genelen()
        for i in range(self.pool_size):
            gdict = self.create_gene()
            self.pool.append(gdict)
        self.decode()


if __name__ == "__main__":
    #test the genetic class
    g = genepool()
    g.splice_on_boundry = True
    g.pool_size = 200
    g.niche_min_iteration = 10000
    #16 bit number (65535) with the decimal three places to the left (10^3 = 1000)
    #max value should be 65.535 minus an offset of 200 giving a variable range of -200 to -134.465
    g.add_numvar("afloat",32,6,-5000)

    g.add_numvar("aint",64,0,200)

    g.seed()

    print g.contains

    max_score = -99999999
    max_gene = ""

    while g.local_optima_reached == False:
        ag = g.get_next()
        score = ag['afloat'] * ag['aint']
        #print ag['gene'],"\t",score
        if score > max_score:
            max_score = score
            max_gene = ag['gene']
        g.set_score(ag['id'],ag['afloat'] * ag['aint'])
    print "MAX_SCORE:",max_score
    print "MAX_GENE:",max_gene

    #test merge_multi
    l = ["101","010","110"]
    if g.merge_multi(l) != "110":
        print "merge_multi error"
    else:
        print "merge_multi pass"

    print str(g.contains)
    print str(ag)


