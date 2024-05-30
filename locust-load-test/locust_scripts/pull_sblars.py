import httpx
import os


def delete_files():
    sblar_dir = os.getenv("SBLAR_LOCATION", "./locust-load-test/sblars")
    for file in os.listdir(sblar_dir):
        file_path = os.path.join(sblar_dir, file)
        os.remove(file_path)


def download_file(client, file_url, local_path):
    response = client.get(file_url)
    response.raise_for_status()
    if not os.path.exists(local_path):
        with open(local_path, "wb") as file:
            file.write(response.content)


def pull_files(client, contents, url):
    sblar_dir = os.getenv("SBLAR_LOCATION", "./locust-load-test/sblars")
    for file in contents:
        if file["type"] == "file":
            local_path = os.path.join(sblar_dir, file["name"])
            if not os.path.exists(sblar_dir):
                os.makedirs(sblar_dir)
            download_file(client, file["download_url"], local_path)
        elif file["type"] == "dir":
            response = client.get(url)
            response.raise_for_status()
            contents = response.json()
            folder_url = url + f"{file['name']}/"
            pull_files(client, contents, folder_url)


def download_files():
    with httpx.Client() as client:
        url = os.getenv("SBLAR_REPO", "https://api.github.com/repos/cfpb/sbl-test-data/contents/locust-sblars")
        response = client.get(url)
        response.raise_for_status()
        contents = response.json()
        pull_files(client, contents, url)
