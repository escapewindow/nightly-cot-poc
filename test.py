#!/usr/bin/env python

import glob
import gnupg
import os

def get_body(clearsign_fh):
    """The gpg2 man page recommends not using clearsigning, but instead
    detached signatures or ascii armored files.  If we proceed with clearsigning
    for human readability and single download, we might use something like this:
    """
    in_body = False
    lines_to_skip = 0
    body = []
    for line in clearsign_fh:
        bareline = line.rstrip()
        if bareline == '-----BEGIN PGP SIGNED MESSAGE-----':
            in_body = True
            lines_to_skip = 2
            continue
        if in_body:
            if lines_to_skip:
                lines_to_skip -= 1
                continue
            if bareline == '-----BEGIN PGP SIGNATURE-----':
                break
            body.append(line)
    else:
        raise ValueError("Missing signature!")
    return ''.join(body)

gpghome = os.path.join(os.getcwd(), 'gpg')
os.chmod(gpghome, 0o700)
# gpg = gnupg.GPG(gpgbinary='gpg2', gnupghome=gpghome, verbose=True)
gpg = gnupg.GPG(gpgbinary='gpg2', gnupghome=gpghome)
gpg.encoding = 'utf-8'
print(dir(gpg))
for f in ("decision.gpg", "decision_cleartext.gpg"):
    with open(os.path.join("cot", f), "rb") as fh:
        verified = gpg.verify_file(fh)
        print("{} {} {} {} {}".format(f, verified.valid, verified.status, verified.key_id, verified.username))
        if verified.status not in ('signature good', "signature valid"):  # XXX only signature good for production
            print("Not a good signature!")

with open(os.path.join("cot", "decision_cleartext.gpg"), "r") as fh:
    print(get_body(fh))
with open("test.py", "r") as fh:
    print(get_body(fh))
