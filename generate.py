#!/usr/bin/env python

import asyncio
from asyncio.subprocess import PIPE
from contextlib import contextmanager
import glob
import json
import os
import pgpy

BASEDIR = os.path.abspath(os.path.dirname(__file__))


# {{{1 misc
def dump_json(obj):
    return json.dumps(obj, indent=2, sort_keys=True)


# {{{1 get_output
async def get_output(cmd, path):
    print("Running {} in {}".format(cmd, path))
    kwargs = {
        'stdout': PIPE,
        'stderr': PIPE,
        'stdin': None,
        'close_fds': True,
        'preexec_fn': lambda: os.setsid(),
        'cwd': path,
    }
    proc = await asyncio.create_subprocess_exec(*cmd, **kwargs)
    output_lines = []
    while True:
        line = await proc.stdout.readline()
        if line:
            output_lines.append(line.decode('utf-8').rstrip())
        else:
            break
    error_lines = await proc.stderr.read()
    if error_lines:
        raise OSError(error_lines)
    return output_lines


# {{{1 gpg
def get_keyring(gpg_dir):
    return pgpy.PGPKeyring(glob.glob(os.path.join(gpg_dir, '*.gpg')))


@contextmanager
def get_key(key_id, keyring):
    with keyring.key(key_id) as key:
        yield key


def sign(string, key):
    message = pgpy.PGPMessage.new(string, cleartext=True)
    # XXX a passphrase protected key will require an unlock
    message |= key.sign(message)
    return message


# {{{1 create_cot
async def get_file_shas(job_dir):
    file_list = await get_output(['find', '.', '-type', 'f'], job_dir)
    shas = {}
    futures = {}
    for f in file_list:
        path = f.replace('./', '')
        # use get_output() instead of hashlib because async
        futures[path] = asyncio.ensure_future(get_output(['openssl', 'sha256', f], job_dir))
    await asyncio.wait(futures.values())
    for k, v in futures.items():
        parts = v.result()[0].split('= ')
        shas[k] = "SHA256:{}".format(parts[1])
    return shas


def get_task_defn(job_dir):
    with open(os.path.join(job_dir, 'public', 'taskcluster', 'task.json')) as fh:
        return json.load(fh)


async def create_cot(job_type):
    job_dir = os.path.join(BASEDIR, job_type, 'artifacts')
    cot = {}
    cot['artifacts'] = await get_file_shas(job_dir)
    cot['task'] = get_task_defn(job_dir)
    # XXX real docker image shas + Docker Artifact Image Builder CoT
    cot['extra'] = {
        'dockerChecksum': "XXX DOCKER SHA {}".format(cot['task']['workerType'])
    }
    if 'decision' not in cot['task']['workerType']:
        cot['extra']['dockerImageBuilder'] = {
            'taskId': 'dockerImageBuilder',
            'runId': 0
        }
    # XXX real taskId + runId
    cot['taskId'] = "taskId{}".format(cot['task']['workerType'])
    cot['runId'] = 0
    return cot


# {{{1 main
async def async_main():
    unsigned = []
    keyring = get_keyring(os.path.join(BASEDIR, "gpg"))
    for job_type in ('decision', 'build'):
        cot = await create_cot(job_type)
        # XXX we'll need to make this unique because there will be duplicated
        # jobs in dependency chains.  decision task at the front, this
        # job at the end.
        unsigned.append(cot)
        with open("{}.txt".format(job_type), "w") as fh:
            print(dump_json(cot), file=fh, end="")
        with get_key('docker1', keyring) as key:
            signed_cot_str = sign(dump_json(unsigned), key)
        with open("{}.gpg".format(job_type), "w") as fh:
            print(signed_cot_str, file=fh, end="")


def main(name=None):
    if name in (None, __name__):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(async_main())
        loop.close()


main(name=__name__)
