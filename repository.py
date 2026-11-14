from datetime import datetime, timezone
from database import get_connection

# ------------------------------------------------------------
# HELPER - Find or create a source
# ------------------------------------------------------------

def _get_or_create_source(cursor, title):
    """
    Reuse an existing source or insert a new one.
    Returns the source ID.
    """

    cursor.execute(
        """
        SELECT source_id
        FROM dbo.Sources WITH (UPDLOCK, HOLDLOCK)
        WHERE title = %(title)s
        """,
        {"title": title}
    )

    row = cursor.fetchone()

    if row:
        return row[0]

    cursor.execute(
        """
        INSERT INTO dbo.Sources (title)
        OUTPUT INSERTED.source_id
        VALUES (%(title)s)
        """,
        {"title": title}
    )

    return cursor.fetchone()[0]

# ------------------------------------------------------------
# HELPER - Insert aliases
# ------------------------------------------------------------

def _add_aliases(cursor, hero_id, aliases):
    """Insert aliases belonging to a hero."""

    for alias in aliases:
        cursor.execute(
            """
            INSERT INTO dbo.HeroAliases (hero_id, alias)
            VALUES (%(hero_id)s, %(alias)s)
            """,
            {
                "hero_id": hero_id,
                "alias": alias
            }
        )

# ------------------------------------------------------------
# HELPER - Insert source relationships
# ------------------------------------------------------------

def _add_sources(cursor, hero_id, sources):
    """Associate a hero with its literary sources."""

    for source in sources:
        source_id = _get_or_create_source(cursor, source)

        cursor.execute(
            """
            INSERT INTO dbo.HeroSources (hero_id, source_id)
            VALUES (%(hero_id)s, %(source_id)s)
            """,
            {
                "hero_id": hero_id,
                "source_id": source_id
            }
        )

# ------------------------------------------------------------
# HELPER - Retrieve one complete hero
# ------------------------------------------------------------

def _get_hero(cursor, hero_id):
    """Retrieve a hero, including aliases and sources."""

    cursor.execute(
        """
        SELECT
            id,
            name,
            status,
            culture,
            historical_period,
            description,
            needs_review
        FROM dbo.Heroes
        WHERE id = %(id)s
        """,
        {"id": hero_id}
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
        "needs_review": bool(row[6]),
        "aliases": [],
        "sources": []
    }

    # Retrieve aliases.
    cursor.execute(
        """
        SELECT alias
        FROM dbo.HeroAliases
        WHERE hero_id = %(id)s
        ORDER BY alias_id
        """,
        {"id": hero_id}
    )

    hero["aliases"] = [r[0] for r in cursor.fetchall()]

    # Retrieve sources.
    cursor.execute(
        """
        SELECT s.title
        FROM dbo.HeroSources hs
        INNER JOIN dbo.Sources s
            ON hs.source_id = s.source_id
        WHERE hs.hero_id = %(id)s
        ORDER BY s.source_id
        """,
        {"id": hero_id}
    )

    hero["sources"] = [r[0] for r in cursor.fetchall()]

    return hero

# ------------------------------------------------------------
# CREATE - Add a new hero
# ------------------------------------------------------------

def create_hero(data):
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.Heroes (
                name,
                status,
                culture,
                historical_period,
                description
            )
            OUTPUT INSERTED.id
            VALUES (
                %(name)s,
                %(status)s,
                %(culture)s,
                %(historical_period)s,
                %(description)s
            )
            """,
            {
                "name": data["name"],
                "status": data["status"],
                "culture": data["culture"],
                "historical_period": data["historical_period"],
                "description": data["description"]
            }
        )

        hero_id = cursor.fetchone()[0]

        # Insert aliases and sources.
        _add_aliases(cursor, hero_id, data["aliases"])
        _add_sources(cursor, hero_id, data["sources"])

        # Save all changes together.
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
            SELECT
                id,
                name,
                status,
                culture,
                historical_period,
                description,
                needs_review
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
                "needs_review": bool(row[6]),
                "aliases": [],
                "sources": []
            }

        # Retrieve all aliases.
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

        # Retrieve all source relationships.
        cursor.execute(
            """
            SELECT hs.hero_id, s.title
            FROM dbo.HeroSources hs
            INNER JOIN dbo.Sources s
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

        cursor.execute(
            """
            UPDATE dbo.Heroes
            SET
                name = %(name)s,
                status = %(status)s,
                culture = %(culture)s,
                historical_period = %(historical_period)s,
                description = %(description)s
            WHERE id = %(id)s
            """,
            {
                "name": data["name"],
                "status": data["status"],
                "culture": data["culture"],
                "historical_period": data["historical_period"],
                "description": data["description"],
                "id": hero_id
            }
        )

        if cursor.rowcount == 0:
            connection.rollback()
            return None

        # Replace existing aliases.
        cursor.execute(
            """
            DELETE FROM dbo.HeroAliases
            WHERE hero_id = %(id)s
            """,
            {"id": hero_id}
        )

        _add_aliases(cursor, hero_id, data["aliases"])

        # Replace existing source relationships.
        cursor.execute(
            """
            DELETE FROM dbo.HeroSources
            WHERE hero_id = %(id)s
            """,
            {"id": hero_id}
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
            """
            DELETE FROM dbo.Heroes
            OUTPUT DELETED.name
            WHERE id = %(id)s
            """,
            {"id": hero_id}
        )

        row = cursor.fetchone()

        if not row:
            connection.rollback()
            return None

        hero_name = row[0]

        # Foreign key cascades remove associated aliases
        # and hero-source relationships.
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

        cursor.execute(
            "SELECT COUNT(*) FROM dbo.Heroes"
        )

        total = cursor.fetchone()[0]

        # Delete the entire hero collection.
        # Cascading deletes remove associated records.
        cursor.execute("DELETE FROM dbo.Heroes")

        connection.commit()

        # Identity values are not reset.
        return total

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()

# ------------------------------------------------------------
# COUNTS - Count all heroes
# ------------------------------------------------------------

def count_heroes():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM dbo.Heroes"
        )

        return cursor.fetchone()[0]

    finally:
        connection.close()

# ------------------------------------------------------------
# VALIDATE - Check all heroes for missing sources
# ------------------------------------------------------------

def validate_heroes():
    """
    Check every hero's source relationships.

    Heroes without sources: needs_review = 1
    Heroes with sources: needs_review = 0

    Only records requiring a change are updated.
    """

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE h
            SET needs_review = CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM dbo.HeroSources hs
                    WHERE hs.hero_id = h.id
                ) THEN 0
                ELSE 1
            END
            OUTPUT INSERTED.id
            FROM dbo.Heroes h
            WHERE
                (
                    h.needs_review = 0
                    AND NOT EXISTS (
                        SELECT 1
                        FROM dbo.HeroSources hs
                        WHERE hs.hero_id = h.id
                    )
                )
                OR
                (
                    h.needs_review = 1
                    AND EXISTS (
                        SELECT 1
                        FROM dbo.HeroSources hs
                        WHERE hs.hero_id = h.id
                    )
                )
        """)

        # Count the IDs returned by the UPDATE.
        updated_count = len(cursor.fetchall())

        # Persist the changes.
        connection.commit()

        timestamp = datetime.now(
            timezone.utc
        ).isoformat(timespec="seconds").replace("+00:00", "Z")

        return {
            "updatedCount": updated_count,
            "timestamp": timestamp
        }

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()
