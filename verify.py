#!/usr/bin/env python

import base64
import glob
import pgpy

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
kr = pgpy.PGPKeyring(glob.glob('gpg/*ring.gpg'))
message = pgpy.PGPMessage.from_file('cot/decision.gpg')
print(message.is_encrypted)
print(message.is_signed)
print(message.signatures)
with kr.key('docker1') as key:
    print(key.verify(message))

sig = message.signatures[0]

#print(str(sig))
print(str(message.message))
#message |= message.signatures[0]

#message = pgpy.PGPMessage.from_file('decision_cleartext.gpg')
#with kr.key('docker1') as key:
#    print(key.verify(message))
