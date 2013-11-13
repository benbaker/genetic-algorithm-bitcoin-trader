"""
cpsu v0.01

ga-bitbot Cryptographic Package Signing Utility

    This utility can cryptographicaly sign packages and upload them to the gene server
    or download and verify packages from the gene server 
    
    If no RSA key pair already exists then one will be created automatically

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

import sys
import paths
import CryptoPK
import xmlrpclib
import gene_server_config
from os import listdir
from os.path import isfile, join


__server__ = gene_server_config.__server__
__port__ = str(gene_server_config.__port__)

print "ga-bitbot Cryptographic Package Signing Utility"

if len(sys.argv) >= 3:
    operation = sys.argv[1]    #valid operations are: sign,get
    package_name = sys.argv[2]
    trusted_key_path = ''
    if len(sys.argv) >= 4:
        trusted_key_path = sys.argv[3]
else:
    print "\nUseage: python cpsu.py [operation] [package] [trusted_keys]\n\n"
    print "Operation options:\n\tsign\t\tsign and upload a package to the gene server\n\n\tget\t\trequest a package from the gene server"
    print "\t\t\tthis operation requires trusted_keys"
    print "\nPackage:\n\tIn the case of this utility, the package is simply a file name"
    print "\nTrusted Keys:\n\tFile path to a directory containing the public keys trusted by the user"
    print "\nExamples:\n\tpython cpsu.py get bct.py './config/trusted_public_keys/'"
    print "\tpython cpsu.py sign mycode.py"
    sys.exit()

#make sure the port number matches the server.
server = xmlrpclib.Server('http://' + __server__ + ":" + __port__)
print "cpsu: connected to",__server__,":",__port__

if operation == 'sign':
    signer = CryptoPK.CryptoPKSign('./config/') #path to the signers key pair
    try:
        package = signer.sign_file(package_name,package_name=package_name,compress_package=True)
    except:
        print "cpsu:Error: Could not sign file, check that the file name given exists."
    else:
        print "cpsu:Info:Package created"
        try:
            if server.put_signed_package(package) == 'OK':
                print "cpsu:Info:Package uploaded to gene server"
        except:
            print "cpsu:Error: Could not upload package to the gene server. Verify the server is running and try again."

elif operation == 'get':
    package = server.get_signed_package(package_name)
    if package != "NOK":
        trusted_keys = []
        trusted_key_files = [fn for fn in listdir(trusted_key_path) if isfile(join(trusted_key_path,fn))]
        for fn in trusted_key_files: #load the trusted keys
            if fn.split('.')[1] == 'key': #only read in '.key' files
                f = open(trusted_key_path+fn)
                key = f.read()
                f.close()
                trusted_keys.append(key)
        receiver = CryptoPK.CryptoPKVerify(package,trusted_keys)
        if receiver.verified: #should pass
            receiver.update_local_file()
            print "cpsu:Info:Package verified and up to date."
        else:
            print "cpsu:Info:Package failed verification"
            print "cpsu:Info:- Either the public key isn't trusted or the package contents have been modified since it was signed."
    else:
        print "cpsu:Warning: Package not found"
else:
    print "cpsu:Error: Invalid operation"


