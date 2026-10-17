"""
CSRF (Cross-Site Request Forgery) protection.

The admin UI authenticates with a cookie session. Without a
CSRF token, any page on the school network could silently
submit a form to this server and the browser would attach the
admin's session cookie to it — deleting students, approving
leaves or changing settings without the admin ever knowing.

Protection works by giving each session a secret token:

    1. The token is stored in the (signed) session cookie.
    2. Every template receives it and renders it as a hidden
       field inside each POST form, and JavaScript sends it
       as the X-CSRF-Token header.
    3. This middleware rejects any unsafe request whose token
       is missing or does not match the session.

An attacker's page can force the browser to *send* a request,
but it cannot read the session cookie to learn the token, so
the forged request fails validation.
"""

import secrets
from urllib.parse import parse_qs

from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


# ============================================================
# CONFIGURATION
# ============================================================

# Key the token is stored under inside the session cookie.
CSRF_SESSION_KEY = "csrf_token"

# Hidden form field name used by HTML forms.
CSRF_FORM_FIELD = "csrf_token"

# Request header used by fetch() calls.
CSRF_HEADER_NAME = "x-csrf-token"

# Methods that do not change server state and therefore
# need no token.
SAFE_METHODS = frozenset(
    {
        "GET",
        "HEAD",
        "OPTIONS",
        "TRACE",
    }
)

# Paths exempt from validation.
#
# The login form is exempt because it is submitted *before* a
# session exists. That is not a hole worth worrying about: the
# worst a forged login does is log the victim in as the
# attacker, and an attacker who already knows valid admin
# credentials does not need CSRF.
EXEMPT_PATHS = frozenset(
    {
        "/login",
    }
)

FORM_CONTENT_TYPE = "application/x-www-form-urlencoded"


# ============================================================
# TOKEN HELPERS
# ============================================================


def get_csrf_token(request: Request) -> str:
    """
    Return this session's CSRF token, creating one if the
    session does not have a token yet.
    """

    token = request.session.get(CSRF_SESSION_KEY)

    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token

    return token


def rotate_csrf_token(request: Request) -> str:
    """
    Issue a brand new CSRF token.

    Called on login so that a token observed before
    authentication cannot be reused afterwards.
    """

    token = secrets.token_urlsafe(32)
    request.session[CSRF_SESSION_KEY] = token

    return token


def csrf_context(request: Request) -> dict:
    """
    Starlette template context processor.

    Registering this on Jinja2Templates makes `csrf_token`
    available to every template automatically, so no route has
    to remember to pass it.
    """

    return {
        "csrf_token": get_csrf_token(request),
    }


# ============================================================
# MIDDLEWARE
# ============================================================


class CSRFMiddleware:
    """
    Reject unsafe requests that do not carry a valid token.

    Implemented as raw ASGI rather than BaseHTTPMiddleware
    because this app serves a long-lived MJPEG stream, and
    BaseHTTPMiddleware sits in the response path where it
    interferes with open-ended streaming responses. This
    middleware only inspects the *request*, then steps out of
    the way.

    Must be installed so that it runs INSIDE SessionMiddleware
    (i.e. added to the app before SessionMiddleware is added),
    because it reads the session from the ASGI scope.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")

        if (
            method in SAFE_METHODS
            or path in EXEMPT_PATHS
        ):
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        submitted = request.headers.get(
            CSRF_HEADER_NAME
        )

        # The body may need to be read to find the token in a
        # form field. Anything read here must be handed back
        # to the route, otherwise the route sees an empty
        # body.
        downstream_receive = receive

        content_type = request.headers.get(
            "content-type",
            "",
        )

        if (
            not submitted
            and content_type.startswith(
                FORM_CONTENT_TYPE
            )
        ):
            body = await request.body()

            submitted = _token_from_form_body(body)

            downstream_receive = _replay_body(body)

        expected = scope.get("session", {}).get(
            CSRF_SESSION_KEY
        )

        valid = bool(
            expected
            and submitted
            and secrets.compare_digest(
                str(submitted),
                str(expected),
            )
        )

        if not valid:
            response = _rejection_response(request)

            await response(
                scope,
                downstream_receive,
                send,
            )
            return

        await self.app(
            scope,
            downstream_receive,
            send,
        )


# ============================================================
# INTERNAL HELPERS
# ============================================================


def _token_from_form_body(body: bytes) -> str | None:
    """
    Pull the CSRF field out of a urlencoded form body.
    """

    try:
        decoded = body.decode("utf-8")
    except UnicodeDecodeError:
        return None

    fields = parse_qs(
        decoded,
        keep_blank_values=True,
    )

    values = fields.get(CSRF_FORM_FIELD)

    if not values:
        return None

    return values[0]


def _replay_body(body: bytes) -> Receive:
    """
    Build a receive callable that hands an already-consumed
    request body to the route as if it were never read.
    """

    delivered = False

    async def receive() -> Message:
        nonlocal delivered

        if delivered:
            return {"type": "http.disconnect"}

        delivered = True

        return {
            "type": "http.request",
            "body": body,
            "more_body": False,
        }

    return receive


def _rejection_response(request: Request):
    """
    Build the 403 sent for a failed CSRF check.

    JSON for fetch() callers, plain text for form posts. Plain
    text (never HTML built from request data) so the error
    page cannot itself become an injection point.
    """

    message = (
        "Security check failed. Your session may have "
        "expired. Please reload the page and try again."
    )

    accepts = request.headers.get("accept", "")

    if "application/json" in accepts:
        return JSONResponse(
            {"detail": message},
            status_code=403,
        )

    return PlainTextResponse(
        message,
        status_code=403,
    )
