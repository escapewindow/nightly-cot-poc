#!/usr/bin/env python

import asyncio
from asyncio.subprocess import PIPE
import json
import os
import pgpy
import pprint

BASEDIR = os.path.abspath(os.path.dirname(__file__))


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
def get_keyring():
    return pgpy.PGPKeyring(
        os.path.join(BASEDIR, 'gpg', 'pub.gpg'),
        os.path.join(BASEDIR, 'gpg', 'sec.gpg'),
    )



# {{{1 create_cot
async def get_file_shas(job_dir):
    file_list = await get_output(['find', '.', '-type', 'f'], job_dir)
    shas = {}
    futures = {}
    for f in file_list:
        path = f.replace('./', '')
        # use get_output() instead of hashlib because async
        futures[f] = asyncio.ensure_future(get_output(['openssl', 'sha256', f], job_dir))
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
    cot['extras'] = {}
    cot['artifacts'] = await get_file_shas(job_dir)
    cot['task'] = get_task_defn(job_dir)
    cot['extras']['dockerChecksum'] = "TODO DOCKER SHA {}".format(cot['task']['workerType'])
    # TODO taskId
    # TODO runId
    # TODO previousCoT
    # TODO sign
    return cot


# {{{1 main
async def async_main():
    job_type = 'decision'
    pprint.pprint(await create_cot(job_type))


def main(name=None):
    if name in (None, __name__):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(async_main())
        loop.close()


main(name=__name__)
