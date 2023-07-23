from __future__ import annotations

import traceback
import typing as t

import graphql
import magql
from flask import Blueprint
from flask import current_app
from flask import Flask
from flask import render_template
from flask import request
from flask.typing import ResponseReturnValue
from flask.typing import RouteCallable

from .files import map_files_to_operations


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
        decorators: list[t.Callable[[RouteCallable], RouteCallable]] | None = None,
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

        if decorators is None:
            decorators = []

        self.decorators = decorators
        """View decorators to apply to each view function. This can be used to
        apply authentication, CORS, etc.
        """

        self._get_context: t.Callable[[], t.Any] | None = None

    def init_app(self, app: Flask) -> None:
        """Register the GraphQL API on the given Flask app.

        Applies :attr:`decorators` to each view function and registers it on
        :attr:`blueprint`, then registers the blueprint on the app.

        :param app: The app to register on.
        """
        if self._get_context is None and "sqlalchemy" in app.extensions:
            context = {"sa_session": app.extensions["sqlalchemy"].session}
            self._get_context = lambda: context

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
        context = None if self._get_context is None else self._get_context()
        return self.schema.execute(
            source=source,
            context=context,
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
            operations = request.get_json(silent=False)

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
                status = _handle_errors(result.errors, status)

            results.append(result.formatted)

        if is_single:
            return current_app.json.response(results[0]), status

        return current_app.json.response(results), status

    def _send_schema(self) -> ResponseReturnValue:
        return self.schema.to_document(), {"Content-Type": "text/plain"}

    def _graphiql_view(self) -> ResponseReturnValue:
        return render_template("magql/graphiql.html")


def _handle_errors(errors: list[graphql.GraphQLError], status: int) -> int:
    """Called by :meth:`MagqlExtension._graphql_view` if an operation result has
    errors.

    A separate function instead of inline to avoid highly nested code.

    :param errors: The list of errors from the execution result.
    :param status: The current status code.
    """
    current_status = 400

    # Set status to 500 for non-GraphQL exceptions. Log the traceback.
    for error in errors:
        oe = error.original_error

        if oe is not None and not isinstance(oe, graphql.GraphQLError):
            current_status = 500
            # Make it easy to recognize internal errors with a generic message.
            error.message = "Internal Server Error"

            # In debug mode, add the traceback to the result.
            if current_app.debug:
                error.extensions = {
                    "exception": "\n".join(
                        traceback.format_exception(type(oe), oe, oe.__traceback__)
                    )
                }

            if error.path is not None:
                message = f"Exception on GraphQL field {error.path}"
            else:
                message = "Exception on GraphQL operation"

            current_app.logger.error(message, exc_info=oe)

    # If a previous operation set 500, don't set 400.
    if current_status > status:
        return current_status

    return status
