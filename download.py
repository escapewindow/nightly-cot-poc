#!/usr/bin/env python

import aiohttp
import asyncio
import hashlib
import json
import logging
from optparse import Values
import os
import pprint
import re
import shutil
import sys
from taskcluster.async import Queue
from taskcluster.utils import calculateSleepTime
import tempfile

log = logging.getLogger(__name__)
BASEDIR = os.path.abspath(os.path.dirname(__file__))
WORKER_TO_GPG_KEY = {
    "gecko-decision": "decision1",
    "opt-linux64": "docker1",
    "image-builder": "DockerImageBuilder",  # fake workerType
}
WHITELIST_DOCKER_IMAGE_NAMES = (
    "taskcluster/decision:0.1.0",
)
# Ugly. Until docker-worker embeds this info, use regex on live.log
DOCKER_HUB_REGEX = re.compile(r"""Digest: (sha256:[0-9a-f]+)$""")
DOCKER_IMAGE_ARTIFACT_REGEX = r"""\[taskcluster [0-9-:Z\. ]+\] Image '{path}' from task '{taskId}' loaded\.  Using image ID (sha256:[0-9a-f]+)\.$"""


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


async def retry_async(func, attempts=5, sleeptime_callback=None,
                      retry_exceptions=(Exception, ), args=(), kwargs=None):
    kwargs = kwargs or {}
    sleeptime_callback = sleeptime_callback or calculateSleepTime
    attempt = 1
    while True:
        try:
            log.debug("retry_async: Calling {}, attempt {}".format(func, attempt))
            return await func(*args, **kwargs)
        except retry_exceptions:
            attempt += 1
            if attempt > attempts:
                log.warning("retry_async: {}: too many retries!".format(func))
                raise
            log.debug("retry_async: {}: sleeping before retry".format(func))
            await asyncio.sleep(sleeptime_callback(attempt))


# download_artifacts {{{1
async def get_artifact(context, artifact_defn, task_id, hash_alg="sha256"):
    log.debug("Getting %s %s", task_id, artifact_defn["name"])
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
    sha = hashlib.new(hash_alg)
    async with context.session.get(signed_url) as resp:
        with open(path, "wb") as fh:
            while True:
                chunk = await resp.content.read(2048)
                if not chunk:
                    break
                fh.write(chunk)
                sha.update(chunk)
    return artifact_defn['name'], sha.hexdigest


def get_status(context, task_id):
    task_status = await context.queue.status(task_id)
    if task_status['status']['state'] != 'completed' or task_status['status']['runs'][-1]['state'] != 'completed':
        raise Exception("Task {} not completed!\n{}".format(task_id, pprint.pformat(task_status)))
    return task_status


def get_docker_image_sha(task_id, task_defn):
    if task_defn['payload']['image'] in WHITELIST_DOCKER_IMAGE_NAMES:
        regex = DOCKER_HUB_REGEX
    else:
        regex = re.compile(DOCKER_IMAGE_ARTIFACT_REGEX.format(
            path=task_defn['payload']['image']['path'],
            taskId=task_defn['payload']['image']['taskId'],
        ))
    path = "{}/public/logs/live.log".format(task_id)
    with open(path, "r") as fh:
        line = fh.readline()
        while line:
            m = regex.match(line)
            if m is not None:
                return m.group(1)
            line = fh.readline()
        else:
            raise Exception("Can't find docker image sha in %s!" % path)


def build_cot(context, artifact_dict, task_id, task_status=None):
    task_status = task_status or get_task_status(context, task_id)
    task_defn = await context.queue.task(task_id)
    # hack in cot flag until it's built in
    task_defn['payload']['features']['generateCertificate'] = True
    # Generate CoT artifact
    extra = {
        "imageArtifactSha256": get_docker_image_sha(task_id, task_defn)
    }
    with open("{}/task.json".format(task_id), "w") as fh:
        print(dump_json(task_defn), file=fh, end='')
    cot = {
        "artifacts": [],
        "task": task_defn,
        "task_id": task_id,
    }
    assert task_id == task_status['status']['taskId']
    cot["runId"] = task_status['status']['runs'][-1]['runId']
    cot["workerGroup"] = task_status['status']['runs'][-1]['workerGroup']
    cot["workerId"] = task_status['status']['runs'][-1]['workerId']
    cot["extra"] = kwargs
    # TODO


async def download_artifacts(context, task_id):
    artifact_list = await context.queue.listLatestArtifacts(task_id)
    async_tasks = []
    artifact_dict = {}
    for artifact_defn in artifact_list['artifacts']:
        async_tasks.append(
            asyncio.ensure_future(
                retry_async(get_artifact, args=(context, artifact_defn, task_id))
            )
        )
    await asyncio.wait(async_tasks)
    for task in async_tasks:
        exc = task.exception()
        if exc is not None:
            raise exc
        name, sha = task.result()
        artifact_dict[name] = sha
    return artifact_dict


# main {{{1
async def async_main(context):
    rm(context.decision_task_id)
    log.info("Decision task %s", context.decision_task_id)
    decision_task_status = get_status(context, task_id)
    artifact_dict = await download_artifacts(context, context.decision_task_id)
    graph_path = "{}/public/task-graph.json".format(context.decision_task_id)
    # TODO hack signing task defn in
    build_cot(context, artifact_dict, task_id, task_status=decision_task_status)
    # TODO do the same for build(s)
    # TODO do the same for BZpO3hsUQvyXH6On1wnfRw (docker image builder)
    #      build_task_defn['payload']['image']['taskId']


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
        gpghome = os.path.join(os.getcwd(), 'gpg')
        os.chmod(context.gpghome, 0o700)
        context.gpg = gnupg.GPG(gpgbinary='gpg2', gnupghome=gnupghome)
        context.gpg.encoding = 'utf-8'
        credentials = {
            'credentials': {
                'clientId': os.environ["TASKCLUSTER_CLIENT_ID"],
                'accessToken': os.environ["TASKCLUSTER_ACCESS_TOKEN"],
            }
        }
        loop = asyncio.get_event_loop()
        try:
            os.chdir("build")
            with aiohttp.ClientSession() as context.session:
                context.queue = Queue(credentials, session=context.session)
                context.decision_task_id = sys.argv[1]
                loop.run_until_complete(async_main(context))
        finally:
            os.chdir(orig_dir)
            loop.close()


main(name=__name__)
