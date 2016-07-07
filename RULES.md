chain of trust artifact creation
--------------------------------

* certificate.json:

```json
{
  "artifacts": [{
    "name": "public/...",
    "hash": "sha256:...",
  }, {
    ...
  }],
  "taskId": "...",
  "runId": "...",
  "workerGroup": "...",
  "workerId": "...",
  "task": {
    // task definition
  },
  "extra": {
    "imageArtifactSha": "sha256:...",
    ...
  }
}
```
 * gpg cleartext signed (e.g., "-----BEGIN PGP SIGNED MESSAGE-----"...)


decision
--------
* workerType == gecko-decision
* certificate signed with non-revoked gecko-decision key
* verify docker image sha against whitelist
 * there is no docker image builder task, because it's downloaded from docker hub
* artifact sums: anything used in the rules.
* non-interactive task defn
* revision
 * matches the other jobs
 * valid repo
* task.payload.features.generateCertificate is True?

build
-----
* verify the sha/link of the decision task cot artifact
* verify the docker sha -- whitelist of known (decision task, docker image builder)
 * follow link to docker image builder task + verify the signature of its cot artifact
 * if not known, it's ok if we have a signed docker image builder cot artifact from a whitelisted docker sha
* build task definition + taskid matches the full-task.json?
* non-interactive task defn
* revision
 * matches the other jobs
 * valid repo
* task.payload.features.generateCertificate is True?


other checks
------------
* do we care about valid workerId?  schedulerId?  whitelists?

* the signing task is part of the task-graph?
* signing task.payload.features.generateCertificate is True?
