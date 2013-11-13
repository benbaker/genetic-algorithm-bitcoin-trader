// parallel coordinate wrapper / form builder
// requires the d3.parcoords library


var mediator = (function(){
	var subscribe = function(channel, fn){
		if (!mediator.channels[channel]) mediator.channels[channel] = [];
		mediator.channels[channel].push({ context: this, callback: fn });
		return this;
	};
     
	unsubscribe = function(channel){
		if (!mediator.channels[channel]) return this;
		delete mediator.channels[channel];
		return this;
	};

        publish = function(channel){
		if (!mediator.channels[channel]) return this;
		var args = Array.prototype.slice.call(arguments, 1);
		for (var i = 0, l = mediator.channels[channel].length; i < l; i++) {
			var subscription = mediator.channels[channel][i];
			subscription.callback.apply(subscription.context, args);
		}
		return this;
        };
     
	return {	//public interface
		channels: {},
		publish: publish,
		subscribe: subscribe,
		unsubscribe: unsubscribe,
		installTo: function(obj){
			obj.subscribe = subscribe;
			obj.publish = publish;
		}
	};
     
}());


function pcf(){
	this.viewDataset = [];
	this.viewDimensions = [];
	this.viewDimensionsActive = [];
	this.viewAlpha = 0.55;
	this.viewColor = "#400800";
	this.viewMode = "queue";
	this.viewComposite = "lighter";
	this.viewRate = 36;
	this.viewFormDiv = "";
	this.viewFormRenderTarget = "";
	this.viewStatsRenderTarget = "";
	this.viewChartRenderTarget = "";
	this.viewLegendRenderTarget = "";
	this.viewLegendEnable = false;
	this.viewStatsEnable = false;
	this.chartWidth = 400;
	this.chartHeight = 250;
	this.pchart;
	this.firstRender = true;
};

//mediator.installTo(pcf);
pcf.prototype.subscribe = mediator.subscribe;
pcf.prototype.unsubscribe = mediator.unsubscribe;
pcf.prototype.publish = mediator.publish;

pcf.prototype.setData = function(d){this.viewDataset = d;};
pcf.prototype.setDimensions = function(d){this.viewDimensionsActive = JSON.parse(JSON.stringify(d)); this.viewDimensions = d;};
pcf.prototype.setAlpha = function(d){this.viewAlpha = d;};
pcf.prototype.setColor = function(d){this.viewColor = d;};
pcf.prototype.setMode = function(d){this.viewMode = d;};
pcf.prototype.setComposite = function(d){this.viewComposite = d;};
pcf.prototype.setRate = function(d){this.viewRate = d;return this.viewRate;};
pcf.prototype.getRate = function(d){ return this.viewRate;};
pcf.prototype.setRenderTarget = function(d){ this.viewFormRenderTarget = d;};
pcf.prototype.setStatsTarget = function(d){ this.viewStatsRenderTarget = d;};
pcf.prototype.viewLegend = function(val){ this.viewLegendEnable = val;};
pcf.prototype.viewStats = function(val){ this.viewStatsEnable = val;};
pcf.prototype.render = function(){
	$(this.viewFormRenderTarget).html('');	//clear render target
	//mediator.channels = {};
	//create a form div to encapsulate the chart + controls
	this.viewFormDiv = this.viewFormRenderTarget + '_pcf_form';		
	jQuery('<div/>',{id:this.viewFormDiv.replace('#','')}).appendTo(this.viewFormRenderTarget);


	this.chartWidth = $(this.viewFormRenderTarget).width() * 0.90;

	this.viewChartRenderTarget = this.viewFormDiv + '_pcf_chart';
	jQuery('<div/>',{id: this.viewChartRenderTarget.replace('#',''), width: this.chartWidth, height: this.chartHeight}).appendTo(this.viewFormDiv);
	$(this.viewChartRenderTarget).addClass("parcoords");

	pchart = d3.parcoords()(this.viewChartRenderTarget)
		.data(this.viewDataset)
		.dimensions(this.viewDimensionsActive)
		.alpha(this.viewAlpha)
		.color(this.viewColor)
		.mode(this.viewMode)
		.composite(this.viewComposite)
		.rate(this.viewRate)
		.render()
		.createAxes()
		.brushable()
		.reorderable();
	if (this.viewStatsEnable == true){
		$(this.viewStatsRenderTarget).html('STATS');
		//pchart.on('brush', listener)
	}
	if (this.viewLegendEnable == true){
		this.viewLegendRenderTarget = this.viewFormDiv + '_pcf_legend';
		jQuery('<div/>',{id: this.viewLegendRenderTarget.replace('#',''), width: this.chartWidth}).appendTo(this.viewFormDiv);

		fs_id = this.viewLegendRenderTarget + '_fs'
		$(this.viewLegendRenderTarget).append('<fieldset id="' + fs_id.replace('#','') + '" ></fieldset>');
		
		for (var i = 0; i < this.viewDimensions.length; i++) {
			var item = this.viewDimensions[i];
		//this.viewDimensions.forEach(function(item){

			if (this.viewDimensionsActive.indexOf(item) >= 0)
			{
				$(fs_id).append($(document.createElement("input")).attr({
		    			 id:	'cb_'+ item + '_' + fs_id.replace('#','')
		    			,type:	'checkbox'
					,name:	item
		    			,checked:true
		    		}));
			} else {
				$(fs_id).append($(document.createElement("input")).attr({
		    			 id:	'cb_'+ item + '_' + fs_id.replace('#','')
		    			,type:	'checkbox'
					,name:	item
		    			,checked:false
		    		}));
			}

			//$('#cb_'+ item + '_' + fs_id.replace('#','')).subscribe = mediator.subscribe;
			//$('#cb_'+ item + '_' + fs_id.replace('#','')).publish = mediator.publish;
			$('#cb_'+ item + '_' + fs_id.replace('#','')).click(function(){
				if ($(this).is(':checked')){
					console.log('checked');
					mediator.publish(this.id +'_checked',this.name);
				} else {
					console.log('unchecked');
					mediator.publish(this.id +'_unchecked',this.name);
				}

			});

			this.unsubscribe('cb_'+ item + '_' + fs_id.replace('#','') +'_checked');
			this.unsubscribe('cb_'+ item + '_' + fs_id.replace('#','') +'_unchecked');

			if (true){
				this.subscribe('cb_'+ item + '_' + fs_id.replace('#','') +'_checked',function(arg){
					console.log(this);
					console.log(arg);
					var index = this.viewDimensionsActive.indexOf(arg);
					if (index == -1){this.viewDimensionsActive.push(arg);}
					this.render();
				});
				this.subscribe('cb_'+ item + '_' + fs_id.replace('#','') +'_unchecked',function(arg){
					console.log(this);
					console.log(arg);
					var index = this.viewDimensionsActive.indexOf(arg);
					if (index >= 0){this.viewDimensionsActive.splice(index, 1);}
					this.render();				
				});


			}

			$(fs_id).append($(document.createElement("label")).attr({
	    			 id:	'label_'+ item + '_' + fs_id.replace('#','')
	    			,for:	'cb_'+ item + '_' + fs_id.replace('#','')
	    		}));

			$('#label_'+ item + '_' + fs_id.replace('#','')).html(' ' + item);
			
			//$(fs_id).buttonset();
			$(fs_id).append('<br>');
			

		};

	}
	this.firstRender = false;
}




