import httpx
import os
import ujson


def get_leis():
    local_path = os.path.join("../sbl-test-data/test_leis/", os.getenv("LEI_FILE", "test_leis.json"))
    if os.path.exists(local_path):
        with open(local_path, "r") as file:
            return ujson.load(file)
    else:
        with httpx.Client() as client:
            url = os.getenv(
                "LEI_REPO",
                "https://raw.githubusercontent.com/cfpb/sbl-test-data/refs/heads/main/test_leis/",
            )
            full_path = url + os.getenv("LEI_FILE", "test_leis.json")
            response = client.get(full_path)
            response.raise_for_status()
            contents = response.json()
            return contents
