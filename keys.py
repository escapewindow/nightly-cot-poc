#!/usr/bin/env python
""" Quick and dirty test gpg key generation script, for scriptworker testing
"""
import gnupg
import os
import pprint
import tempfile

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
    ascii_armored_public_key = gpg.export_keys(keyid)
    with open("{}.pub".format(path), "w") as fh:
        print(ascii_armored_public_key, file=fh)
    ascii_armored_private_key = gpg.export_keys(keyid, True)
    with open("{}.sec".format(path), "w") as fh:
        print(ascii_armored_private_key, file=fh)


# main {{{1
def main(name=None):
    fingerprints = {}
    with tempfile.TemporaryDirectory() as tmpdir:
        gpg = gnupg.GPG(gnupghome=tmpdir)
        gpg.encoding = 'utf-8'
        for key_tuple in KEY_DATA:
            k = dict(zip(("name_real", "name_comment", "name_email"), key_tuple))
            k['key_length'] = 2048
            key = gpg.gen_key(gpg.gen_key_input(**k))
            fingerprints[key.fingerprint] = k['name_email']
        emails = {v: k for k, v in fingerprints.items()}
        pprint.pprint(fingerprints)
        pprint.pprint(emails)
        for key in gpg.list_keys():
            path = os.path.join("/tmp", fingerprints[key['fingerprint']])
            write_key(gpg, key['keyid'], path)


main()
