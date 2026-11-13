
from database import get_connection

try:
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT DB_NAME(), USER_NAME()")

    result = cursor.fetchone()

    print("Database connection successful!")
    print("Database:", result[0])
    print("Authenticated user:", result[1])

    connection.close()

except Exception as e:
    print("Database connection failed:")
    print(e)
