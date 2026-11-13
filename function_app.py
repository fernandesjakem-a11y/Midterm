import azure.functions as func
import logging
import json
import os
import hmac
from functools import wraps
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Create one Key Vault client for the application.
credential = DefaultAzureCredential()

secret_client = SecretClient(
    vault_url="https://kv-midterm-ferna.vault.azure.net/",
    credential=credential
)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

import repository

FIELDS = [
    "name", "aliases", "status", "culture",
    "sources", "historical_period", "description"
]

# ------------------------------------------------------------
# Helpers and handler
# ------------------------------------------------------------

def response(data, status=200):
    """Return a JSON response."""
    return func.HttpResponse(
        json.dumps(data),
        status_code=status,
        mimetype="application/json"
    )

class APIError(Exception):
    def __init__(self, message, status):
        self.message = message
        self.status = status

def get_api_key():
    secret = secret_client.get_secret("HEROES-API-KEY")
    return secret.value

def handle_function(
    needs_json=False,
    needs_id=False,
    needs_existing_hero=False
):
    def decorator(handler):
        @wraps(handler)
        def wrapper(req: func.HttpRequest, *args, **kwargs):
            try:
                # --------------------------------------------
                # API key authentication
                # --------------------------------------------

                key = get_api_key()
                provided_key = req.headers.get("X-API-Key") or ""

                if not key:
                    logging.error("HEROES_API_KEY is not configured.")
                    raise APIError(
                        "Server authentication is not configured.", 500
                    )

                if not hmac.compare_digest(provided_key, key):
                    raise APIError("Unauthorized.", 401)

                # --------------------------------------------
                # JSON body validation
                # --------------------------------------------

                if needs_json:
                    try:
                        body = req.get_json()
                    except (ValueError, TypeError):
                        raise APIError("Invalid JSON request body.", 400)

                    if not isinstance(body, dict):
                        raise APIError(
                            "Request body must be a JSON object.", 400
                        )

                    missing = [
                        field for field in FIELDS
                        if field not in body
                        or body[field] is None
                        or body[field] == ""
                    ]

                    if missing:
                        raise APIError(
                            "Missing required fields: " + ", ".join(missing),
                            400
                        )

                    req.validated_body = body

                # --------------------------------------------
                # Hero ID validation
                # --------------------------------------------

                raw_id = req.params.get("id")

                if needs_id and not raw_id:
                    raise APIError("Missing hero ID.", 400)

                if raw_id is not None:
                    if not raw_id.strip():
                        raise APIError("Invalid hero ID.", 400)

                    try:
                        hero_id = int(raw_id)
                    except (ValueError, TypeError):
                        raise APIError("Invalid hero ID.", 400)

                    if hero_id <= 0:
                        raise APIError("Invalid hero ID.", 400)

                    req.validated_hero_id = hero_id

                # --------------------------------------------
                # Hero existence validation
                # --------------------------------------------

                if needs_existing_hero and raw_id is not None:
                    hero = repository.get_hero(req.validated_hero_id)

                    if hero is None:
                        raise APIError("Hero not found.", 404)

                    req.validated_hero = hero

                return handler(req, *args, **kwargs)

            except APIError as e:
                return response({"error": e.message}, e.status)

            except Exception:
                logging.exception("Unexpected API error.")
                return response(
                    {"error": "Internal server error."}, 500
                )

        return wrapper
    return decorator

# ------------------------------------------------------------
# POST - Create hero
# ------------------------------------------------------------

@app.route(route="heroes", methods=["POST"])
@handle_function(needs_json=True)
def create_hero(req: func.HttpRequest):
    hero = repository.create_hero(req.validated_body)
    return response(hero, 201)

# ------------------------------------------------------------
# GET - Retrieve heroes
# ------------------------------------------------------------

@app.route(route="heroes", methods=["GET"])
@handle_function(needs_existing_hero=True)
def get_hero(req: func.HttpRequest):

    if req.params.get("id") is None:
        return response(repository.get_all_heroes())

    return response(req.validated_hero)

# ------------------------------------------------------------
# PUT - Update hero
# ------------------------------------------------------------

@app.route(route="heroes", methods=["PUT"])
@handle_function(
    needs_json=True,
    needs_id=True,
    needs_existing_hero=True
)
def update_hero(req: func.HttpRequest):
    hero = repository.update_hero(
        req.validated_hero_id,
        req.validated_body
    )

    return response(hero)

# ------------------------------------------------------------
# DELETE - Delete individual hero
# ------------------------------------------------------------

@app.route(route="heroes", methods=["DELETE"])
@handle_function(
    needs_id=True,
    needs_existing_hero=True
)
def delete_hero(req: func.HttpRequest):
    hero_name = repository.delete_hero(req.validated_hero_id)

    return response({
        "message": f"Hero '{hero_name}' deleted successfully."
    })

# ------------------------------------------------------------
# PURGE - Delete all heroes
# ------------------------------------------------------------

@app.route(route="heroes/purge", methods=["DELETE"])
@handle_function()
def purge_heroes(req: func.HttpRequest):
    total = repository.purge_heroes()

    return response({
        "message": "All heroes have been purged successfully.",
        "deleted": total
    })

# ------------------------------------------------------------
# COUNTS - Count all heroes
# ------------------------------------------------------------

@app.route(route="heroes/counts", methods=["GET"])
@handle_function()
def count_heroes(req: func.HttpRequest):
    return response({
        "count": repository.count_heroes()
    })