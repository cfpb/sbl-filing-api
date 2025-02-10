# SBL Filing API
This app manages the SBL data submission, processing, and validation.

---
## Contact Us
If you have an inquiry or suggestion for the user and financial institutions management API or any SBL related code, please reach out to us at <sblhelp@cfpb.gov>

---
### Dependencies
- [Poetry](https://python-poetry.org/) is used as the package management tool. Once installed, just running `poetry install` in the root of the project should install all the dependencies needed by the app.
- [Docker](https://www.docker.com/) is used for local development where ancillary services will run.

---
### Pre-requisites
[SBL Project Repo](https://github.com/cfpb/sbl-project) contains the `docker-compose.yml` to run the ancillary services.  See [LOCAL_DEV_COMPOSE.md](https://github.com/cfpb/sbl-project/blob/main/LOCAL_DEV_COMPOSE.md) for more information.
- Not all services need to run, this module `sbl-filing-api` is part of the docker compose file, which doesn't need to be ran in docker for local development.
- Issuing `docker compose up -d pg keycloak user-fi` would start the necessary services (regtech-user-fi-management, postgres, and keycloak)
```bash
$ cd ~/Projects/sbl-project
$ docker compose up -d pg keycloak user-fi
[+] Running 3/3
 ⠿ Network sbl-project_default       Created     0.2s
 ⠿ Container sbl-project-pg-1        Started     2.6s
 ⠿ Container sbl-project-keycloak-1  Started     13.4s
 ⠿ Container sbl-project-user-fi-1   Started     17.3s
```

----
## File Upload

This application allows users to upload small business loan register files.  It can be configured to store them in
either a local filesystem, or an AWS S3 bucket.

### Local Configuration

#### File System
By default, this application is configured to upload files into a directory named `upload` in the project root when
running locally within the [.env.local](src/.env.local) file.  The properties involved are:
```properties
FS_UPLOAD_CONFIG__PROTOCOL="file"
FS_UPLOAD_CONFIG__ROOT="../upload"
```

#### S3
If you wish to use an Amazon S3 bucket for testing locally:

1. Create an S3 bucket in AWS.  For the purposes of this README, assume it is named `sbl-filing-api`.
2. Ensure you have access to an AWS user with IAM permissions to read and write to the bucket.
3. Ensure you have the [AWS CLI](https://aws.amazon.com/cli/) installed.
4. Ensure you have ran `aws configure` to configure the AWS CLI with credentials necessary to access the given bucket.
5. Update your environment with the following environment variables (use the bucket name created above in 
`FS_UPLOAD_CONFIG__ROOT` if it is different):
    ```bash
    export FS_UPLOAD_CONFIG__PROTOCOL="s3"
    export FS_UPLOAD_CONFIG__ROOT="sbl-filing-api"
    ```
   This can be made permanent by updating e.g. your `$HOME/.zshrc` file.
6. Optionally you may update [.env.local](src/.env.local) instead if you prefer.
7. Restart the application if it is already running.

**Important:** This will make API calls and store files in S3, which may result in charges depending on usage.

If you choose to update `.env.local`, please do not commit that change.

----
## Open source licensing info
1. [TERMS](TERMS.md)
2. [LICENSE](LICENSE)
3. [CFPB Source Code Policy](https://github.com/cfpb/source-code-policy/)