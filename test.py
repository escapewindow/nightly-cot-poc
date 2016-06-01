#!/usr/bin/env python

import glob
import gnupg
import os

#contents = ""

#with open("foo.gpg", "r") as fh:
#    contents = fh.read()
#    while True:
#        line = fh.readline()
#        if not line:
#            break
#        if line.startswith('-') or line.startswith('Version'):
#            continue
#        contents += line.rstrip()

#print(contents)
gpghome = os.path.join(os.getcwd(), 'gpg')
print(gpghome)
gpg = gnupg.GPG(gpgbinary='gpg2', gnupghome=gpghome)
gpg.encoding = 'utf-8'
print(gpg.list_keys())
#kr = pgpy.PGPKeyring(glob.glob('gpg/*.gpg'))
#message = pgpy.PGPMessage.from_file('decision.gpg')
#print(message.is_signed)
#print(message.signatures)
#with kr.key('docker1') as key:
#    print(key.verify(message))
with open("decision.gpg", "r") as fh:
    print(gpg.verify_file(fh))
