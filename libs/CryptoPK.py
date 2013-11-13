"""
CryptoPK v0.01

Cryptographic Public Key Code Signing/Verification Classes Based on RSASSA-PKCS1-v1_5 

    Features a complete digital signature/verification implementation
    
    If no RSA key pair exists then one will be created automatically

    A signed package is a json dictionary containing:
     - RSA public key
     - base64 encoded signature (RSA4096 encrypted SHA512 hash of the plain text and package name)
     - base64 encoded plain text data (may be zlib compressed)
     - MD5 hash of the plain text
     - package name
     - compression flag

    The signature guarantees the origin of the package contents to the owner of the public key
    

Copyright 2013 Brian Monkaba

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
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA512
from Crypto.Hash import MD5
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
from Crypto import Random
import hashlib
import base64
import json
import zlib
import random
import time
import logging
import sys
import getpass

logger = logging.getLogger(__name__)


class CryptoPKSign:
    def __init__(self,key_path=''):
        self.key_path = key_path
        self.pub = ''
        self.prv = ''
        self.prv_key_locked = True
        try: #load existing priv/pub key pair if available
            f = open(self.key_path + 'public.key')
            self.pub = f.read()
            f.close()
            f = open(self.key_path + 'private.key')
            self.prv = f.read()
            f.close()
        except: #if no key pair exists then create one
            logger.info("CryptoPKSign:__init__: no existing keys found, generating a new key pair")
            self.__gen_key_pair()   
        return

    def __gen_key_pair(self):
        import os
        #generate a public/private key pair
        self.rsa=RSA.generate(4096,os.urandom)
        self.pub = self.rsa.publickey().exportKey() #public key
        self.prv = self.rsa.exportKey() #private key
        #save the key pair
        f = open(self.key_path + 'public.key','w')
        f.write(self.pub)
        f.close()
        f = open(self.key_path + 'private.key','w')
        f.write(self.prv)
        f.close()

    def unlock_private_key(self):
        if self.prv_key_locked == True:
            #decrypts the private key
            try: #load the salt file
                f = open(self.key_path+'salt.txt','r')
                salt = f.read()
                f.close()
                logger.info("CryptoPKSign:__init__: salt loaded")
            except: #salt file not found, generate a new salt
                pre_salt = str(time.time() * random.random() * 1000000) + 'H7gfJ8756Jg7HBJGtbnm856gnnblkjiINBMBV734'
                salt = hashlib.sha512(pre_salt).digest()
                f = open(self.key_path+'salt.txt','w')
                f.write(salt)
                f.close()
                logger.info("CryptoPKSign:__init__: new salt file generated")
            if self.prv.find('BEGIN RSA PRIVATE KEY') > -1:#check to see if the private key is encrypted
                logger.warning("CryptoPKSign:__init__: non-enrypted private key found")
                print "\n\nPrivate key is not encrypted\nEnter a new password to encrypt the private key:"
                password = raw_input()
                hash_pass = hashlib.sha256(password + salt).digest()
                iv = Random.new().read(AES.block_size)
                encryptor = AES.new(hash_pass, AES.MODE_CBC,iv)
                text = json.dumps(self.prv)
                pad_len = 16 - len(text)%16 #pad the text
                text += " " * pad_len
                ciphertext = iv + encryptor.encrypt(text)   #prepend the iv parameter to the encrypted data
                f = open(self.key_path + 'private.key','w')
                f.write(ciphertext)
                f.close()
            else:
                #request password to decrypt private key
                print "\n\nEnter the private key password:"
                password = getpass.getpass()
                hash_pass = hashlib.sha256(password + salt).digest()
                decryptor = AES.new(hash_pass, AES.MODE_CBC,self.prv[:AES.block_size])
                text = decryptor.decrypt(self.prv[AES.block_size:])
                try:
                    self.prv = json.loads(text)
                except:
                    logger.error("CryptoPKSign:unlock_private_key: invalid password or corrupted encrypted private key file found")
                    sys.exit()
        self.prv_key_locked = False
        return

    def sign(self,plain_text,package_name='',compress_package=False):
        #returns a public key signed package as a json string

        self.unlock_private_key()

        #MD5 is intended to be used by receivers who wish to validate that they have the latest package.
        md=MD5.new(plain_text).hexdigest() 
        h=SHA512.new(plain_text + package_name + md + str(compress_package))
        key = RSA.importKey(self.prv) #import the private key
        signature = base64.b64encode(PKCS1_v1_5.new(key).sign(h)) #sign & convert to base64 encoding
        if compress_package == True:
            plain_text = zlib.compress(plain_text,9)
        str_d = json.dumps({'public_key':self.pub,'signature':signature,'plain_text':base64.b64encode(plain_text),'package_name':package_name,'MD5':md,'compressed':compress_package})
        return str_d 

    def sign_file(self,filename,package_name='',compress_package=False):
        try:
            f = open(filename)
        except:
            raise Exception("CryptoPKSign:sign_file:ERROR: file not found")
            
        plain_text = f.read()
        f.close()
        return self.sign(plain_text,package_name,compress_package)

class CryptoPKVerify:
    def __init__(self,package,trusted_keys = []):
        #package is the json output created by CryptoPKSign.sign
        #if verification fails the plain text will not be made available
        #trusted_keys is a list of trusted public keys
        self.plain_text = ''
        self.verified = False
        self.trusted_source = False
        self.md5 = ''
        try:
            package = json.loads(package)
        except:
            raise Exception("CryptoPKVerify:__init__:ERROR: package json loading failed")
        self.package_name = package['package_name']
        if package['public_key'] in trusted_keys:
            self.trusted_source = True
            #check to see if package is compressed
            if package['compressed'] == True:
                try:
                    plain_text = zlib.decompress(base64.b64decode(package['plain_text']))
                except:
                    raise Exception("CryptoPKVerify:__init__:ERROR: package decompression failed")
            else:
                try:
                    plain_text = base64.b64decode(package['plain_text'])
                except:
                    raise Exception("CryptoPKVerify:__init__:ERROR: package base64 decoding failed")
            #verify the MD5 hash sent inside the package
            self.md5 = MD5.new(plain_text).hexdigest()
            if self.md5 != package['MD5']:
                raise Exception("CryptoPKVerify:__init__:ERROR: package MD5 verification failed") 
            #verify the package
            key = RSA.importKey(package['public_key'])
            h=SHA512.new(plain_text + self.package_name + package['MD5'] + str(package['compressed']))
            self.verified = PKCS1_v1_5.new(key).verify(h,base64.b64decode(package['signature']))
            if self.verified:
                self.plain_text = plain_text
            return

    def verify_local_file(self,filename = ''):
        if filename == '':
            #use the implied filename from the package_name
            filename = self.package_name
        if self.verified == False:
            raise Exception("CryptoPKVerify:verify_local_file:ERROR: package failed verifiction")
        if self.trusted_source == False:
            raise Exception("CryptoPKVerify:verify_local_file:ERROR: package is from an untrusted source")
        try:        
            f = open(filename)
            local_plain_text = f.read()     
            f.close()
        except:
            logger.info("CryptoPKVerify:verify_local_file: local file does not exist")
            return False

        if MD5.new(local_plain_text).hexdigest() == self.md5:
            logger.info("CryptoPKVerify:verify_local_file: local file is up to date")
            return True
        else:
            logger.info("CryptoPKVerify:verify_local_file: local file is out of date")
            return False

    def update_local_file(self,filename = ''):
        if self.verify_local_file(filename) == False and self.verified: #verified test is redundant but better safe than sorry :)
            #package is valid and local file either does not exist or is out of date
            #update the file
            if filename == '':
                #use the implied filename from the package_name
                filename = self.package_name
            f = open(filename,'w')
            f.write(self.plain_text)
            f.close()
            logger.info("CryptoPKVerify:update_local_file: local file is now up to date")
        else:
            logger.info("CryptoPKVerify:update_local_file: local file is already up to date")
        return True

if __name__ == '__main__':
    print "*"*80
    print "Cryptographic public key code signing/verification class library"
    print "based on RSASSA-PKCS1-v1_5"
    print "Testing module..."
    print "*"*80
    print "CryptoPK:__main__:INFO: Signing a package"
    signer = CryptoPKSign()
    trusted_keys = [signer.pub] #in real world use the trusted keys are provided, this is for testing only
    package = signer.sign('I am not sure if this is at all correct.')
    print "CryptoPK:__main__:INFO: Verifying the package"
    receiver = CryptoPKVerify(package,trusted_keys)
    if receiver.verified: #should pass
        print "CryptoPK:__main__:INFO: Package verified."
        print "CryptoPK:__main__:INFO: Plain text: ",receiver.plain_text
    else:
        print "CryptoPK:__main__:INFO: Package verification failed."
        print "CryptoPK:__main__:INFO: Plain text: ",receiver.plain_text

    print "CryptoPK:__main__:INFO: Corrupting the public key" 
    package = package[:64] + 'A' + package[65:]
    package = package[:90] + '1' + package[91:]

    receiver = CryptoPKVerify(package,trusted_keys)
    if receiver.verified: #should fail
        print "CryptoPK:__main__:INFO: Package verified."
        print "CryptoPK:__main__:INFO: Plain text: ",receiver.plain_text
    else:
        print "CryptoPK:__main__:INFO: Package verification failed."
        #if verification fails plain text will not be available
        print "CryptoPK:__main__:INFO: Plain text: ",receiver.plain_text

    print "CryptoPK:__main__:INFO: Using an untrusted public key" 
    trusted_keys2 = []  
    receiver = CryptoPKVerify(package,trusted_keys2)
    if receiver.verified: #should fail
        print "CryptoPK:__main__:INFO: Package verified."
        print "CryptoPK:__main__:INFO: Plain text: ",receiver.plain_text
    else:
        print "CryptoPK:__main__:INFO: Package verification failed."
        #if verification fails plain text will not be available
        print "CryptoPK:__main__:INFO: Plain text: ",receiver.plain_text

    #quick visual benchmark
    print "CryptoPK:__main__:INFO: Signing 100 messages"
    signer = CryptoPKSign()
    pkg_lst = []
    for i in xrange(100):
        pkg_lst.append(signer.sign(str(i)+'kjhsdkfhglksdjghkl'+('*'*1200)+'sdjfghklsdjghklsdjfg'+str(i)))

    print "CryptoPK:__main__:INFO: Verifying 100 messages"
    pass_count = 0
    for pkg in pkg_lst:
        receiver = CryptoPKVerify(pkg,trusted_keys)
        if receiver.verified:
            pass_count += 1

    print "CryptoPK:__main__:INFO: Messages verified:",pass_count

    print "CryptoPK:__main__:INFO: Signing this module"
    package = CryptoPKSign().sign(open('CryptoPK.py').read(),'CryptoPK.py')
    receiver = CryptoPKVerify(package,trusted_keys)
    if receiver.verified: #should pass
        print "CryptoPK:__main__:INFO: Package verified."
        #print "Plain text: ",receiver.plain_text
    else:
        print "CryptoPK:__main__:INFO: Package verification failed."
        #print "Plain text: ",receiver.plain_text
    print "CryptoPK:__main__:INFO: Uncompressed package length:",len(package)

    print "CryptoPK:__main__:INFO: Signing this module - compressed package"
    package = CryptoPKSign().sign(open('CryptoPK.py').read(),'CryptoPK.py',compress_package=True)
    receiver = CryptoPKVerify(package,trusted_keys)
    if receiver.verified: #should pass
        print "CryptoPK:__main__:INFO: Package verified."
        #print "Plain text: ",receiver.plain_text
    else:
        print "CryptoPK:__main__:INFO: Package verification failed."
        #print "Plain text: ",receiver.plain_text
    print "CryptoPK:__main__:INFO: Compressed length:",len(package)

    print "CryptoPK:__main__:INFO: Verifying status of local files..."
    receiver.verify_local_file('CryptoPK.py') #explicit filename
    receiver.verify_local_file()                #implied filename from package name
    receiver.verify_local_file('asdf')          #file not found
    #receiver.verify_local_file('sign.py')       #file out of date (difference found)

    receiver.update_local_file('asdf')          #file not found, will create a new one with the package contents
    print "CryptoPK:__main__:INFO:"+" -"*20 + ' START OF PACKAGE DUMP ' + "-"*20
    print package
    print "CryptoPK:__main__:INFO:"+" -"*20 + ' END OF PACKAGE DUMP ' + "-"*20
    #print "CryptoPK:__main__:INFO: Saving the test package"
    #f = open('test_package.txt','w')
    #f.write(package)
    #f.close()

