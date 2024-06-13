from __future__ import annotations

import typing as t

import graphql
import magql
import pytest
from flask import Flask
from flask_sqlalchemy_lite import SQLAlchemy

from flask_magql import MagqlExtension

context_schema = magql.Schema()


@context_schema.query.field("echo", "JSON")
def resolve_echo(
    parent: t.Any, info: graphql.GraphQLResolveInfo, **kwargs: t.Any
) -> t.Any:
    return info.context


@pytest.fixture()
def schema() -> magql.Schema:
    return context_schema


@pytest.fixture()
def db() -> SQLAlchemy:
    return SQLAlchemy()


@pytest.fixture()
def create_app(db: SQLAlchemy, ext: MagqlExtension) -> t.Callable[[], Flask]:
    def create_app() -> Flask:
        app = Flask(__name__)
        app.config["SQLALCHEMY_ENGINES"] = {"default": "sqlite://"}
        db.init_app(app)
        ext.init_app(app)
        return app

    return create_app


def test_automatic_context(app: Flask, ext: MagqlExtension, db: SQLAlchemy) -> None:
    """If no context provider is set and Flask-SQLAlchemy is enabled, db.session
    is provided in the context.
    """
    with app.app_context():
        session = db.session
        result = ext.execute("{ echo }")

    assert result.data is not None
    assert result.data["echo"] == {"sa_session": session}


def test_manual_context(ext: MagqlExtension, create_app: t.Callable[[], Flask]) -> None:
    """If a context provider is set, the automatic behavior does not override it."""

    @ext.context_provider
    def other_context() -> dict[str, t.Any]:
        return {"a": 1, "b": "c"}

    app = create_app()

    with app.app_context():
        result = ext.execute("{ echo }")

    assert result.data is not None
    assert result.data["echo"] == {"a": 1, "b": "c"}
