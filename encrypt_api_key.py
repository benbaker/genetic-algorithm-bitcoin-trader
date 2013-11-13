
"""
encrypt_api_key v0.01

genetic trade simulator

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


from Crypto.Cipher import AES
from Crypto import Random
import hashlib
import json
import time
import random

print "\n\nga-bitbot API Key Encryptor v0.1a"
print "-" * 30
print "\n\n"

print "Enter the API KEY:"
key = raw_input()

print "\nEnter the API SECRET KEY:"
secret = raw_input()

print "\n\nEnter an encryption password:"
print "(This is the password ga-bitbot will require to execute trades)"
password = raw_input()


print "\n"
try:
    f = open('./config/salt.txt','r')
    salt = f.read()
    f.close()
    print "Using the current local password salt..."
except:
    print "Generating the local password salt..."
    pre_salt = str(time.time() * random.random() * 1000000) + 'H7gfJ8756Jg7HBJGtbnm856gnnblkjiINBMBV734'
    salt = hashlib.sha512(pre_salt).digest()
    f = open('./config/salt.txt','w')
    f.write(salt)
    f.close()



print "\n"
print "Generating the encrypted API KEY file..."
hash_pass = hashlib.sha256(password + salt).digest()
iv = Random.new().read(AES.block_size)
encryptor = AES.new(hash_pass, AES.MODE_CBC,iv)
text = json.dumps({"key":key,"secret":secret})
#pad the text
pad_len = 16 - len(text)%16
text += " " * pad_len
ciphertext = iv + encryptor.encrypt(text)   #prepend the iv parameter to the encrypted data
f = open('./config/api_key.txt','w')
f.write(ciphertext)
f.close()

print "Verifying encrypted file..."
f = open('./config/api_key.txt','r')
d = f.read()
f.close()
f = open('./config/salt.txt','r')
salt = f.read()
f.close()
hash_pass = hashlib.sha256(password + salt).digest()
decryptor = AES.new(hash_pass, AES.MODE_CBC,d[:AES.block_size])
text = decryptor.decrypt(d[AES.block_size:])
try:
    d = json.loads(text)
except:
    print "Failed verification...try again."
else:
    print "Verification complete."
    print "\nDon't forget your password:",password," This is what ga-bitbot will request to enable automated trading."


