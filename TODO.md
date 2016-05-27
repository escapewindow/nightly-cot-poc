docker-worker
-------------

* put the header of live-backing.log in a machine-readable format?  esp docker image info
 * artifact with docker sha, and link to docker builder task if applicable. (taskId/runId?)
* download and sum the previous chain, possibly create full-cot.json
* save the task.json, to embed in chain-of-trust artifact -- needed to verify original request + non-interactive etc
* create chain-of-trust artifact(s), sign, and upload as artifact.  this includes checksums for all other artifacts.

decision task
-------------
* dependent chain of trust artifact links in task definitions.  for signing, that would be decision, build. docker will be retrieved from build artifacts.
* `"enableChainOfTrust": true` in the worker instructions
