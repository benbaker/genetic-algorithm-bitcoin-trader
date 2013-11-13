#!/bin/bash       
cd config
redis-server redis.conf &
cd ..
pypy gal.py xlclient &
