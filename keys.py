#!/usr/bin/env python
""" Quick and dirty test gpg key generation script, for scriptworker testing
"""
import gnupg
import os
import pprint
import tempfile

# Data {{{1
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
)


# main {{{1
def main(name=None):
    with tempfile.TemporaryDirectory() as tmpdir:
        gpg = gnupg.GPG(gnupghome=tmpdir)
        for key_tuple in KEY_DATA:
            k = dict(zip(("name_real", "name_comment", "name_email"), key_tuple))
            k['key_length'] = 2048
            gpg.gen_key(gpg.gen_key_input(**k))
        pprint.pprint(gpg.list_keys())
        pprint.pprint(gpg.list_keys(True))


main()
