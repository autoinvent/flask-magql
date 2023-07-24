from __future__ import annotations

import typing as t
from functools import wraps

import magql
import pytest
from flask import Flask
from flask import request
from flask.typing import ResponseReturnValue
from werkzeug.exceptions import Unauthorized

from flask_magql import MagqlExtension


def auth_required(
    f: t.Callable[..., ResponseReturnValue]
) -> t.Callable[..., ResponseReturnValue]:
    @wraps(f)
    def decorated(*args: t.Any, **kwargs: t.Any) -> ResponseReturnValue:
        if request.authorization is None:
            raise Unauthorized()

        return f(*args, **kwargs)

    return decorated


def create_ext_init(schema: magql.Schema) -> MagqlExtension:
    return MagqlExtension(schema, decorators=[auth_required])


def create_ext_append(schema: magql.Schema) -> MagqlExtension:
    ext = MagqlExtension(schema)
    ext.decorators.append(auth_required)
    return ext


@pytest.mark.parametrize("create_ext", [create_ext_init, create_ext_append])
def test_decorators(
    schema: magql.Schema, create_ext: t.Callable[[magql.Schema], MagqlExtension]
) -> None:
    """An authorization decorator can be applied to all routes."""
    ext = create_ext(schema)
    app = Flask(__name__)
    ext.init_app(app)
    client = app.test_client()

    assert client.post("/graphql").status_code == 401
    assert client.get("/graphiql").status_code == 401
    assert client.get("/schema.graphql").status_code == 401

    response = client.post(
        "/graphql", json={"query": "{ greet }"}, auth=("magql", "magql")
    )
    assert response.status_code == 200
