#!/usr/bin/env python
""" Quick and dirty test gpg key generation script, for scriptworker testing
"""
import gnupg
import logging
import os
# import pexpect
import pprint
import subprocess
import tempfile

log = logging.getLogger(__name__)

# Constants {{{1
GPG = '/usr/local/bin/gpg'
MY_EMAIL = "scriptworker@example.com"
KEYS_TO_TRUST = ('decision.root@example.com', 'build.root@example.com', 'docker.root@example.com')
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


# generate_keys {{{1
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


# update_trust {{{1
def update_trust(gpg_path, gpg_home, emails):
    log.info("Updating ownertrust...")
    ownertrust = []
    trustdb = os.path.join(gpg_home, "trustdb.gpg")
    if os.path.exists(trustdb):
        os.remove(trustdb)
    # trust MY_EMAIL ultimately
    ownertrust.append("{}:6\n".format(emails[MY_EMAIL]))
    for email in KEYS_TO_TRUST:
        ownertrust.append("{}:5\n".format(emails[email]))
    ownertrust = ''.join(ownertrust).encode('utf-8')
    print(ownertrust)
    cmd = [
        gpg_path,
        "--homedir", gpg_home,
        "--no-default-keyring",
        "--secret-keyring", os.path.join(gpg_home, "secring.gpg"),
        "--keyring", os.path.join(gpg_home, "pubring.gpg"),
        "--import-ownertrust"
    ]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout = p.communicate(input=ownertrust)[0]
    if stdout:
        log.info("gpg output:\n{}".format(stdout))
    assert not p.returncode
    print(subprocess.check_output(
    [
        gpg_path,
        "--homedir", gpg_home,
        "--no-default-keyring",
        "--secret-keyring", os.path.join(gpg_home, "secring.gpg"),
        "--keyring", os.path.join(gpg_home, "pubring.gpg"),
        "--export-ownertrust"
    ]))


# main {{{1
def main(name=None):
    log.setLevel(logging.INFO)
    log.addHandler(logging.StreamHandler())
    tmpdir = tempfile.mkdtemp()
    #with tempfile.TemporaryDirectory() as tmpdir:
    try:
        gpg = gnupg.GPG(gnupghome=tmpdir)
        gpg.encoding = 'utf-8'
        fingerprints = generate_keys(gpg)
        emails = {v: k for k, v in fingerprints.items()}
        update_trust(GPG, tmpdir, emails)
        for key in gpg.list_keys():
            email = fingerprints[key['fingerprint']]
            path = os.path.join(tmpdir, email)
            write_key(gpg, key['keyid'], path)
        # TODO tests!
    finally:
        log.info("Files are in {}".format(tmpdir))


main()
