#!/bin/bash          
cd config
redis-server redis.conf &
cd ..
pypy gal.py server &
sleep 5
cd tools
cd nimbs
node server.js &
cd ..
cd ..
sleep 3
pypy bid_maker.py

