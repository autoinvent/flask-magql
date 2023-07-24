from __future__ import annotations

import typing as t

from flask import Flask
from flask.testing import FlaskClient

from flask_magql import MagqlExtension


def test_graphql(client: FlaskClient) -> None:
    """/graphql executes GraphQL queries."""
    response = client.post("/graphql", json={"query": "{ greet }"})
    assert response.json == {"data": {"greet": "Hello, World!"}}


def test_graphiql(client: FlaskClient) -> None:
    """/graphiql returns an HTML page that configures GraphiQL's fetch URL."""
    response = client.get("/graphiql")
    assert response.mimetype == "text/html"
    assert 'fetch("/graphql"' in response.text


def test_schema(client: FlaskClient) -> None:
    """/schema.graphql returns a plain text GraphQL schema document."""
    response = client.get("/schema.graphql")
    assert response.mimetype == "text/plain"
    assert 'greet(name: String! = "World")' in response.text


def test_url_prefix(ext: MagqlExtension, create_app: t.Callable[[], Flask]) -> None:
    """The extension's blueprint can be modified to change the URL prefix."""
    ext.blueprint.url_prefix = "/api"
    app = create_app()

    with app.test_request_context():
        assert app.url_for("magql.graphql") == "/api/graphql"
