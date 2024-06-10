# Running Locust tests

## Testing Data
The locust tests rely on a set of files located in the https://github.com/cfpb/sbl-test-data repo.
- The locust-sblars folder contains a list of sblar files that are randomly selected for testing the POST submission endpoint
- The test_leis folder contains a test_leis.json file that contains a list of LEIs randomly selected to use for the endpoints.  The name of the file used for the LEIs can be configured using the `LEI_FILE` filename.

The name of the repos for both pulling random SBLARs and the LEIs file can be configured using the env vars `SBLAR_REPO` and `LEI_REPO`, respectively.

## Test Scripts
The locust scripts that can be ran for the load balancing tests can be found in the locust_scripts folder.  Which script is ran is configured in the configs/filing-api.conf file.  To change which script to run, update the following in the filing-api.conf:
- `locustfile = locust_scripts/filing_api_locust.py`

For example, if you want to run the just_submissions.py test, which tests just the latest submission endpoints, the filing-api.conf should read:
- `locustfile = locust_scripts/just_submissions.py`

## Poetry
The command to run Locust using poetry is `poetry run locust` from the root of the repo.

The default configuration of locust when running the command can be found in the pyproject.toml under [tool.locust].  See https://docs.locust.io/en/stable/configuration.html to learn more about each of the configs.
Of main importance are the config variables `locustfile` mentioned above, and the `host` config.

If you are running poetry locust tests locally, you first must have the filing-api running (poetry run uvicorn main:app --reload --port 8888).  If you use the EKS cluster host, make sure the service is running.

Env variables that you want to modify you will need to set in your environment first.  For example, `export LEI_FILE=my_test_leis.json`

A report.html is written to the locust-load-test/reports directory

## Docker
The docker image can be run locally in two ways.
- Running `sh docker_build_and_run.sh`.  This will run in headless mode, so essentially a 'one off' run of the test that connects to the filing-api container that is started with docker compose (see https://github.com/cfpb/sbl-project/blob/main/LOCAL_DEV_COMPOSE.md).  A report.html is written to the locust-load-test/reports directory

- Running in docker compose from the https://github.com/cfpb/sbl-project/tree/main repo.  This starts up a Web UI version of locust that can be reached via http://localhost:8089/.  Tests can then be ran repeatedly via the Web UI.

## Kubernetes
Helm chart overrides can be found in the internal EKS repo.

## Env Vars
The following env vars can be changed to modify how your test runs:
- USER_INDEX - Used to offset user IDs created in Keycloak, so that two running tests don't step on each other.  Defaults to `0`, should be incremented by 10, 100, etc to ensure created Keycloak users don't step on each other.
- SBLAR_LOCATION - Where locally the SBLARs are pulled to and 'uploaded' from.  This shouldn't need to be changed. Defaults to `./locust-load-test/sblars`
- SBLAR_REPO - Github repo where to pull test SBLARs from.  Defaults to `https://api.github.com/repos/cfpb/sbl-test-data/contents/locust-sblars`
- LEI_REPO - Github repo where to pull a list of LEIs from.  Defaults to `https://raw.githubusercontent.com/cfpb/sbl-test-data/test_leis/`
- LEI_FILE - File to read the LEIs list from.  Defaults to `test_leis.json`
- POST_SUB_WEIGHT - Used when running just_submissions.py script, to weight the POST submission endpoint.  Defaults to `5`.
- GET_SUB_WEIGHT - Used when running just_submissions.py script, to weight the GET latest submission endpoint.  Defaults to `10`.
- GET_REPORT_WEIGHT - Used when running just_submissions.py script, to weight the GET latest submission report endpoint.  Defaults to `2`.
- KC_URL - Keycloak URL to instantiate new users.  Defaults to `http://localhost:8880`
- KC_ADMIN_CLIENT_ID - Keycloak admin client id.  Defaults to `admin-cli`
- KC_ADMIN_CLIENT_SECRET - Keycloak admin secret to log into the client.  Defaults to `local_test_only`
- KC_REALM - Keycloak realm for filing-api users.  Defaults to `regtech`
- AUTH_CLIENT - Keycloak client for the filing-api service.  Defaults to `regtech-client`