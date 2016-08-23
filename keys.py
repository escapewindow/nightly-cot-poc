#!/usr/bin/env python
""" Quick and dirty test gpg key generation script, for scriptworker testing
Written against homebrew gpg 2.0.30 and libgcrypt 1.7.3 on osx 10.11.6
"""
# TODO:
#  X verify that gpg.conf actually makes my key default -- signature with no key specified
#    used the default key
#  _ sign the trusted keys with my key
#  _ sign the embedded keys with the appropriate trusted key
#  _ verify the exported keys have the signatures still
#  _ verify trust! sign something with each key. everything should be a valid
#    signature except the unknown key
#  _ verify trust without private keys imported: create a new gpg home with
#    only the appropriate pubkeys to verify
#  _ cmdln args?  delete tmpdir, where to write the keys, verbosity, location of gpg binary
#  _ tests for version of gpg; docs for same
#  _ should we even use python-gnupg or just wrap gpg for everything in this script?
#  _ library reusability?
import gnupg
import logging
import os
import pexpect
import pprint
import subprocess
import sys
import tempfile

log = logging.getLogger(__name__)

# Constants {{{1
GPG = '/usr/local/bin/gpg'
MY_EMAIL = "scriptworker@example.com"
TRUSTED_EMAILS = ('decision.root@example.com', 'build.root@example.com', 'docker.root@example.com')
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
TEST_DATA = (
    ("decision@example.com", "decision.root@example.com"),
    ("build@example.com", "build.root@example.com"),
    ("docker@example.com", "docker.root@example.com"),
)


# write_keys {{{1
def write_keys(gpg, tmpdir, fingerprints):
    """ Write ascii armored keys to tmpdir/keys
    """
    keydir = os.path.join(tmpdir, "keys")
    log.info("Writing keys...")
    os.makedirs(keydir)
    for key in gpg.list_keys():
        email = fingerprints[key['fingerprint']]
        keyid = key['keyid']
        path = os.path.join(keydir, email)
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


# create_gpg_conf {{{1
def create_gpg_conf(tmpdir, emails):
    """ Use my key by default
    """
    with open(os.path.join(tmpdir, "gpg.conf"), "w") as fh:
        print("default-key {}".format(emails[MY_EMAIL]), file=fh)


# gpg_default_args {{{1
def gpg_default_args(gpg_home):
    return [
        "--homedir", gpg_home,
        "--no-default-keyring",
        "--secret-keyring", os.path.join(gpg_home, "secring.gpg"),
        "--keyring", os.path.join(gpg_home, "pubring.gpg"),
    ]


# update_trust {{{1
def update_trust(gpg_path, gpg_home, emails):
    """ Trust my key ultimately; TRUSTED_EMAILS fully
    """
    log.info("Updating ownertrust...")
    ownertrust = []
    trustdb = os.path.join(gpg_home, "trustdb.gpg")
    if os.path.exists(trustdb):
        os.remove(trustdb)
    # trust MY_EMAIL ultimately
    ownertrust.append("{}:6\n".format(emails[MY_EMAIL]))
    # Trust TRUSTED_EMAILS fully.  That means they will need to be signed
    # by my key, and then any key they sign will be valid.
    for email in TRUSTED_EMAILS:
        ownertrust.append("{}:5\n".format(emails[email]))
    log.debug(pprint.pformat(ownertrust))
    ownertrust = ''.join(ownertrust).encode('utf-8')
    cmd = [gpg_path] + gpg_default_args(gpg_home) + ["--import-ownertrust"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout = p.communicate(input=ownertrust)[0]
    if p.returncode:
        if stdout:
            log.critical("gpg output:\n{}".format(stdout.decode('utf-8')))
        sys.exit(p.returncode)
    log.debug(subprocess.check_output(
        [gpg_path] + gpg_default_args(gpg_home) + ["--export-ownertrust"]).decode('utf-8')
    )


# sign_keys {{{1
def sign_keys(gpg_path, gpg_home, emails, exportable=False):
    """Sign the keys marked by 'emails'.
    """
    if exportable:
        first_arg = "--sign-key"
    else:
        first_arg = "--lsign-key"
    for email in emails:
        cmd_args = gpg_default_args(gpg_home) + [first_arg, email]
        log.info("{} {}".format(gpg_path, cmd_args))
        child = pexpect.spawn(gpg_path, cmd_args)
        child.expect(b".*Really sign\? \(y/N\) ")
        child.sendline(b'y')
        child.interact()
        child.close()
        if child.exitstatus != 0 or child.signalstatus is not None:
            raise Exception("Failed signing {}! exit {} signal {}".format(email, child.exitstatus, child.signalstatus))


# sign_message {{{1
def sign_message(gpg, key, message, path):
    with open(path, "w") as fh:
        signed = gpg.sign(message, keyid=key)
        print(signed, file=fh)
        return path


# main {{{1
def main(name=None):
    log.setLevel(logging.INFO)
    log.addHandler(logging.StreamHandler())
    tmpdir = tempfile.mkdtemp()
    try:
        gpg = gnupg.GPG(gnupghome=tmpdir)
        gpg.encoding = 'utf-8'
        fingerprints_dict = generate_keys(gpg)
        emails_dict = {v: k for k, v in fingerprints_dict.items()}
        create_gpg_conf(tmpdir, emails_dict)
        update_trust(GPG, tmpdir, emails_dict)
        sign_keys(GPG, tmpdir, TRUSTED_EMAILS)
        write_keys(gpg, tmpdir, fingerprints_dict)
        for num, val in enumerate(TEST_DATA):
            log.info("Signing with {}".format(val[0]))
            signed = sign_message(gpg, val[0], str(num), os.path.join(tmpdir, "{}.gpg".format(str(num))))
            log.info("verifying...")
            with open(signed, "rb") as fh:
                verified = gpg.verify_file(fh)
            print(verified.trust_text)
            print(verified.username)
            print(verified.key_id)
            print(verified.signature_id)
#            for prop in ('username', 'key_id', 'signature_id', 'fingerprint', 'trust_level', 'trust_text'):
#                log.info(verified.getattr(prop))
    finally:
        # remove tmpdir?
        log.info("Files are in {}".format(tmpdir))
        import shutil
        shutil.rmtree(tmpdir)


main()
