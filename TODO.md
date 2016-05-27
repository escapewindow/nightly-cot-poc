docker-worker
-------------

* put the header of live-backing.log in a machine-readable format?  esp docker image info
 * artifact with docker sha, and link to docker builder task if applicable. (taskId/runId?)
* download and sum the previous chain, possibly create full-cot.json
* save the task.json, upload as artifact
* create chain-of-trust artifact(s), sign, and upload as artifact.  this includes checksums for all other artifacts.

decision task
-------------
* dependent chain of trust links.  for signing, that would be decision, build. docker will be retrieved from build artifacts.
