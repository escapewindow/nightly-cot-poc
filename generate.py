#!/usr/bin/env python

import asyncio
from asyncio.subprocess import PIPE
import json
import os
import pgpy
import pprint

BASEDIR = os.path.abspath(os.path.dirname(__file__))


def get_keyring():
    return pgpy.PGPKeyring(
        os.path.join(BASEDIR, 'gpg', 'pub.gpg'),
        os.path.join(BASEDIR, 'gpg', 'sec.gpg'),
    )


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
        shas[k] = parts[1]
    return shas


async def create_manifest(job_type):
    job_dir = os.path.join(BASEDIR, job_type, 'artifacts')
    shas = await get_file_shas(job_dir)
    return shas  # XXX


async def async_main():
    job_type = 'decision'
    pprint.pprint(await create_manifest(job_type))


def main(name=None):
    if name in (None, __name__):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(async_main())
        loop.close()


main(name=__name__)
