import os
import random
import logging

from keycloak import KeycloakOpenID, KeycloakOpenIDConnection, KeycloakAdmin
from pull_sblars import download_files
from leis import get_leis

logger = logging.getLogger(__name__)

COUNT = 0


def startup():
    # Used to generate different users in keycloak based on the number of Users started
    global COUNT
    COUNT += 1
    user_number = int(os.getenv("USER_INDEX", 0)) + COUNT
    leis = get_leis()
    lei = leis[random.randint(0, len(leis) - 1)]
    keycloak_connection = KeycloakOpenIDConnection(
        server_url=os.getenv("KC_URL", "http://localhost:8880"),
        client_id=os.getenv("KC_ADMIN_CLIENT_ID", "admin-cli"),
        client_secret_key=os.getenv("KC_ADMIN_CLIENT_SECRET", "local_test_only"),
        realm_name=os.getenv("KC_REALM", "regtech"),
        verify=False,
    )
    keycloak_admin = KeycloakAdmin(connection=keycloak_connection)
    user_id = ""
    try:
        for group in leis:
            keycloak_admin.create_group({"name": group}, skip_exists=True)
        user_id = keycloak_admin.create_user(
            {
                "email": f"locust_test{user_number}@cfpb.gov",
                "username": f"locust_test{user_number}",
                "enabled": True,
                "firstName": f"locust_test{user_number}",
                "lastName": f"locust_test{user_number}",
                "credentials": [
                    {
                        "value": f"locust_test{user_number}",
                        "type": "password",
                    }
                ],
                "groups": [lei],
            }
        )
    except Exception:
        logger.exception("Error creating user in keycloak.")

    keycloak_openid = KeycloakOpenID(
        server_url=os.getenv("KC_URL", "http://localhost:8880") + "/auth",
        client_id=os.getenv("AUTH_CLIENT", "regtech-client"),
        realm_name=os.getenv("KC_REALM", "regtech"),
        verify=False,
    )

    token = keycloak_openid.token(f"locust_test{user_number}", f"locust_test{user_number}")["access_token"]

    download_files()

    return user_id, token, lei
