from typing import Any
import json
from fastapi.responses import JSONResponse


class JsonapiResponse(JSONResponse):
    """
    Base response class for json:api requests, sets `Content-Type: application/vnd.api+json`.

    For detailed information, see `Starlette responses <https://www.starlette.io/responses/>`_.
    """
    media_type = 'application/vnd.api+json'

    def render(self, content: Any) -> bytes:
        if content is None:
            return b''

        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            # default=lambda obj: str(obj) if isinstance(obj, UUID) else obj.__dict__
        ).encode("utf-8")

