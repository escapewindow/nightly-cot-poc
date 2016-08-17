#!/usr/bin/env python
""" Quick and dirty test gpg key generation script, for scriptworker testing
"""
import gnupg
import logging
import os
import pprint
import tempfile

log = logging.getLogger(__name__)

# Constants {{{1
MY_EMAIL = "scriptworker@example.com"
KEYS_TO_TRUST = ('decision.root@example.com', 'build.root@example.com', 'docker.root@example.com')
KEY_DIR = "/tmp"
KEY_DATA = (
    # Root keys.  These sign the embedded keys.  We trust the root keys, and
    # the signature makes the embedded keys valid.
    ("Decision Root", "root key for the decision task keys", "decision.root@example.com"),
    ("Build Root", "root key for the build task keys", "build.root@example.com"),
    ("Docker Root", "root key for the docker task keys", "docker.root@example.com"),

    # Embedded keys.  These represent the keys that are baked into the
    # worker AMIs.
    ("Decision Embedded", "embedded key for the decision ami", "decision@example.com"),
    ("Build Embedded", "embedded key for the build ami", "build@example.com"),
    ("Docker Embedded", "embedded key for the docker ami", "docker@example.com"),

    # This is the key scriptworker will use to sign its own CoT.
    ("Scriptworker Local", "embedded key for the scriptworker", "scriptworker@example.com"),

    # This is an orphaned, untrusted key.  Could also be evil.com.
    ("Invalid key", "Some random key", "unknown@example.com"),
)


# write_key {{{1
def write_key(gpg, keyid, path):
    """ Write the pub and sec keys for keyid to path.pub and path.sec
    """
    log.info("Writing keys to %s.{pub,sec}" % path)
    ascii_armored_public_key = gpg.export_keys(keyid)
    with open("{}.pub".format(path), "w") as fh:
        print(ascii_armored_public_key, file=fh)
    ascii_armored_private_key = gpg.export_keys(keyid, True)
    with open("{}.sec".format(path), "w") as fh:
        print(ascii_armored_private_key, file=fh)


def generate_keys(gpg):
    """ Generate the gpg keys from KEY_DATA
    """
    log.info("Generating keys...")
    fingerprints = {}
    for key_tuple in KEY_DATA:
        k = dict(zip(("name_real", "name_comment", "name_email"), key_tuple))
        k['key_length'] = 2048
        key = gpg.gen_key(gpg.gen_key_input(**k))
        fingerprints[key.fingerprint] = k['name_email']
    return fingerprints


# main {{{1
def main(name=None):
    log.setLevel(logging.INFO)
    log.addHandler(logging.StreamHandler())
    with tempfile.TemporaryDirectory() as tmpdir:
        gpg = gnupg.GPG(gnupghome=tmpdir)
        gpg.encoding = 'utf-8'
        fingerprints = generate_keys(gpg)
        emails = {v: k for k, v in fingerprints.items()}
        for key in gpg.list_keys():
            path = os.path.join(KEY_DIR, fingerprints[key['fingerprint']])
            write_key(gpg, key['keyid'], path)
        # TODO trust MY_EMAIL
        # TODO sign KEYS_TO_TRUST
        # TODO tests!


main()
