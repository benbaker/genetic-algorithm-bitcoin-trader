"""
neural_network v0.01

Feed forward neural network class library

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

#feed forward NN implementation
import math

def sigmoid(x):
  return 1 / (1 + math.exp(-x))

class Neuron:
    def __init__(self,id,num_inputs):
        self.num_inputs = num_inputs
        self.id = id + '_'+ str(self.num_inputs).zfill(3)
        self.input_weights = list(range(self.num_inputs))
        self.bias = 1
        self.output = 0

    def create_neuron(self):
        return

    def get_num_weights(self):
        return self.num_inputs + 1

    def get_weights(self):
        return self.input_weights + [self.bias]

    def set_weights(self,weights):
        self.input_weights = weights[:-1]
        self.bias = weights[-1]
        return

    def set_inputs(self,inputs):
        #verify the inputs
        #if len(inputs) != self.num_inputs:
        #    print "ERROR: incorrect number of required ("+str(self.num_inputs)+ ") inputs received: "+str(len(inputs))
        #    return
        #calculate and set the output
        #sum the inputs * weights
        output = 0
        for i in xrange(self.num_inputs):
            output += inputs[i] * self.input_weights[i]  #apply input weighting
        output *= self.bias #apply the neuron bias
        self.output = 1 / (1 + math.exp(-output))    #apply sigmoid
        return self.output

    def get_output(self):
        return self.output

class NeuronLayer:
    def __init__(self,id,num_neurons,num_inputs):
        self.num_neurons = num_neurons
        self.num_inputs = num_inputs
        self.neurons = []
        self.id = id.zfill(3)

    def create_layer(self):
        for i in xrange(self.num_neurons):
            self.neurons.append(Neuron(self.id + '_' + str(i).zfill(3),self.num_inputs))
            self.neurons[-1].create_neuron()
        return

    def get_neuron_ids(self):
        nids = []
        for n in self.neurons:
            nids.append(n.id)
        return nids

class NeuralNet:
    def __init__(self,num_inputs,num_outputs,num_hidden_layers,num_neurons_per_hidden_layer):
        #define input layer, hidden layer(s) and output layer
        self.num_inputs = num_inputs    #input layer neurons (each neuron takes only one input each)
        self.num_outputs = num_outputs  #output layer neurons, num of inputs are defined by num_neurons_per_layer
        self.num_hidden_layers = num_hidden_layers
        self.num_neurons_per_hidden_layer = num_neurons_per_hidden_layer
        self.neuron_layers = []
        self.create_network()

    def create_network(self):
        #build the input layer 
        #- number of input layer neurons equals the number of NN inputs with each neuron taking one NN input
        self.neuron_layers = []
        self.neuron_layers.append(NeuronLayer(str(0),self.num_inputs,1))
        self.neuron_layers[-1].create_layer()

        #build the hidden layers
        #- number of inputs equals the number of neurons from the previous layer
        for i in xrange(self.num_hidden_layers):
            self.neuron_layers.append(NeuronLayer(str(i+1),self.num_neurons_per_hidden_layer,self.neuron_layers[-1].num_neurons))
            self.neuron_layers[-1].create_layer()

        #build the output layer
        #- number of inputs equals the number of neurons from the previous layer
        #- number of neurons equals the number of outputs
        self.neuron_layers.append(NeuronLayer(str(self.num_hidden_layers + 1),self.num_outputs,self.neuron_layers[-1].num_neurons))
        self.neuron_layers[-1].create_layer()
        return

    def get_neuron_ids(self):
        #each ID is formated as layer_neuron_inputs: 1_2_3 is layer 1, neuron 2 which takes 3 inputs
        nids = []
        for nl in self.neuron_layers:
            nids += nl.get_neuron_ids()
        return nids

    def get_weighting_params(self):
        ids = self.get_neuron_ids()
        params = []
        for aid in ids:
            layer,neuron,inp = aid.split('_')
            for i in xrange(int(inp) + 1):#the plus one is for the bias weighting for the neuron itself
                params.append('_'.join((layer,neuron,str(i).zfill(3))))
        return params
                
    def get_num_weights(self):
        num_weights = 0
        ids = self.get_neuron_ids()
        for aid in ids:
            layer,neuron,inp = aid.split('_')
            num_weights += int(inp) + 1
        return num_weights

    def get_weights(self):
        weights = []
        for layer in self.neuron_layers:
            for neuron in layer.neurons:
                weights += neuron.get_weights()
        return weights

    def set_weights(self,weights):
        if len(weights) != self.get_num_weights():
            print "Error: NeuralNet:set_weights incorrect number if weights supplied"  
            return
        for layer in self.neuron_layers:
            for neuron in layer.neurons:
                num = neuron.get_num_weights()
                neuron.set_weights(weights[:num])
                weights = weights[num:]
        return

    def set_inputs(self,inputs):
        #if len(inputs) != self.num_inputs:
        #    print "Error: wrong number of inputs"
        outputs = []
        #set the input layer (one neuron for each input)
        for i in xrange(len(inputs)):
            outputs.append(self.neuron_layers[0].neurons[i].set_inputs([inputs[i]]))
        inputs = outputs
        #sets the inputs and returns the outputs for intermediate & final layers
        for layer in self.neuron_layers[1:]:
            outputs = [] 
            for neuron in layer.neurons:
                outputs.append(neuron.set_inputs(inputs))
            #set the intermediate layer outputs as the next layers inputs
            inputs = outputs
        #return the final layer outputs
        return outputs


#ga-bitbot specific NN utils
def generate_gene_def_template(nn,filename):
    template = """{
	"name":"REPLACE THIS WITH A NAME",
	"version":"0.9",
	"description":"REPLACE THIS WITH A DESCRIPTION",

	"fitness_script":"%{FITNESS_NAME}",
	"fitness_config":
	{
		"set" :
		{
			"input_file_name": "./datafeed/bcfeed_mtgoxUSD_1min.csv",
			"nlsf": 1.0,
			"stbf": 1.025,
			"commision": 0.006,
			"atr_depth": 60,
			"max_length" : 300000,
			"enable_flash_crash_protection" : 1,
			"flash_crash_protection_delay" : 240
		}
	},

	"set" :
	{
		"prune_threshold" : 0.30,
		"max_prune_threshold" : 0.20,
		"min_prune_threshold" : 0.03,
		"step_prune_threshold_rate" : 0.03,
		"mutate" : 0.10,
		"max_mutate" : 0.20,
		"min_mutate" : 0.00,
		"step_mutate_rate" : 0.0001,
		"multiple_parent" : 0.05,
		"max_multiple_parents" : 7,
		"niche_trigger" : 3,
		"niche_min_iteration" : 7,
		"bit_sweep_rate" : 0.40, 
		"bit_sweep_min_iteration" : 5,
		"pool_size" : 50,
		"pool_family_ratio" : 0.99,
		"pool_max_survivor_ratio" : 0.3,
		"kill_score" : -10000,
		"max_iteration" : 60000,
		"local_optima_trigger" : 8
	},

	"call" :
	{
		"add_numvar":
		[
%{NUMVARS}
		]
	}
}"""

    params = nn.get_weighting_params()
    numvars = ""
    #num var config of : 11,3,-1.0235,1.0
    #gives:
    #resolution: 2048 values
    #step size: 0.001
    #min value: -1.0235
    #max value: 1.0235
    for p in params:
        numvars += '\t\t\t["_NN_'+p+'",11,3,-1.0235,1.0],\n'
    numvars = numvars.rstrip(',\n')
    template = template.replace('%{FITNESS_NAME}',filename.split('.')[0])
    template = template.replace('%{NUMVARS}',numvars)
    template = template.replace('\t','    ')
    #f = open(filename,'w')
    #f.write(template)
    #f.close()
    return template

def generate_fitness_template(nn,filename):
    import neural_network_fitness_template
    #f = open('neural_network_fitness_template.pyt','r')
    template = neural_network_fitness_template.template #f.read()
    #f.close()
    params =  nn.get_weighting_params()
    output = ""
    for item in params:
        output += "\t\tself._NN_"+item+" = 1\n"
    output = output.replace('\t','    ')
    template = template.replace('#%{NN_WEIGHTS}',output)
    template = template.replace('#%{NN_NUM_INPUTS}',str(nn.num_inputs))
    template = template.replace('#%{NN_NUM_OUTPUTS}',str(nn.num_outputs))
    template = template.replace('#%{NN_NUM_HIDDEN_LAYERS}',str(nn.num_hidden_layers))
    template = template.replace('#%{NN_NUM_NEURONS_PER_HIDDEN_LAYER}',str(nn.num_neurons_per_hidden_layer))
    #f = open(filename,'w')
    #f.write(template)
    #f.close()
    return template



if __name__ == "__main__":
    num_inputs = 8
    num_outputs = 3
    num_hidden_layers = 4
    num_neurons_per_hidden_layer = 8
    nn = NeuralNet(num_inputs,num_outputs,num_hidden_layers,num_neurons_per_hidden_layer)
    nn.create_network()
    print "Neuron IDs:"
    print nn.get_neuron_ids()
    print "\n\nNeuron weighting & bias parameters:"
    params =  nn.get_weighting_params()
    #print params
    print "\n\nNeuron weighting & bias parameter count:"
    num_weights = nn.get_num_weights()
    print num_weights
    print "\n\nNeuron initalized weights & bias parameters:"
    #print nn.get_weights()
    print "\n\nNeuron set get weights & bias parameters test:"
    weights = list(range(num_weights))
    nn.set_weights(weights)
    got_weights = nn.get_weights()
    if got_weights == weights:
        print "passed."
    else:
        print "failed."
    #print got_weights
    print "\n\nNeuron set inputs test:"
    print "outputs: " + str(nn.set_inputs(range(num_inputs)))

    print "\n\nNeuron speed test:"
    import time
    num_runs = 3000
    inputs = range(num_inputs)
    start = time.time()
    for i in xrange(num_runs):
        nn.set_inputs(inputs)
    t = time.time() - start
    print "updates/sec :",num_runs/t


    #build a gene_def template
    generate_gene_def_template(nn,'test_scafold.json')
    
    #build scafolding for a NN fitness class
    generate_fitness_template(nn,'test_fitness.py')

