import os
import random
import logging

from locust import HttpUser, task, between
from startup import startup
from shutdown import shutdown

logger = logging.getLogger(__name__)


class FilingApiUser(HttpUser):
    wait_time = between(1, 5)
    token: str
    user_id: str
    lei: str

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client.verify = False

    @task(int(os.getenv("POST_SUB_WEIGHT", "5")))
    def submit_sblar(self):
        sblar_dir = os.getenv("SBLAR_LOCATION", "./locust-load-test/sblars")
        sblar = random.choice(os.listdir(sblar_dir))
        self.client.post(
            f"/v1/filing/institutions/{self.lei}/filings/2024/submissions",
            headers={"Authorization": "Bearer " + self.token},
            files=[("file", (sblar, open(os.path.join(sblar_dir, sblar), "rb"), "text/csv"))],
        )

    @task(int(os.getenv("GET_SUB_WEIGHT", "10")))
    def get_latest_submission(self):
        self.client.get(
            f"/v1/filing/institutions/{self.lei}/filings/2024/submissions/latest",
            headers={"Authorization": "Bearer " + self.token},
        )

    @task(int(os.getenv("GET_REPORT_WEIGHT", "2")))
    def get_latest_submission_report(self):
        self.client.get(
            f"/v1/filing/institutions/{self.lei}/filings/2024/submissions/latest/report",
            headers={"Authorization": "Bearer " + self.token},
        )

    def on_stop(self):
        shutdown(self.user_id)

    def on_start(self):
        user_id, token, lei = startup()
        self.user_id = user_id
        self.token = token
        self.lei = lei
