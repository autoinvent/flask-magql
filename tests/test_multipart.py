from __future__ import annotations

import typing as t
from io import BytesIO

import graphql
import magql
import pytest
from flask import Flask
from flask.testing import FlaskClient
from werkzeug.datastructures import FileStorage

file_schema = magql.Schema()


@file_schema.query.field("single", "String!", args={"data": "Upload!"})
def resolve_single(
    parent: t.Any, info: graphql.GraphQLResolveInfo, **kwargs: t.Any
) -> str:
    data = t.cast(FileStorage, kwargs["data"])
    return data.stream.read().decode()


@file_schema.query.field("multi", "[String!]!", args={"data": "[Upload!]!"})
def resolve_multi(
    parent: t.Any, info: graphql.GraphQLResolveInfo, **kwargs: t.Any
) -> list[str]:
    data = t.cast(list[FileStorage], kwargs["data"])
    return [i.stream.read().decode() for i in data]


@pytest.fixture()
def schema() -> magql.Schema:
    return file_schema


def test_upload(app: Flask, client: FlaskClient) -> None:
    """A file can be uploaded using the multipart spec.
    https://github.com/jaydenseric/graphql-multipart-request-spec
    """
    response = client.post(
        "/graphql",
        data={
            "operations": app.json.dumps(
                {
                    "query": "query($data: Upload!) { single(data: $data) }",
                    "variables": {"data": None},
                }
            ),
            "map": app.json.dumps({"0": ["variables.data"]}),
            "0": (BytesIO(b"file0"), "0"),
        },
    )
    assert response.json == {"data": {"single": "file0"}}


def test_upload_multiple(app: Flask, client: FlaskClient) -> None:
    """Files can be mapped to a list type."""
    response = client.post(
        "/graphql",
        data={
            "operations": app.json.dumps(
                {
                    "query": "query($data: [Upload!]!) { multi(data: $data) }",
                    "variables": {"data": [None, None]},
                }
            ),
            "map": app.json.dumps(
                {"0": ["variables.data.0"], "1": ["variables.data.1"]}
            ),
            "0": (BytesIO(b"file0"), "0"),
            "1": (BytesIO(b"file1"), "1"),
        },
    )
    assert response.json == {"data": {"multi": ["file0", "file1"]}}


def test_batch(app: Flask, client: FlaskClient) -> None:
    """Files can be applied to batch queries."""
    response = client.post(
        "/graphql",
        data={
            "operations": app.json.dumps(
                [
                    {
                        "query": "query($data: Upload!) { single(data: $data) }",
                        "variables": {"data": None},
                    },
                    {
                        "query": "query($data: [Upload!]!) { multi(data: $data) }",
                        "variables": {"data": [None]},
                    },
                ]
            ),
            "map": app.json.dumps(
                {
                    "0": ["0.variables.data"],
                    "1": ["1.variables.data.0"],
                }
            ),
            "0": (BytesIO(b"file0"), "0"),
            "1": (BytesIO(b"file1"), "1"),
        },
    )
    assert response.json == [
        {"data": {"single": "file0"}},
        {"data": {"multi": ["file1"]}},
    ]
