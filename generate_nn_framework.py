import paths
import neural_network


num_inputs = ""

while not num_inputs.isdigit():
    print "Enter the number of inputs to the neural network:"
    num_inputs = raw_input()
num_inputs = int(num_inputs)

num_outputs = ""
while not num_outputs.isdigit():
    print "Enter the number of outputs to the neural network:"
    num_outputs = raw_input()
num_outputs = int(num_outputs)

num_hidden_layers = ""
while not num_hidden_layers.isdigit():
    print "Enter the number of hidden layers in the neural network:"
    num_hidden_layers = raw_input()
num_hidden_layers = int(num_hidden_layers)

num_neurons_per_hidden_layer = ""
while not num_neurons_per_hidden_layer.isdigit():
    print "Enter the number of neurons in each hidden layer:"
    num_neurons_per_hidden_layer = raw_input()
num_neurons_per_hidden_layer = int(num_neurons_per_hidden_layer)

nn = neural_network.NeuralNet(num_inputs,num_outputs,num_hidden_layers,num_neurons_per_hidden_layer)
nn.create_network()

print "\n\nThe specified neural network has "+str(nn.get_num_weights())+" weights."

#build the gene_def template
gene_def_template = neural_network.generate_gene_def_template(nn,'nn_template_fitness.py')
f = open('nn_template_gene_def.json','w')
f.write(gene_def_template)
f.close()
print "generated the gene_def template: nn_template_gene_def.json"

#build the neural network fitness class template
nn_template_fitness = neural_network.generate_fitness_template(nn,'nn_template_fitness.py')
f = open('nn_template_fitness.py','w')
f.write(nn_template_fitness)
f.close()
print "generated the fitness template: nn_template_fitness.py"

