from __future__ import annotations

import typing as t

import graphql
import magql
import sqlalchemy.orm as sa_orm
from flask import Blueprint
from flask import current_app
from flask import Flask
from flask import render_template
from flask import request
from flask.typing import ResponseReturnValue, RouteCallable

from .files import map_files_to_operations


class MagqlExtension:
    """Serve a Magql :class:`~.magql.schema.Schema` to provide a GraphQL API.

    The following views are registered:

    .. list-table::
        :header-rows: 1

        * - URL
          - Endpoint
          - Description
        * - ``/graphql``
          - ``.graphql``
          - The GraphQL API view. Supports the `multipart spec`_, and batched
            operations.
        * - ``/schema.graphql``
          - ``.schema``
          - The GraphQL schema document served as a text file. Useful if a tool
            does not use the introspection query to discover the API.
        * - ``/graphiql``
          - ``.graphiql``
          - The `GraphiQL`_ UI for exploring the schema and building queries.

    .. _multipart spec: https://github.com/jaydenseric/graphql-multipart-request-spec

    :param schema: The schema to serve.
    :param sa_session: The SQLAlchemy session to query data with.
    :param decorators: View decorators applied to each view function. This can
        be used to apply authentication, CORS, etc.
    """

    def __init__(
        self,
        schema: magql.Schema,
        sa_session: sa_orm.scoped_session | sa_orm.sessionmaker | sa_orm.Session,
        *,
        decorators: list[t.Callable[[RouteCallable], RouteCallable]] | None = None,
    ) -> None:
        self._sa_session = sa_session
        """The SQLAlchemy session to query data with."""

        self.schema = schema
        """The Magql schema to serve."""

        self.blueprint = Blueprint("magql", __name__, template_folder="templates")
        """The Flask blueprint that will hold these GraphQL routes and be
        registered on the app. The blueprint can be modified, for example to add
        a URL prefix: ``me.blueprint.url_prefix = "/api"``.
        """

        if decorators is None:
            decorators = []

        self.decorators = decorators
        """View decorators to apply to each view function. This can be used to
        apply authentication, CORS, etc.
        """

    def init_app(self, app: Flask) -> None:
        """Register the GraphQL API on the given Flask app.

        Applies :attr:`decorators` to each view function and registers it on
        :attr:`blueprint`, then registers the blueprint on the app.

        :param app: The app to register on.
        """
        self.blueprint.add_url_rule(
            "/graphql",
            methods=["POST"],
            endpoint="graphql",
            view_func=self._decorate(self._graphql_view),
        )
        self.blueprint.add_url_rule(
            "/schema.graphql",
            endpoint="schema",
            view_func=self._decorate(self._send_schema),
        )
        self.blueprint.add_url_rule(
            "/graphiql",
            endpoint="graphiql",
            view_func=self._decorate(self._graphiql_view),
        )
        app.register_blueprint(self.blueprint)

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
        return self.schema.execute(
            source=source,
            context=self._sa_session,
            variables=variables,
            operation=operation,
        )

    def _decorate(self, f: RouteCallable) -> RouteCallable:
        """Apply the list of view decorators to the given view function."""

        for d in self.decorators:
            f = d(f)

        return f

    def _graphql_view(self) -> ResponseReturnValue:
        if request.mimetype == "multipart/form-data":
            operations = current_app.json.loads(request.form["operations"])
            file_map = current_app.json.loads(request.form["map"])
            map_files_to_operations(operations, file_map, request.files)
        else:
            operations = request.json

        is_single = not isinstance(operations, list)

        if is_single:
            operations = [operations]

        results = []
        status = 200

        for operation in operations:
            result = self.execute(
                source=operation["query"],
                variables=operation.get("variables"),
                operation=operation.get("operationName"),
            )

            if result.errors is not None:
                status = 400

            results.append(result.formatted)

        if is_single:
            return current_app.json.response(results[0]), status

        return current_app.json.response(results), status

    def _send_schema(self):
        return self.schema.to_document(), {"Content-Type": "text/plain"}

    def _graphiql_view(self) -> ResponseReturnValue:
        return render_template("magql/graphiql.html")
