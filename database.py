import pyodbc
import struct
from azure.identity import DefaultAzureCredential

# ------------------------------------------------------------
# Azure SQL configuration
# ------------------------------------------------------------

SERVER = "hero-api.database.windows.net"
DATABASE = "heroes-api-db-3482538"

# ODBC Driver 18 for SQL Server
DRIVER = "{ODBC Driver 18 for SQL Server}"

# Azure SQL authentication scope
SQL_SCOPE = "https://database.windows.net/.default"


# ------------------------------------------------------------
# Database connection
# ------------------------------------------------------------

def get_connection():

    # Obtain an Azure authentication token.
    credential = DefaultAzureCredential()
    token = credential.get_token(SQL_SCOPE).token

    # Convert the token into the format expected by ODBC.
    token_bytes = token.encode("utf-16-le")
    token_struct = struct.pack(
        f"<I{len(token_bytes)}s",
        len(token_bytes),
        token_bytes
    )

    # Build the SQL Server connection string.
    connection_string = (
        f"DRIVER={DRIVER};"
        f"SERVER=tcp:{SERVER},1433;"
        f"DATABASE={DATABASE};"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    # Open and return the database connection.
    connection = pyodbc.connect(
        connection_string,
        attrs_before={1256: token_struct}
    )

    return connection
