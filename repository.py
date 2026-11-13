import pyodbc
from database import get_connection

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------

def _get_or_create_source(cursor, title):
    """
    Find an existing source or create a new one.
    Returns the source ID.
    """

    # Lock the matching key range to avoid duplicate inserts
    # when multiple requests attempt to create the same source.
    cursor.execute(
        """
        SELECT source_id
        FROM dbo.Sources WITH (UPDLOCK, HOLDLOCK)
        WHERE title = ?
        """,
        title
    )

    row = cursor.fetchone()

    if row:
        return row[0]

    cursor.execute(
        """
        INSERT INTO dbo.Sources (title)
        OUTPUT INSERTED.source_id
        VALUES (?)
        """,
        title
    )

    return cursor.fetchone()[0]


def _add_aliases(cursor, hero_id, aliases):
    """Insert aliases associated with a hero."""

    for alias in aliases:
        cursor.execute(
            """
            INSERT INTO dbo.HeroAliases (hero_id, alias)
            VALUES (?, ?)
            """,
            hero_id,
            alias
        )


def _add_sources(cursor, hero_id, sources):
    """Associate a hero with existing or newly created sources."""

    for source in sources:
        source_id = _get_or_create_source(cursor, source)

        cursor.execute(
            """
            INSERT INTO dbo.HeroSources (hero_id, source_id)
            VALUES (?, ?)
            """,
            hero_id,
            source_id
        )


def _get_hero(cursor, hero_id):
    """Retrieve a hero and its associated aliases and sources."""

    cursor.execute(
        """
        SELECT id, name, status, culture,
               historical_period, description
        FROM dbo.Heroes
        WHERE id = ?
        """,
        hero_id
    )

    row = cursor.fetchone()

    if not row:
        return None

    hero = {
        "id": row[0],
        "name": row[1],
        "status": row[2],
        "culture": row[3],
        "historical_period": row[4],
        "description": row[5],
        "aliases": [],
        "sources": []
    }

    # Retrieve the hero's aliases.
    cursor.execute(
        """
        SELECT alias
        FROM dbo.HeroAliases
        WHERE hero_id = ?
        """,
        hero_id
    )

    hero["aliases"] = [row[0] for row in cursor.fetchall()]

    # Retrieve the hero's associated sources.
    cursor.execute(
        """
        SELECT s.title
        FROM dbo.HeroSources hs
        JOIN dbo.Sources s
            ON hs.source_id = s.source_id
        WHERE hs.hero_id = ?
        """,
        hero_id
    )

    hero["sources"] = [row[0] for row in cursor.fetchall()]

    return hero


# ------------------------------------------------------------
# CREATE - Add a new hero
# ------------------------------------------------------------

def create_hero(data):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Insert the main hero record.
        cursor.execute(
            """
            INSERT INTO dbo.Heroes (
                name, status, culture,
                historical_period, description
            )
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?)
            """,
            data["name"],
            data["status"],
            data["culture"],
            data["historical_period"],
            data["description"]
        )

        hero_id = cursor.fetchone()[0]

        # Insert the hero's aliases and source relationships.
        _add_aliases(cursor, hero_id, data["aliases"])
        _add_sources(cursor, hero_id, data["sources"])

        # Commit all changes together.
        connection.commit()

        return _get_hero(cursor, hero_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ------------------------------------------------------------
# READ - Retrieve all heroes
# ------------------------------------------------------------

def get_all_heroes():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, name, status, culture,
                   historical_period, description
            FROM dbo.Heroes
            ORDER BY id
            """
        )

        heroes = {}

        for row in cursor.fetchall():
            heroes[row[0]] = {
                "id": row[0],
                "name": row[1],
                "status": row[2],
                "culture": row[3],
                "historical_period": row[4],
                "description": row[5],
                "aliases": [],
                "sources": []
            }

        # Retrieve all aliases in one query.
        cursor.execute(
            """
            SELECT hero_id, alias
            FROM dbo.HeroAliases
            ORDER BY alias_id
            """
        )

        for hero_id, alias in cursor.fetchall():
            if hero_id in heroes:
                heroes[hero_id]["aliases"].append(alias)

        # Retrieve all source relationships in one query.
        cursor.execute(
            """
            SELECT hs.hero_id, s.title
            FROM dbo.HeroSources hs
            JOIN dbo.Sources s
                ON hs.source_id = s.source_id
            ORDER BY hs.hero_id, s.source_id
            """
        )

        for hero_id, source in cursor.fetchall():
            if hero_id in heroes:
                heroes[hero_id]["sources"].append(source)

        return list(heroes.values())

    finally:
        connection.close()


# ------------------------------------------------------------
# READ - Retrieve one hero
# ------------------------------------------------------------

def get_hero(hero_id):
    connection = get_connection()

    try:
        cursor = connection.cursor()
        return _get_hero(cursor, hero_id)

    finally:
        connection.close()


# ------------------------------------------------------------
# UPDATE - Update an existing hero
# ------------------------------------------------------------

def update_hero(hero_id, data):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        # Update the main hero information.
        cursor.execute(
            """
            UPDATE dbo.Heroes
            SET name = ?,
                status = ?,
                culture = ?,
                historical_period = ?,
                description = ?
            WHERE id = ?
            """,
            data["name"],
            data["status"],
            data["culture"],
            data["historical_period"],
            data["description"],
            hero_id
        )

        if cursor.rowcount == 0:
            connection.rollback()
            return None

        # Replace the existing aliases.
        cursor.execute(
            "DELETE FROM dbo.HeroAliases WHERE hero_id = ?",
            hero_id
        )

        _add_aliases(cursor, hero_id, data["aliases"])

        # Replace the existing source relationships.
        cursor.execute(
            "DELETE FROM dbo.HeroSources WHERE hero_id = ?",
            hero_id
        )

        _add_sources(cursor, hero_id, data["sources"])

        connection.commit()

        return _get_hero(cursor, hero_id)

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ------------------------------------------------------------
# DELETE - Delete one hero
# ------------------------------------------------------------

def delete_hero(hero_id):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT name FROM dbo.Heroes WHERE id = ?",
            hero_id
        )

        row = cursor.fetchone()

        if not row:
            return None

        hero_name = row[0]

        # Associated aliases and relationships are deleted
        # automatically through ON DELETE CASCADE.
        cursor.execute(
            "DELETE FROM dbo.Heroes WHERE id = ?",
            hero_id
        )

        connection.commit()

        return hero_name

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ------------------------------------------------------------
# PURGE - Delete all heroes
# ------------------------------------------------------------

def purge_heroes():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM dbo.Heroes")
        total = cursor.fetchone()[0]

        if total == 0:
            return 0

        # Cascading deletes remove aliases and relationships.
        cursor.execute("DELETE FROM dbo.Heroes")

        connection.commit()

        # Identity values are intentionally not reset.
        return total

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


# ------------------------------------------------------------
# COUNT - Count all heroes
# ------------------------------------------------------------

def count_heroes():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("SELECT COUNT(*) FROM dbo.Heroes")

        return cursor.fetchone()[0]

    finally:
        connection.close()
