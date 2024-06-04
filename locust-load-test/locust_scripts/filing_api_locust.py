import os
import random
import logging

from pydantic.types import SecretStr
from locust import HttpUser, task, between
from keycloak import KeycloakOpenID, KeycloakOpenIDConnection, KeycloakAdmin
from pull_sblars import download_files, delete_files

COUNT = 0
LEIS = ["123456789TESTBANK123", "123456789TESTBANK456", "123456789TESTBANKSUB456"]
logger = logging.getLogger(__name__)

class FilingApiUser(HttpUser):
    wait_time = between(1, 5)
    token: str
    user_number: int
    user_id: str
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client.verify = False

    @task
    def put_snapshot_id(self):
        self.client.put(
            f"/v1/filing/institutions/{self.lei}/filings/2024/institution-snapshot-id",
            headers={"Authorization": "Bearer " + self.token},
            json={"institution_snapshot_id": "test"}
        )

    @task
    def get_contact_info(self):
        self.client.get(
            f"/v1/filing/institutions/{self.lei}/filings/2024/contact-info",
            headers={"Authorization": "Bearer " + self.token}
        )

    @task
    def put_contact_info(self):
        response = self.client.get(
            f"/v1/filing/institutions/{self.lei}/filings/2024/contact-info",
            headers={"Authorization": "Bearer " + self.token}
        )
        filing = response.json()
        contact_info = {
            "filing": filing["id"],
            "first_name": "test_first_name_1",
            "last_name": "test_last_name_1",
            "hq_address_street_1": "address street 1",
            "hq_address_street_2": "",
            "hq_address_city": "Test City 1",
            "hq_address_state": "TS",
            "hq_address_zip": "12345",
            "phone_number": "112-345-6789",
            "email": "name_1@email.test",
        }
        if "contact_info" in filing:
            contact_info["id"] = filing["contact_info"]["id"]
        self.client.put(
            f"/v1/filing/institutions/{self.lei}/filings/2024/contact-info",
            json=contact_info,
            headers={"Authorization": "Bearer " + self.token}
        )

    @task
    def submit_sblar(self):
        sblar_dir = os.getenv("SBLAR_LOCATION", "./locust-load-test/sblars")
        sblar = random.choice(os.listdir(sblar_dir))
        self.client.post(
            f"/v1/filing/institutions/{self.lei}/filings/2024/submissions",
            headers={"Authorization": "Bearer " + self.token},
            files=[("file", (sblar, open(os.path.join(sblar_dir, sblar), "rb"), "text/csv"))]
        )

    @task
    def get_latest_submission(self):
        self.client.get(
            f"/v1/filing/institutions/{self.lei}/filings/2024/submissions/latest",
            headers={"Authorization": "Bearer " + self.token}
        )

    @task
    def get_latest_submission_report(self):
        self.client.get(
            f"/v1/filing/institutions/{self.lei}/filings/2024/submissions/latest/report",
            headers={"Authorization": "Bearer " + self.token}
        )

    @task
    def get_filing_periods(self):
        self.client.get("/v1/filing/periods", headers={"Authorization": "Bearer " + self.token})

    @task
    def get_filing(self):
        self.client.get(
            f"/v1/filing/institutions/{self.lei}/filings/2024",
            headers={"Authorization": "Bearer " + self.token}
        )

    def on_stop(self):
        keycloak_connection = KeycloakOpenIDConnection(
            server_url=os.getenv("KC_URL", "http://localhost:8880"),
            client_id=os.getenv("KC_ADMIN_CLIENT_ID", "admin-cli"),
            client_secret_key=os.getenv("KC_ADMIN_CLIENT_SECRET", "local_test_only"),
            realm_name=os.getenv("KC_REALM", "regtech"),
            verify=False
        )
        keycloak_admin = KeycloakAdmin(connection=keycloak_connection)
        keycloak_admin.delete_user(self.user_id)
        delete_files()

    def on_start(self):
        # Used to generate different users in keycloak based on the number of Users started
        global COUNT, LEIS
        COUNT += 1
        self.user_number = COUNT
        self.lei = LEIS[random.randint(0, 2)]
        keycloak_connection = KeycloakOpenIDConnection(
            server_url=os.getenv("KC_URL", "http://localhost:8880"),
            client_id=os.getenv("KC_ADMIN_CLIENT_ID", "admin-cli"),
            client_secret_key=os.getenv("KC_ADMIN_CLIENT_SECRET", "local_test_only"),
            realm_name=os.getenv("KC_REALM", "regtech"),
            verify=False
        )
        keycloak_admin = KeycloakAdmin(connection=keycloak_connection)
        try:
            self.user_id = keycloak_admin.create_user(
                {
                    "email": f"locust_test{self.user_number}@cfpb.gov",
                    "username": f"locust_test{self.user_number}",
                    "enabled": True,
                    "firstName": f"locust_test{self.user_number}",
                    "lastName": f"locust_test{self.user_number}",
                    "credentials": [
                        {
                            "value": f"locust_test{self.user_number}",
                            "type": "password",
                        }
                    ],
                    "groups": [self.lei],
                }
            )
        except Exception:
            logger.exception("Error creating user in keycloak.")
            

        keycloak_openid = KeycloakOpenID(
            server_url=os.getenv("KC_URL", "http://localhost:8880") + "/auth",
            client_id=os.getenv("AUTH_CLIENT", "regtech-client"),
            realm_name=os.getenv("KC_REALM", "regtech"),
            verify=False
        )

        self.token = keycloak_openid.token(f"locust_test{self.user_number}", f"locust_test{self.user_number}")[
            "access_token"
        ]

        download_files()
