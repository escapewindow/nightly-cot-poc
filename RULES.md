chain of trust artifact creation
--------------------------------

* chain-of-trust.json:

```json
{
    "artifacts": {
        "name1": "SHA256:...",
        "name2": "SHA256:...",
    },
    "taskId": "...",
    "runId": "...",
    "task": {
    },
    "chainOfTrust": [{
        "url": "...",
        "checksum": "SHA256:..."
    }, {
        "url": "...",
        "checksum": "SHA256:..."
    }],
    "extra": {
        "dockerChecksum": "SHA256:...",
        "dockerImageBuilder": {
            "taskId": "...",
            "runId": "...",
        }
    }
}
```
 * signed.

* full-chain-of-trust.json:
 * a list of the above chain-of-trust.json files, and signed.
 * we could do this per-task, or have a report-generator task at the end that conglomerates, reports on auditable information / instance ids / etc.


decision
--------
* number of decision tasks per task group == 1
 * multiple runs are ok.
* workerType == gecko-decision
* signed with non-revoked 'docker' key
* TODO: record the docker image sha, verify sha against whitelist
 * there is no docker image builder task, because it's downloaded from docker hub
* artifact sums: anything used in the rules.
* non-interactive task defn
* revision
 * matches the other jobs
 * valid repo

### full graph verification
* the task json matches the graph in taskcluster: no added tasks?
 * TODO: deal with multiple successful runs of the decision task.


build
-----
* number of each type of build task per task group == 1
 * multiple runs are ok.
* verify the sha/link of the decision task cot artifact
* verify the docker sha -- whitelist of known (decision task, docker image builder)
 * follow link to docker image builder task + verify the signature if its cot artifact
 * if not known, it's ok if we have a signed docker image builder cot artifact from a whitelisted docker sha
* build task matches the task.json
* non-interactive task defn
* revision
 * matches the other jobs
 * valid repo


other checks
------------
* do we care about valid workerId?  schedulerId?  whitelists?
