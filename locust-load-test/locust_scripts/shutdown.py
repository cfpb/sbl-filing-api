import os

from keycloak import KeycloakOpenIDConnection, KeycloakAdmin
from pull_sblars import delete_files


def shutdown(user_id):
    keycloak_connection = KeycloakOpenIDConnection(
        server_url=os.getenv("KC_URL", "http://localhost:8880"),
        client_id=os.getenv("KC_ADMIN_CLIENT_ID", "admin-cli"),
        client_secret_key=os.getenv("KC_ADMIN_CLIENT_SECRET", "local_test_only"),
        realm_name=os.getenv("KC_REALM", "regtech"),
        verify=False,
    )
    keycloak_admin = KeycloakAdmin(connection=keycloak_connection)
    keycloak_admin.delete_user(user_id)
    delete_files()
