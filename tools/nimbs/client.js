// example node.js client implementation


var ch_depth = '24e67e0d-1cad-4cc0-9e7a-f8523ef460fe'
var ch_trades = 'dbf1dee9-4f2e-4a08-8cb7-748919a71b21'
var ch_ticker = 'd5f06780-30a8-4a48-a2f8-7ed181b4a13f'

var io = require('socket.io-client');
var serverUrl = 'http://localhost:8080/ga_bitbot';
var conn = io.connect(serverUrl);


var p1 = "asdfasdf"

conn.emit('call', p1, function(resp, data) {
    console.log('server sent resp code ' + resp);
});


conn.on('message', onMessage);
function onMessage(msg)
{
//	if (msg.channel == ch_depth){console.log(msg);}
	if (msg.channel == ch_trades){console.log(msg);}
	if (msg.channel == ch_ticker){console.log(msg);}
}
