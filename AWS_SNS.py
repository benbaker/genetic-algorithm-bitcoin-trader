"""
AWS_SNS v0.01

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

try:
    import boto
except:
    print "AWS_SNS requires the boto package to be installed. Visit http://code.google.com/p/boto/ for downloads."
    import sys
    sys.exit()



from contextlib import closing
from Crypto.Cipher import AES
import getpass
import base64
import hmac
import hashlib
import time
import json
import urllib
import urllib2
import urlparse

class ServerError(Exception):
    def __init__(self, ret):
        self.ret = ret
    def __str__(self):
        return "Server error: %s" % self.ret
class UserError(Exception):
    def __init__(self, errmsg):
        self.errmsg = errmsg
    def __str__(self):
        return self.errmsg

class Client:
    def __init__(self, enc_password=""):
        if enc_password == "":
            print "AWS_SNS: Enter your AWS file encryption password."
            enc_password = getpass.getpass()#raw_input()
        try:
            f = open('./config/salt.txt','r')
            salt = f.read()
            f.close()
            hash_pass = hashlib.sha256(enc_password + salt).digest()

            f = open('./config/aws_api_key.txt')
            ciphertext = f.read()
            f.close()
            decryptor = AES.new(hash_pass, AES.MODE_CBC,ciphertext[:AES.block_size])
            plaintext = decryptor.decrypt(ciphertext[AES.block_size:])
            d = json.loads(plaintext)
            self.key = d['key']
            self.secret = d['secret']
            self.topic_arn = d['topic_arn']
        except:
            print "\n\n\nError: you may have entered an invalid password or the encrypted api key file doesn't exist"
            print "If you haven't yet generated the encrypted key file, run the encrypt_aws_key.py script.\n"
            print "Note: Text messaging services requires an AWS subscription with Amazon.com"
            while 1:
                pass

        self.connection = boto.connect_sns(self.key, self.secret)

    def send(self,text_message):
        return self.connection.publish(topic=self.topic_arn,message=text_message)

if __name__ == "__main__":
    def ppdict(d):
        #pretty print a dict
        print "-"*40
        try:
            for key in d.keys():
                print key,':',d[key]
        except:
            print d
        return d

    def pwdict(d,filename):
        #pretty write a dict
        f = open(filename,'w')
        try:
            for key in d.keys():
                f.write(key + " : " + str(d[key]) + "\n")
        except:
            pass
        f.write('\n' + '-'*80 + '\n')
        f.write(str(d))
        f.close()
        return d

    print "\nAWS_SNS module test"
    c = Client()
    b = ppdict(pwdict(c.send('AWS_SNS module test'),'./test_data/aws_send.txt'))
    print "test message sent."
    print "done."


