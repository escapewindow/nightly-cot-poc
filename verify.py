#!/usr/bin/env python

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
message = pgpy.PGPMessage.from_file('decision.gpg')
print(message.is_signed)
print(message.signatures)
with kr.key('docker1') as key:
    print(key.verify(message))

#message = pgpy.PGPMessage.from_file('decision_cleartext.gpg')
#with kr.key('docker1') as key:
#    print(key.verify(message))
