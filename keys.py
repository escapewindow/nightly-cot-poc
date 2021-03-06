#!/usr/bin/env python
""" Quick and dirty test gpg key generation script, for scriptworker testing
Written against homebrew gpg 2.0.30 and libgcrypt 1.7.3 on osx 10.11.6
"""
# TODO:
#  X verify that gpg.conf actually makes my key default -- signature with no key specified
#    used the default key
#  X sign the trusted keys with my key
#  X sign the embedded keys with the appropriate trusted key
#  _ verify the exported keys have the signatures still
#  X verify trust! sign something with each key. everything should be a valid
#    signature except the unknown key
#  _ verify trust without private keys imported: create a new gpg home with
#    only the appropriate pubkeys to verify
#  _ cmdln args?  delete tmpdir, where to write the keys, verbosity, location of gpg binary
#  _ tests for version of gpg; docs for same
#  _ library reusability?
#  _ new pub keyrings per git dir
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
TRUSTED_EMAILS = ("docker.root@example.com", )
KEY_DATA = (
    # Format: (name, comment, email, [expire])

    # Root keys.  These sign the embedded keys.  We trust the root keys, and
    # the signature makes the embedded keys valid.
    ("Docker Root", "root key for the docker task keys", "docker.root@example.com"),

    # Embedded keys.  These represent the keys that are baked into the
    # worker AMIs.
    ("Docker Embedded", "embedded key for the docker ami", "docker@example.com", "1d"),

    # This is the key scriptworker will use to sign its own CoT.
    ("Scriptworker Test", "test key for scriptworker", "scriptworker@example.com"),

    # This is an orphaned, untrusted key.  Could also be evil.com.
    ("Invalid key", "Some random key", "unknown@example.com"),
)
SUBKEY_DATA = (
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
def generate_keys(gpg, key_data):
    """ Generate the gpg keys from KEY_DATA
    """
    log.info("Generating keys...")
    fingerprints = {}
    for key_tuple in key_data:
        k = dict(zip(("name_real", "name_comment", "name_email", "expire_date"), key_tuple))
        k.setdefault('key_length', 4096)
        key = gpg.gen_key(gpg.gen_key_input(**k))
        fingerprints[key.fingerprint] = k['name_email']
    return fingerprints


# create_gpg_conf {{{1
def create_gpg_conf(tmpdir, my_fingerprint):
    """ set sec team guidelines; use my key by default
    """
    with open(os.path.join(tmpdir, "gpg.conf"), "w") as fh:
        # https://wiki.mozilla.org/Security/Guidelines/Key_Management#GnuPG_settings
        print("personal-digest-preferences SHA512 SHA384\n"
              "cert-digest-algo SHA256\n"
              "default-preference-list SHA512 SHA384 AES256 ZLIB BZIP2 ZIP Uncompressed\n"
              "keyid-format 0xlong\n", file=fh)
        # default key
        print("default-key {}".format(my_fingerprint), file=fh)


# gpg_default_args {{{1
def gpg_default_args(gpg_home):
    return [
        "--homedir", gpg_home,
        "--no-default-keyring",
        "--secret-keyring", os.path.join(gpg_home, "secring.gpg"),
        "--keyring", os.path.join(gpg_home, "pubring.gpg"),
    ]


# update_trust {{{1
def update_trust(gpg_path, gpg_home, emails, my_fingerprint, trusted_fingerprints):
    """ Trust my key ultimately; trusted_fingerprints fully
    """
    log.info("Updating ownertrust...")
    ownertrust = []
    trustdb = os.path.join(gpg_home, "trustdb.gpg")
    if os.path.exists(trustdb):
        os.remove(trustdb)
    # trust my_fingerprint ultimately
    ownertrust.append("{}:6\n".format(my_fingerprint))
    # Trust trusted_fingerprints fully.  That means they will need to be signed
    # by my key, and then any key they sign will be valid.
    for fingerprint in trusted_fingerprints:
        ownertrust.append("{}:5\n".format(fingerprint))
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


# sign_key {{{1
def sign_key(gpg_path, gpg_home, email, signing_key=None):
    """Sign the keys marked by 'emails'.
    """
    args = []
    if signing_key:
        args.extend(['-u', signing_key])
        log.info("Signing {} with {}...".format(email, signing_key))
    else:
        log.info("Signing {}...".format(email))
    args.append("--lsign-key")
    args.append(email)
    cmd_args = gpg_default_args(gpg_home) + args
    child = pexpect.spawn(gpg_path, cmd_args)
    child.expect(b".*Really sign\? \(y/N\) ")
    child.sendline(b'y')
    i = child.expect([pexpect.EOF, pexpect.TIMEOUT])
    if i != 0:
        raise Exception("Failed signing {}! Timeout".format(email))
    else:
        child.close()
        if child.exitstatus != 0 or child.signalstatus is not None:
            raise Exception("Failed signing {}! exit {} signal {}".format(email, child.exitstatus, child.signalstatus))


# sign_keys {{{1
def sign_keys(gpg_path, gpg_home, trusted_emails, subkey_data):
    for email in trusted_emails:
        sign_key(gpg_path, gpg_home, email)
    for params in subkey_data:
        sign_key(gpg_path, gpg_home, params[0], signing_key=params[1])


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
        fingerprints_dict = generate_keys(gpg, KEY_DATA)
        emails_dict = {v: k for k, v in fingerprints_dict.items()}
        create_gpg_conf(tmpdir, emails_dict[MY_EMAIL])
        update_trust(GPG, tmpdir, emails_dict, emails_dict[MY_EMAIL],
                     [emails_dict[email] for email in TRUSTED_EMAILS])
        sign_keys(GPG, tmpdir, TRUSTED_EMAILS, SUBKEY_DATA)
        write_keys(gpg, tmpdir, fingerprints_dict)
        for num, val in enumerate(SUBKEY_DATA):
            log.info("Signing with {}".format(val[0]))
            signed = sign_message(gpg, val[0], str(num), os.path.join(tmpdir, "{}.gpg".format(str(num))))
            log.info("verifying...")
            with open(signed, "rb") as fh:
                verified = gpg.verify_file(fh)
            print(verified.trust_text)
            print(verified.username)
            cmd = [GPG] + gpg_default_args(tmpdir) + ["-v", os.path.join(tmpdir, "{}.gpg".format(str(num)))]
            subprocess.check_call(cmd)
#            print(verified.key_id)
#            print(verified.signature_id)
            # TODO --list-sigs or --check-sigs, then parse the text output for meaning :( :( :(
            # give up on verifying which signature path for now?
    finally:
        # remove tmpdir?
        log.info("Files are in {}".format(tmpdir))
#        import shutil
#        shutil.rmtree(tmpdir)


main()
