import os
import mssql_python

SERVER = "hero-api.database.windows.net"
DATABASE = "heroes-api-db-3482538"

def get_connection():

    connection_string = (
        f"Server={SERVER};"
        f"Database={DATABASE};"
        "Authentication=ActiveDirectoryDefault;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )

    return mssql_python.connect(
        connection_string,
        timeout=30
    )