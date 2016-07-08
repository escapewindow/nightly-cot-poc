#!/usr/bin/env python
"""Convert a cleartext-signed message into an ascii-armored message.
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
    print(body)


main(name=__name__)
