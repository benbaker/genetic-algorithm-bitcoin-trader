#!/bin/bash          
cd config
redis-server redis.conf &
cd ..
pypy gal.py all &
sleep 6
cd tools
cd nimbs
node server.js &
cd ..
cd ..
sleep 10
python -mwebbrowser http://127.0.0.1:8088/#tab-10 &
pypy bid_maker.py

