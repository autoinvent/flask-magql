from __future__ import annotations

import typing as t

import graphql
import magql
import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.test import TestResponse

from flask_magql import MagqlExtension

basic_schema = magql.Schema()


@basic_schema.query.field(
    "greet", "String!", args={"name": magql.Argument("String!", default="World")}
)
def resolve_greet(
    parent: t.Any, info: graphql.GraphQLResolveInfo, **kwargs: t.Any
) -> str:
    name = kwargs["name"]
    return f"Hello, {name}!"


@pytest.fixture()
def schema() -> magql.Schema:
    return basic_schema


@pytest.fixture()
def ext(schema: magql.Schema) -> MagqlExtension:
    return MagqlExtension(schema)


@pytest.fixture()
def create_app(ext: MagqlExtension) -> t.Callable[[], Flask]:
    def create_app() -> Flask:
        app = Flask(__name__)
        ext.init_app(app)
        return app

    return create_app


@pytest.fixture()
def app(create_app: t.Callable[[], Flask]) -> Flask:
    return create_app()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    return app.test_client()


class TGqlRequestF(t.Protocol):
    def __call__(
        self, query: str, variables: dict[str, t.Any] | None = None
    ) -> TestResponse:
        ...
