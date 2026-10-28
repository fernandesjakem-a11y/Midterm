import azure.functions as func
import logging
import json
import os
import hmac
from functools import wraps

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

heroes = {
    1: {
        "id": 1,
        "name": "Odysseus",
        "aliases": [
            "Ulysses",
            "King of Ithaca",
            "Son of Laertes"
        ],
        "status": "Mythical",
        "culture": "Ancient Greek",
        "sources": [
            "The Iliad by Homer",
            "The Odyssey by Homer"
        ],
        "historical_period": "Greek Mythological Heroic Age",
        "description": "Odysseus is the legendary king of Ithaca and a central hero of Homer's Odyssey. Known for his intelligence, cunning, and resourcefulness, he played a key role in the Trojan War and endured a long journey home, facing monsters, gods, and numerous challenges before reuniting with his wife Penelope and son Telemachus."
    }
}
next_id = 2

# ------------------------------------------------------------

def error_response(message: str, status_code: int) -> func.HttpResponse:
    return func.HttpResponse(
        message,
        status_code=status_code,
        mimetype="text/plain"
    )

class APIError(Exception):
    def __init__(self, message, status_code):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

def get_api_key():
    return os.getenv("HEROES_API_KEY")

def validate_api_key():
    def decorator(handler):
        @wraps(handler)
        def wrapper(req: func.HttpRequest, *args, **kwargs):
            expected_key = get_api_key()
            provided_key = req.headers.get("X-API-Key")

            if not provided_key or not hmac.compare_digest(provided_key, expected_key):
                return error_response("Unauthorized.", 401)

            return handler(req, *args, **kwargs)

        return wrapper
    return decorator

def handle_exceptions(required_fields=None, needs_json=False, needs_existing_hero=False, needs_hero_id=False):
    def decorator(handler):
        @wraps(handler)
        def wrapper(req: func.HttpRequest, *args, **kwargs):
            try:
                # Validate JSON body when required.
                if needs_json:
                    try:
                        body = req.get_json()
                    except (ValueError, TypeError):
                        raise APIError("Invalid JSON request body.", 400)
                    if not isinstance(body, dict):
                        raise APIError("Request body must be a JSON object.", 400)

                    if required_fields:
                        missing = [
                            field for field in required_fields
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

                # Validate hero ID and existence when required.
                raw_id = req.params.get("id")

                if needs_hero_id and not raw_id:
                    raise APIError("Missing hero ID.", 400)
                if needs_existing_hero and raw_id:
                    try:
                        hero_id = int(raw_id)
                    except (ValueError, TypeError):
                        raise APIError("Invalid hero ID.", 400)

                    if hero_id not in heroes:
                        raise APIError("Hero not found.", 404)

                    req.validated_hero_id = hero_id
                return handler(req, *args, **kwargs)

            except APIError as exc:
                return error_response(exc.message, exc.status_code)

            except Exception:
                logging.exception("Unexpected API error.")
                return error_response("Internal server error.", 500)

        return wrapper
    return decorator

# ------------------------------------------------------------

@app.route(route="heroes", methods=["POST"])
@validate_api_key()
@handle_exceptions(
    required_fields=[
        "name",
        "aliases",
        "status",
        "culture",
        "sources",
        "historical_period",
        "description"
    ],
    needs_json=True
)
def create_hero(req: func.HttpRequest) -> func.HttpResponse:
    global next_id
    body = req.validated_body
    hero = {
        "id": next_id,
        "name": body["name"],
        "aliases": body["aliases"],
        "status": body["status"],
        "culture": body["culture"],
        "sources": body["sources"],
        "historical_period": body["historical_period"],
        "description": body["description"]
    }

    heroes[next_id] = hero
    next_id += 1

    return func.HttpResponse(
        json.dumps(hero),
        status_code=201,
        mimetype="application/json"
    )

@app.route(route="heroes", methods=["GET"])
@validate_api_key()
@handle_exceptions(needs_existing_hero=True)
def get_hero(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('GET request received for heroes.')

    # If no specific ID is provided, return all heroes.
    if req.params.get('id') is None:
        return func.HttpResponse(
            json.dumps(list(heroes.values())),
            status_code=200,
            mimetype="application/json"
        )
    # If a specific ID is provided, return that hero. 
    hero = heroes[req.validated_hero_id]
    return func.HttpResponse(
        json.dumps(hero),
        status_code=200,
        mimetype="application/json"
    )

@app.route(route="heroes", methods=["PUT"])
@validate_api_key()
@handle_exceptions(
    needs_existing_hero=True,
    required_fields=[
        "name",
        "aliases",
        "status",
        "culture",
        "sources",
        "historical_period",
        "description"
    ],
    needs_json=True, needs_hero_id=True
)
def update_hero(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('PUT request received for heroes.')

    hero_id = req.validated_hero_id
    req_body = req.validated_body
    hero = heroes[hero_id]
    hero.update({
        "name": req_body["name"],
        "aliases": req_body["aliases"],
        "status": req_body["status"],
        "culture": req_body["culture"],
        "sources": req_body["sources"],
        "historical_period": req_body["historical_period"],
        "description": req_body["description"]
    })

    return func.HttpResponse(
        json.dumps(hero),
        status_code=200,
        mimetype="application/json"
    )

@app.route(route="heroes", methods=["DELETE"])
@validate_api_key()
@handle_exceptions(needs_existing_hero=True, needs_hero_id=True)
def delete_hero(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('DELETE request received for heroes.')

    hero_id = req.validated_hero_id
    hero = heroes[hero_id]
    del heroes[hero_id]

    return func.HttpResponse(
        f"Hero '{hero['name']}' deleted successfully.",
        status_code=200,
        mimetype="text/plain"
    )

@app.route(route="heroes/purge", methods=["DELETE"])
@validate_api_key()
@handle_exceptions()
def purge_heroes(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('PURGE request received for heroes.')

    heroes.clear()

    return func.HttpResponse(
        "All heroes have been purged successfully.",
        status_code=200,
        mimetype="text/plain"
    )

@app.route(route="heroes/counts", methods=["GET"])
@validate_api_key()
@handle_exceptions()
def count_heroes(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('COUNTS request received for heroes.')

    total = len(heroes)

    return func.HttpResponse(
        json.dumps({"count": total}),
        status_code=200,
        mimetype="application/json"
    )