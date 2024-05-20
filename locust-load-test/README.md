# Running Locust tests

## Poetry
To run the locust test in poetry, you first must have the filing-api running (poetry run uvicorn main:app --reload --port 8888).  The pyproject.toml specifies configuration of the
locust runtime in [tool.locust].  See https://docs.locust.io/en/stable/configuration.html if you want to change parameters to alter test runs.  The filing_api_locust.py script has
default os.getenv values to run in this environment.

A report.html is written to the locust-load-test/reports directory

## Docker
The docker image can be run locally in two ways.
- Running `sh docker_build_and_run.sh`.  This will run in headless mode, so essentially a 'one off' run of the test that connects to the filing-api container that is started with docker compose (see https://github.com/cfpb/sbl-project/blob/main/LOCAL_DEV_COMPOSE.md).  A report.html is written to the locust-load-test/reports directory

- Running in docker compose from the https://github.com/cfpb/sbl-project/tree/main repo.  This starts up a Web UI version of locust that can be reached via http://localhost:8089/.  Tests can then be ran repeatedly via the Web UI.

## Kubernetes
Helm chart overrides can be found in the internal EKS repo.