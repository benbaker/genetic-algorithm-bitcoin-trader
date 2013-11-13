//
// server.js v0.01 
//
//    -- A node.js ga-bitbot server which also serves as a mtgox socket.io bridge 
//	 This application must be started on the same computer running the ga-bitbot gene server.	
//
//
// Copyright 2011 Brian Monkaba
//
// This file is part of ga-bitbot.
//
//  ga-bitbot is free software: you can redistribute it and/or modify
//  it under the terms of the GNU General Public License as published by
//  the Free Software Foundation, either version 3 of the License, or
//  (at your option) any later version.
//
//  ga-bitbot is distributed in the hope that it will be useful,
//  but WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//  GNU General Public License for more details.
//
//  You should have received a copy of the GNU General Public License
//  along with ga-bitbot.  If not, see <http://www.gnu.org/licenses/>.
//
var _redis = require("redis");
var redis = _redis.createClient();
var express = require('express');
var app = express();
app.use(express.static(__dirname + '/'));
app.use(express.errorHandler({ dumpExceptions: true, showStack: true }));

var http = require('http');
var https = require('https');
var xmlrpc = require('xmlrpc');
var rpcClient = xmlrpc.createClient({ host: '127.0.0.1', port: 9854, path: '/gene'});

var ch_depth = '24e67e0d-1cad-4cc0-9e7a-f8523ef460fe';
var ch_trades = 'dbf1dee9-4f2e-4a08-8cb7-748919a71b21';
var ch_ticker = 'd5f06780-30a8-4a48-a2f8-7ed181b4a13f';
var trade_buffer = [];

var full_depth = "";
var ask_depth = {};
var bid_depth = {};
var initializing = 1;

//
// get full depth using the mtgox http api 
//   - bootstrap the depth data on the server
var options = {
	host: 'localhost',	
	path: '/api/1/BTCUSD/fulldepth'
};

//give a bad address for the depth init - needed for debug 
//because multiple requests from server restarts could get the IP banned

/*
console.log('Requesting depth initialization...');
https.get({ host: 'mtgox000.com', path: '/api/1/BTCUSD/fulldepth' }, function(res) {
	console.log("statusCode: ", res.statusCode);
	console.log("headers: ", res.headers);

	res.on("data", function(chunk) {
		full_depth += chunk;
		console.log('---data received-----');
	});

	res.on("end", function() {
		console.log('https end');
		full_depth = JSON.parse(full_depth);
		console.log('---ask depth-----' + full_depth.return.asks.length);
		console.log('---bid depth-----' + full_depth.return.bids.length);
		full_depth.return.asks.forEach(function(item){
			 ask_depth[item.price] = item.amount;
		});
		full_depth.return.bids.forEach(function(item){
			 bid_depth[item.price] = item.amount;
		});
		initializing = 0;
	});

}).on('error', function(e) {
  console.error('HTTPS ERROR:: ' + e);
  initializing = 0;
});

//wait state commented out for debug - full depth retreival disabled
//while (initializing == 1) {
	//wait
//}
console.log('Depth initialization complete');

*/

//
// create app routes
//

app.get('/', function (req, res) {
	res.sendfile(__dirname + '/bridge.html');
});

app.get('/img/*', function (req, res) {
	res.sendfile(__dirname +'/img/'+req.params);
});

app.get('/gene_link/:hid/:gid/*', function (req, res) {
	console.log(req.params);
	res.sendfile(__dirname +'/'+req.params);
});

app.get('/gene_link/:hid/:gid', function (req, res) {
	console.log(req.params);
	redis.get(req.params.hid + '/' + req.params.gid+'.html', function (err, reply) {
		if (reply == null)
		{	//file request
			console.log(__dirname +'/'+req.params.gid);
			res.sendfile(__dirname +'/'+req.params.gid);
		}
		res.send(JSON.parse(reply));
	});
});


//
// create socket.io server
//
var server = http.createServer(app);
var io = require('socket.io').listen(server);
io.set('log level', 1);
server.listen(8088);
var gabb = io.of('/ga_bitbot');
var rpc_start_call = 0;

//performance metric functions - used to measure gene_server latency
function startRPC(){
	var d = new Date();
	rpc_start_call = d.getSeconds();
	rpc_start_call += (d.getMilliseconds()) / 1000;
}

function endRPC(){
	var d = new Date();
	var rpc_end_call = d.getSeconds();
	rpc_end_call += (d.getMilliseconds()) / 1000;
	//return latency in milliseconds
	return (rpc_end_call - rpc_start_call) * 1000;
}


gabb.on('connection', function (socket) {

	io.sockets.emit('user connected');
    //when a user connects send them the full bid and ask depths
	socket.emit('message', {'channel':'full_ask','depth':ask_depth});
	socket.emit('message', {'channel':'full_bid','depth':bid_depth});

	socket.on('disconnect', function () {
		 io.sockets.emit('user disconnected');
	});

	socket.on('message', function (p1, fn) {
		// do something
	});


	socket.on('request_gene_db', function () {
		rpcClient.methodCall('get_db', [], function (error, value) {
				//console.log('get pids response: ' + value);
				//stream the databases one at a time
				var dbl = JSON.parse(value);
				for (var db in dbl){
					console.log('get pids response: ' + db);
					var dbp = {};
					dbp[db] = dbl[db];
					socket.emit('message', {'channel':'gene_db','value':dbp});
				}
			});
	});

	socket.on('request_gene_db_stripped', function () {
		try{
			rpcClient.methodCall('get_db_stripped', [], function (error, value) {
					//console.log('sending request_gene_db_stripped response');
					try{socket.emit('message', {'channel':'gene_db_stripped','value':JSON.parse(value)});}catch(err){console.log('get_db_stripped emit error');};
				});
		}catch(err){
			console.log('get_db_stripped error');
		};
	});

	socket.on('request_gene_server_metrics', function () {
		try{
			startRPC();
			rpcClient.methodCall('get_gene_server_metrics', [], function (error, value) {
					value = JSON.parse(value);
					value.server_latency = endRPC();
					//console.log('gene server response time: ' + value.latency);
					//console.log('sending get_gene_server_metrics response' + value);
					socket.emit('message', {'channel':'gene_server_metrics','value':value});
			});
		}catch(err){
			console.log('get_gene_server_metrics error');
		};
	});

	socket.on('set_trade_enable', function (state,gene_def) {
		rpcClient.methodCall('trade_enable', [state,gene_def], function (error, value) {
				console.log('trade_enable response: ' + value);
				//socket.emit('message', {'channel':'gene_db','value':JSON.parse(value)});
			});
	});

	socket.on('set_trade_priority', function (priority,gene_def) {
		rpcClient.methodCall('trade_priority', [priority,gene_def], function (error, value) {
				console.log('trade_priority response: ' + value);
				//socket.emit('message', {'channel':'gene_db','value':JSON.parse(value)});
			});
	});

	socket.on('request_gene_data', function (gene_def,gene_id) {
		console.log('gene data requested: id: ' + gene_id + ' , from db: ' + gene_def);
		redis.get(gene_def + '/' + gene_id, function (err, reply) {
			socket.emit('message', {'channel':'gene_data','value':JSON.parse(reply)});
		});
	});
});

//
// create client socket.io connection to MtGox
//
var ioc = require('socket.io-client');
var serverUrl = 'https://socketio.mtgox.com:443/mtgox';
var conn = ioc.connect(serverUrl);

conn.on('connect',    onConnect);
conn.on('disconnect', onDisconnect);
conn.on('error',      onError);
conn.on('message',    onMessage);

function onConnect(msg)
{
	if (conn.socket.connected) {
		sub = {"channel":ch_depth,"op":"subscribe"};
		conn.send(sub);
		sub = {"channel":ch_trades,"op":"subscribe"};
		conn.send(sub);
		sub = {"channel":ch_ticker,"op":"subscribe"};
		conn.send(sub);
		console.log('CONNECTED : ' + serverUrl);
	}
}
function onError(msg)
{
	console.log('MSG ERROR :' + serverUrl);
}
function onDisconnect(msg)
{
	console.log('DISCONNECTED : ' + serverUrl);
}
function onMessage(msg)
{
	//relay the message to all connected clients
	//console.log(msg);
	gabb.emit('message',msg);

	//keep local depth data updated
	if (msg.channel == ch_depth)
	{
		if(typeof(msg.depth) !== 'undefined')
		{
			var p_depth = parseFloat(parseFloat(msg.depth.price).toFixed(2)); //round to the nearest cent 
			if (msg.depth.type_str == 'bid')
			{
				bid_depth[msg.depth.price] = parseFloat(msg.depth.total_volume_int) / 100000000.0;
				ask_depth[msg.depth.price] = 0.0;
			}
			if (msg.depth.type_str == 'ask')
			{
				bid_depth[msg.depth.price] = 0.0;
				ask_depth[msg.depth.price] = parseFloat(msg.depth.total_volume_int) / 100000000.0;
			}
		}
	}

	//keep local depth data updated
	if (msg.channel == ch_trades)
	{
		if(typeof(msg.trade) !== 'undefined')
		{
			if (msg.trade.price_currency == 'USD')
			{
                //add the trade to the buffer - used for 1min reporting
				trade_buffer.push({'volume':msg.trade.amount, 'price':msg.trade.price});
				console.log('server.js: ch_trades-amt: ' + msg.trade.amount + ', ch_trades-price: ' + msg.trade.price);
			}
		}
	}

}

// send the 1 min volume weighted trade data
function log_one_min_trade()
{
	var volume = 0;
	var weighted = 0;
	var t = Date.now();
	trade_buffer.forEach(function(trade){
		volume += parseFloat(trade.volume);
		weighted += parseFloat(trade.volume) * parseFloat(trade.price);
	});
	trade_buffer = []; //clear the buffer
	if (volume > 0)
	{
        	weighted = weighted / volume;
		gabb.emit('message', {'channel':'1min','price':weighted,'volume':volume,'time':(new Date).getTime()});
        	console.log('server.js: 1min price: ' + weighted + ', 1min volume: ' + volume);
	}
}


//periodically send data pulled from the xmlrpc server (gene server)
function xmlrpcBroadcastBridge()
{
	var pid = "NODEJS";
	var gene_def_hash = "";
	// Sends a method call to the XML-RPC server
	rpcClient.methodCall('get_default_gene_def_hash', [], function (error, value) {	
	    gene_def_hash = value.replace(/"/g,""); 
	    //console.log('get default gene hash response: ' + value);
		rpcClient.methodCall('pid_register_client', [pid, gene_def_hash], function (error, value) {
			//client is registered - now pull the data
			rpcClient.methodCall('get_target', [pid], function (error, value) {
				//console.log('get target response: ' + value +', '+ pid +', '+ gene_def_hash);
				gabb.emit('message', {'channel':'target_bid','price':value,'gene_def_hash':gene_def_hash});
			});
			rpcClient.methodCall('get_pids', [], function (error, value) {
				//console.log('get pids response: ' + value);
				gabb.emit('message', {'channel':'pids','value':JSON.parse(value)});
			});
		});

	});	
}

// periodic timers
setInterval(log_one_min_trade, 60000); //60 second interval
setInterval(xmlrpcBroadcastBridge, 10000); //10 second interval
