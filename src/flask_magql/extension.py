from __future__ import annotations

import typing as t

import graphql
import magql
from flask import Blueprint
from flask import current_app
from flask import Flask
from flask.typing import ResponseReturnValue

from . import _views


class MagqlExtension:
    """Serve a Magql :class:`~.magql.schema.Schema` to provide a GraphQL API.

    The following views are registered. The blueprint's name is ``magql`` by
    default, which is the prefix for each endpoint name.

    .. list-table::
        :header-rows: 1

        * - URL
          - Endpoint
          - Description
        * - ``/graphql``
          - ``.graphql``
          - The GraphQL API view. Supports the `multipart spec`__ and batched
            operations.
        * - ``/schema.graphql``
          - ``.schema``
          - The GraphQL schema document served as a text file. Useful if a tool
            does not use the introspection query to discover the API.
        * - ``/graphiql``
          - ``.graphiql``
          - The `GraphiQL`__ UI for exploring the schema and building queries.

    .. __: https://github.com/jaydenseric/graphql-multipart-request-spec
    .. __: https://github.com/graphql/graphiql/tree/main/packages/graphiql#readme

    :param schema: The schema to serve.
    :param decorators: View decorators applied to each view function. This can
        be used to apply authentication, CORS, etc.
    """

    def __init__(
        self,
        schema: magql.Schema,
        *,
        decorators: list[
            t.Callable[
                [t.Callable[..., ResponseReturnValue]],
                t.Callable[..., ResponseReturnValue],
            ]
        ]
        | None = None,
    ) -> None:
        self.schema = schema
        """The Magql schema to serve."""

        self.blueprint: Blueprint = Blueprint(
            "magql", __name__, template_folder="templates"
        )
        """The Flask blueprint that will hold these GraphQL routes and be
        registered on the app. The blueprint can be modified, for example to add
        a URL prefix: ``me.blueprint.url_prefix = "/api"``.
        """

        self.blueprint.add_url_rule(
            "/graphql",
            methods=["POST"],
            endpoint="graphql",
            view_func=_views.graphql,
        )
        self.blueprint.add_url_rule(
            "/schema.graphql",
            endpoint="schema",
            view_func=_views.schema,
        )
        self.blueprint.add_url_rule(
            "/graphiql",
            endpoint="graphiql",
            view_func=_views.graphiql,
        )
        self.blueprint.add_url_rule(
            "/conveyor/",
            endpoint="conveyor",
            view_func=_views.conveyor,
            defaults={"path": ""},
        )
        self.blueprint.add_url_rule(
            "/conveyor/<path:path>",
            endpoint="conveyor",
            view_func=_views.conveyor,
        )

        if decorators is None:
            decorators = []

        self.decorators = decorators
        """View decorators to apply to each view function. This can be used to
        apply authentication, CORS, etc.
        """

        self._get_context: t.Callable[[], t.Any] = _default_fsa_context

    def init_app(self, app: Flask) -> None:
        """Register the GraphQL API on the given Flask app.

        Applies :attr:`decorators` to each view function and registers it on
        :attr:`blueprint`, then registers the blueprint on the app.

        :param app: The app to register on.
        """
        app.extensions["magql"] = self
        app.register_blueprint(self.blueprint)

    def context_provider(self, f: t.Callable[[], t.Any]) -> t.Callable[[], t.Any]:
        """Decorate a function that should be called by :meth:`execute` to
        provide a value for ``info.context`` in resolvers.
        """
        self._get_context = f
        return f

    def execute(
        self,
        source: str,
        variables: dict[str, t.Any] | None = None,
        operation: str | None = None,
    ) -> graphql.ExecutionResult:
        """Execute a GraphQL operation (query or mutation). The SQLAlchemy
        session is passed as the context.

        :param source: The operation (query or mutation) written in GraphQL
            language to execute on the schema.
        :param variables: Maps placeholder names in the source to input values
            passed along with the request.
        :param operation: The name of the operation if the source defines
            multiple.
        """
        context = self._get_context()
        return self.schema.execute(
            source=source,
            context=context,
            variables=variables,
            operation=operation,
        )


def _default_fsa_context() -> dict[str, t.Any] | None:
    """Use the Flask-SQLAlchemy(-Lite) session."""
    try:
        db = current_app.extensions["sqlalchemy"]
    except KeyError:
        return None

    return {"sa_session": db.session}
