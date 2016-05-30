docker-worker
-------------

* put the header of live-backing.log in a machine-readable format?  esp docker image info
 * artifact with docker sha, and link to docker builder task if applicable. (taskId/runId?)
* download and sum the previous chain, possibly create full-cot.json
* save the task.json, to embed in chain-of-trust artifact -- needed to verify original request + non-interactive etc
* create chain-of-trust artifact(s), sign, and upload as artifact.  this includes checksums for all other artifacts.
* disable ssh to the worker. ensure any interactive docker session shows it in the task definition.

decision task
-------------
* dependent chain of trust artifact links in task definitions.  for signing, that would be decision, build. docker will be retrieved from build artifacts.
* `"enableChainOfTrust": true` in the worker instructions

docker image builder
--------------------
* ASK: signed by a different key than docker worker?  (run on a different ami?)
* ASK: is this going to be added to the graph at decision task time, or appended later?
 * appending will have full graph verification consequences

docker hub
----------
* we need the decision docker image sha in a whitelist, so 1. build 2. upload 3. communicate sha to releng 4. receive ack that sha was added to whitelist 5. change to new docker image
* the docker image builder's docker image sha will also be whitelisted, so same as above.
* do we run tests on these whitelisted docker images?
 * no ssh, logic matches a certain repo's settings

queue
-----
* We have urls like https://queue.taskcluster.net/v1/task/DgnGMqNVTM2gwZN6rVvwhA/artifacts/public/build/target.tar.bz2 for tests, I imagine so we don't care which runId generates the artifact.  For the Chain of Trust, we can use the latest, but we need to archive an immutable url.
 * ASK: Is there a way to get a unique url from the queue for a given artifact?

worker gpg keys
---------------
* root gpg key(s): child keys must be signed by at least N keys in a whitelist?  Split keys, 3/5 key shards needed to sign something?
* families of keys: scriptworker, docker worker.  hooks keytype?
* a way to generate a new, limited lifespan key every time we create a new worker AMI
* a way to revoke keys and check for revocation


