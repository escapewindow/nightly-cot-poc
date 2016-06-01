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
os.chmod(gpghome, 0o700)
print(gpghome)
gpg = gnupg.GPG(gpgbinary='gpg2', gnupghome=gpghome, verbose=True)
gpg.encoding = 'utf-8'
print(gpg.list_keys())
print(dir(gpg))
for f in ("decision.gpg", "decision_cleartext.gpg"):
    with open(os.path.join("cot", f), "rb") as fh:
        verified = gpg.verify_file(fh)
        print("{} {}".format(f, verified))
