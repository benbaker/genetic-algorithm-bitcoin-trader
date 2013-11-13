function gene_def_lib(){
	this.gene_def_lib_entries = ko.observableArray([]);
};

gene_def_lib.prototype.removeAll = function(db_lib){
	//remove any existing db librarys
	this.gene_def_lib_entries.splice(1,1000); //remove all items
};



function gene_db_lib(){
	this.gene_db_lib_entries = ko.observableArray([]);
	this.gene_def_lib = new gene_def_lib();
};

gene_db_lib.prototype.load = function(db_lib){
	//remove any existing db librarys
	this.gene_db_lib_entries.splice(1,1000); //remove all items
	this.gene_def_lib.removeAll();
	//load new librarys
	for (var db in db_lib){
		if (db_lib[db]['gene_def'] != "UNDEFINED"){
			this.gene_db_lib_entries.push(ko.mapping.fromJS(db_lib[db]));
			this.gene_def_lib.gene_def_lib_entries.push(ko.mapping.fromJS(JSON.parse(db_lib[db]['gene_def'])));
		}
	}

	ko.applyBindings(this);
	

};





