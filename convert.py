#!/usr/bin/env python
"""Convert a cleartext-signed message into an ascii-armored message.
https://lists.gnupg.org/pipermail/gnupg-users/2007-June/031414.html
"""
import gnupg
import hashlib
import json
import logging
from optparse import Values
import os
import subprocess
import sys
import tempfile

log = logging.getLogger(__name__)


def get_output(cmd, valid_codes=(0, ), **kwargs):
    """Run ``cmd``, then raise ``subprocess.CalledProcessError`` on non-zero
    exit code, or return stdout text on zero exit code.
    """
    log.debug("Getting output from {}".format(cmd))
    try:
        outfile = tempfile.TemporaryFile()
        proc = subprocess.Popen(cmd, stdout=outfile, **kwargs)
        rc = proc.wait()
        outfile.seek(0)
        output = outfile.read().decode('utf-8')
        if rc in valid_codes:
            return output
        else:
            print(output)
            error = subprocess.CalledProcessError(proc.returncode, cmd)
            error.output = error
            raise error
    finally:
        outfile.close()


def get_body(path):
    """The gpg2 man page recommends not using clearsigning, but instead
    detached signatures or ascii armored files.  If we proceed with clearsigning
    for human readability and single download, we might use something like this:
    """
    try:
        _, temppath = tempfile.mkstemp()
        os.remove(temppath)
        subprocess.check_call(
            './gpg.sh -u me --output {} < {}'.format(temppath, path), shell=True
        )
        with open(temppath, "r") as fh:
            body = fh.read()
    finally:
        os.remove(temppath)
    return body


def get_sig(clearsign_fh):
    """The gpg2 man page recommends not using clearsigning, but instead
    detached signatures or ascii armored files.  If we proceed with clearsigning
    for human readability and single download, we might use something like this:
    """
    in_sig = False
    sig = []
    for line in clearsign_fh:
        bareline = line.rstrip()
        if bareline == '-----BEGIN PGP SIGNATURE-----':
            in_sig = True
        if in_sig:
            sig.append(line)
            if bareline == '-----END PGP SIGNATURE-----':
                break
    if not sig:
        raise ValueError("Missing signature!")
    return ''.join(sig)


# main {{{1
def main(name=None):
    if name not in (None, __name__):
        return
    if len(sys.argv) != 2:
        print("Usage: {} FILENAME".format(sys.argv[0]), file=sys.stderr)
        sys.exit(1)
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)8s - %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    log.addHandler(handler)
    gnupghome = os.path.join(os.getcwd(), 'gpg')
    os.chmod(gnupghome, 0o700)
    gpg = gnupg.GPG(gpgbinary='gpg2', options=["--local-user", "me"], gnupghome=gnupghome)
    gpg.encoding = 'utf-8'

    with open(sys.argv[1], "r") as fh:
        contents = fh.read()
    verified = gpg.verify(contents)
    print(dir(verified))
    print(verified.valid)
    print(verified.key_id)
    print(verified.status)
    body = get_body(sys.argv[1])
    if body.endswith('\n') or body.endswith('\r'):
        body = body[:-1]
    with open("text_part", "w") as fh:
        print(body, file=fh, end='')
    with open(sys.argv[1], "r") as fh:
        with open("sig_part", "w") as out:
            print(get_sig(fh), file=out, end='')
    subprocess.check_call(
        './gpg.sh --output sig_part.gpg --dearmor < sig_part', shell=True
    )
    subprocess.check_call(
        ['./gpg.sh', '-z0', '--textmode', '--store', 'text_part']
    )
    subprocess.check_call(
        'cat sig_part.gpg text_part.gpg > my_new_file.gpg', shell=True
    )
    with open("my_new_file.gpg", "rb") as fh:
        contents = fh.read()
    verified = gpg.verify(contents)
    print(dir(verified))
    print(verified.valid)
    print(verified.key_id)
    print(verified.status)


main(name=__name__)
