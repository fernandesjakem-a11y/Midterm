
import repository

# Test data for a new hero.
hero_data = {
    "name": "Achilles",
    "aliases": [
        "The Swift-Footed",
        "Hero of the Trojan War"
    ],
    "status": "Mythical",
    "culture": "Ancient Greek",
    "sources": [
        "The Iliad by Homer"
    ],
    "historical_period": "Greek Mythological Heroic Age",
    "description": "Achilles was a legendary Greek warrior and one of the central heroes of the Trojan War."
}

# CREATE
print("\n--- CREATE HERO ---")
created = repository.create_hero(hero_data)
print(created)

hero_id = created["id"]

# READ ALL
print("\n--- GET ALL HEROES ---")
print(repository.get_all_heroes())

# READ ONE
print("\n--- GET SPECIFIC HERO ---")
print(repository.get_hero(hero_id))

# COUNT
print("\n--- COUNT HEROES ---")
print(repository.count_heroes())

# UPDATE
print("\n--- UPDATE HERO ---")

hero_data["description"] = "Updated description for Achilles."

updated = repository.update_hero(hero_id, hero_data)
print(updated)

# DELETE
print("\n--- DELETE HERO ---")
deleted = repository.delete_hero(hero_id)
print(deleted)

# VERIFY DELETION
print("\n--- VERIFY DELETION ---")
print(repository.get_hero(hero_id))
