#!/usr/bin/env python

import aiohttp
import asyncio
import json
import logging
from optparse import Values
import os
import pprint
import shutil
import sys
from taskcluster.async import Queue
import tempfile

log = logging.getLogger(__name__)
BASEDIR = os.path.abspath(os.path.dirname(__file__))
WORKER_TO_GPG_KEY = {
    "gecko-decision": "decision1",
    "opt-linux64": "docker1",
    "image-builder": "DockerImageBuilder",  # fake workerType
}


# helper functions {{{1
def dump_json(obj):
    return json.dumps(obj, indent=2, sort_keys=True)


def rm(path):
    log.debug("rm %s", path)
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    assert not os.path.exists(path)


def makedirs(path):
    log.debug("makedirs %s", path)
    try:
        os.makedirs(path)
    except OSError:
        pass
    assert os.path.isdir(path)


async def get_artifact(context, artifact_defn, task_id):
    path = "{}/{}".format(task_id, artifact_defn['name'])
    parent_dir = '/'.join(path.split('/')[:-1])
    makedirs(parent_dir)
    unsigned_url = context.queue.buildUrl(
        methodName='getLatestArtifact',
        replDict={
            'taskId': task_id,
            'name': artifact_defn['name'],
        }
    )
    signed_url = context.queue.buildSignedUrl(requestUrl=unsigned_url)
    async with context.session.get(signed_url) as resp:
        with open(path, "wb") as fh:
            while True:
                chunk = await resp.content.read(2048)
                if not chunk:
                    break
                fh.write(chunk)


# download_artifacts {{{1
async def download_artifacts(context, task_id):
    task_status = await context.queue.status(task_id)
    if task_status['status']['state'] != 'completed':
        raise Exception("Task {} not completed!\n{}".format(task_id, pprint.pformat(task_status)))
    artifact_list = await context.queue.listLatestArtifacts(task_id)
    async_tasks = []
    for artifact_defn in artifact_list['artifacts']:
        async_tasks.append(
            asyncio.ensure_future(get_artifact(context, artifact_defn, task_id))
        )
    await asyncio.wait(async_tasks)
    for task in async_tasks:
        exc = task.exception()
        if exc is not None:
            raise exc

    sys.exit(0)
    task_defn = await context.queue.task(task_id)
    return task_defn


# main {{{1
async def async_main(context):
    rm(context.decision_task_id)
    log.info("Decision task %s", context.decision_task_id)
    await download_artifacts(context, context.decision_task_id)


def main(name=None):
    if name in (None, __name__):
        if len(sys.argv) != 2:
            print("Usage: {} DECISION_TASK_ID".format(sys.argv[0]), file=sys.stderr)
            sys.exit(1)
        log.setLevel(logging.DEBUG)
        log.addHandler(logging.StreamHandler())
        makedirs("build")
        orig_dir = os.getcwd()
        context = Values()
        credentials = {
            'credentials': {
                'clientId': os.environ["TASKCLUSTER_CLIENT_ID"],
                'accessToken': os.environ["TASKCLUSTER_ACCESS_TOKEN"],
            }
        }
        try:
            os.chdir("build")
            with aiohttp.ClientSession() as context.session:
                context.queue = Queue(credentials, session=context.session)
                context.decision_task_id = sys.argv[1]
                loop = asyncio.get_event_loop()
                loop.run_until_complete(async_main(context))
                loop.close()
        finally:
            os.chdir(orig_dir)


main(name=__name__)
