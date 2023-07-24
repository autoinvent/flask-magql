from __future__ import annotations

import typing as t

import graphql
import magql
import pytest
from flask import Flask
from flask.testing import FlaskClient

error_schema = magql.Schema()


@error_schema.query.field(
    "greet", "String!", args={"name": magql.Argument("String!", default="World")}
)
def resolve_greet(
    parent: t.Any, info: graphql.GraphQLResolveInfo, **kwargs: t.Any
) -> str:
    name = kwargs["name"]
    return f"Hello, {name}!"


@error_schema.query.fields["greet"].args["name"].validator
def validate_greet_name(
    info: graphql.GraphQLResolveInfo, value: str, data: t.Any
) -> None:
    if value[0].islower():
        raise magql.ValidationError("Must be capitalized.")


@error_schema.query.field("error", "String")
def resolve_error(
    parent: t.Any, info: graphql.GraphQLResolveInfo, **kwargs: t.Any
) -> None:
    raise Exception("error requested")


@pytest.fixture()
def schema() -> magql.Schema:
    return error_schema


def test_success(client: FlaskClient) -> None:
    """A valid query results in a 200 status."""
    response = client.post("/graphql", json={"query": """{ greet(name: "Test") }"""})
    assert response.status_code == 200


def test_syntax_error(client: FlaskClient) -> None:
    """A GraphQL syntax error results in a 400 status."""
    response = client.post("/graphql", json={"query": "{ greet() }"})
    assert response.status_code == 400
    json = response.get_json(silent=False)
    assert json["errors"][0]["message"].startswith("Syntax Error")


def test_type_error(client: FlaskClient) -> None:
    """An incorrect input type results in a 400 status."""
    response = client.post("/graphql", json={"query": "{ greet(name: 1) }"})
    assert response.status_code == 400
    json = response.get_json(silent=False)
    assert "non string value" in json["errors"][0]["message"]


def test_validation_error(client: FlaskClient) -> None:
    """An input validation error results in a 400 status."""
    response = client.post("/graphql", json={"query": """{ greet(name: "test") }"""})
    assert response.status_code == 400
    json = response.get_json(silent=False)
    assert json["errors"][0]["message"] == "magql argument validation"


def test_code_error(client: FlaskClient, caplog: pytest.LogCaptureFixture) -> None:
    """A Python error results in a 500 status. The error message is rewritten
    and the traceback is logged.
    """
    response = client.post("/graphql", json={"query": "{ error }"})
    assert response.status_code == 500
    json = response.get_json(silent=False)
    assert json["errors"][0]["message"] == "Internal Server Error"
    assert "extensions" not in json["errors"][0]
    assert "Exception on GraphQL field ['error']" in caplog.text
    assert "Traceback (most recent call last)" in caplog.text
    assert "Exception: error requested" in caplog.text


def test_500_debug(app: Flask, client: FlaskClient) -> None:
    """In debug mode, the traceback is added to the error."""
    app.debug = True
    response = client.post("/graphql", json={"query": "{ error }"})
    assert response.status_code == 500
    json = response.get_json(silent=False)
    assert json["errors"][0]["message"] == "Internal Server Error"
    tb_text = json["errors"][0]["extensions"]["traceback"]
    assert "Traceback (most recent call last)" in tb_text
    assert "Exception: error requested" in tb_text


def test_batch_max(client: FlaskClient) -> None:
    """A status from an earlier operation in a batch shouldn't be overwritten
    with a lower status in a later operation.
    """
    response = client.post(
        "/graphql",
        json=[{"query": "{ error }"}, {"query": """{ greet(name: "test") }"""}],
    )
    assert response.status_code == 500
    json = response.get_json(silent=False)
    assert json[0]["errors"][0]["message"] == "Internal Server Error"
    assert json[1]["errors"][0]["message"] == "magql argument validation"
