
import os
import mssql_python

SERVER = "hero-api.database.windows.net"
DATABASE = "heroes-api-db-3482538"

def get_connection():

    # Use Managed Identity in Azure.
    # Use your personal Azure login locally.
    authentication = os.getenv(
        "DB_AUTHENTICATION",
        "ActiveDirectoryDefault"
    )

    connection_string = (
        f"Server={SERVER};"
        f"Database={DATABASE};"
        f"Authentication={authentication};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
    )

    return mssql_python.connect(
        connection_string,
        timeout=30
    )
