import os
import random

from locust import HttpUser, task, between
from startup import startup
from shutdown import shutdown

COUNT = 0
LEIS = ["123456789TESTBANK123", "123456789TESTBANK456", "123456789TESTBANKSUB456"]


class FilingApiUser(HttpUser):
    wait_time = between(1, 5)
    token: str
    user_number: int
    user_id: str

    @task
    def put_snapshot_id(self):
        self.client.put(
            f"/v1/filing/institutions/{self.lei}/filings/2024/institution-snapshot-id",
            headers={"Authorization": "Bearer " + self.token},
            json={"institution_snapshot_id": "test"},
        )

    @task
    def get_contact_info(self):
        self.client.get(
            f"/v1/filing/institutions/{self.lei}/filings/2024/contact-info",
            headers={"Authorization": "Bearer " + self.token},
        )

    @task
    def put_contact_info(self):
        response = self.client.get(
            f"/v1/filing/institutions/{self.lei}/filings/2024/contact-info",
            headers={"Authorization": "Bearer " + self.token},
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
            headers={"Authorization": "Bearer " + self.token},
        )

    @task(5)
    def submit_sblar(self):
        sblar_dir = os.getenv("SBLAR_LOCATION", "./locust-load-test/sblars")
        sblar = random.choice(os.listdir(sblar_dir))
        self.client.post(
            f"/v1/filing/institutions/{self.lei}/filings/2024/submissions",
            headers={"Authorization": "Bearer " + self.token},
            files=[("file", (sblar, open(os.path.join(sblar_dir, sblar), "rb"), "text/csv"))],
        )

    @task(10)
    def get_latest_submission(self):
        self.client.get(
            f"/v1/filing/institutions/{self.lei}/filings/2024/submissions/latest",
            headers={"Authorization": "Bearer " + self.token},
        )

    @task(2)
    def get_latest_submission_report(self):
        self.client.get(
            f"/v1/filing/institutions/{self.lei}/filings/2024/submissions/latest/report",
            headers={"Authorization": "Bearer " + self.token},
        )

    @task
    def get_filing_periods(self):
        self.client.get("/v1/filing/periods", headers={"Authorization": "Bearer " + self.token})

    @task
    def get_filing(self):
        self.client.get(
            f"/v1/filing/institutions/{self.lei}/filings/2024",
            headers={"Authorization": "Bearer " + self.token},
        )

    def on_stop(self):
        shutdown(self.user_id)

    def on_start(self):
        user_id, token, lei = startup()
        self.user_id = user_id
        self.token = token
        self.lei = lei
