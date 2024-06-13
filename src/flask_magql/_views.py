from __future__ import annotations

import collections.abc as c
import traceback
import typing as t
from functools import wraps

from flask import current_app
from flask import render_template
from flask import request
from flask.typing import ResponseReturnValue
from graphql import GraphQLError
from werkzeug.sansio.response import Response

from .files import map_files_to_operations

if t.TYPE_CHECKING:
    from .extension import MagqlExtension


def _get_magql_ext() -> MagqlExtension:
    """Get the Magql extension for the current app."""
    return current_app.extensions["magql"]  # type: ignore[no-any-return]


def _apply_ext_decorators(
    f: c.Callable[..., ResponseReturnValue],
) -> c.Callable[..., ResponseReturnValue]:
    """Apply the extension's decorators to a view function."""

    @wraps(f)
    def view(**kwargs: t.Any) -> ResponseReturnValue:
        ext = _get_magql_ext()
        decorated = f

        for d in ext.decorators:
            decorated = d(decorated)

        return decorated(**kwargs)

    return view


@_apply_ext_decorators
def graphql() -> tuple[Response, int]:
    if request.mimetype == "multipart/form-data":
        operations = current_app.json.loads(request.form["operations"])
        file_map = current_app.json.loads(request.form["map"])
        map_files_to_operations(operations, file_map, request.files)
    else:
        operations = request.get_json(silent=False)

    is_single = not isinstance(operations, list)

    if is_single:
        operations = [operations]

    ext = _get_magql_ext()
    results = []
    status = 200

    for operation in operations:
        result = ext.execute(
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


def _handle_errors(errors: list[GraphQLError], status: int) -> int:
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

        if oe is not None and not isinstance(oe, GraphQLError):
            current_status = 500
            # Make it easy to recognize internal errors with a generic message.
            error.message = "Internal Server Error"

            # In debug mode, add the traceback to the result.
            if current_app.debug:
                error.extensions = {
                    "traceback": "\n".join(
                        traceback.format_exception(type(oe), oe, oe.__traceback__)
                    )
                }

            current_app.logger.error(
                f"Exception on GraphQL field {error.path}", exc_info=oe
            )

    # If a previous operation set 500, don't set 400.
    if current_status > status:
        return current_status

    return status


@_apply_ext_decorators
def schema() -> tuple[str, dict[str, str]]:
    ext = _get_magql_ext()
    return ext.schema.to_document(), {"Content-Type": "text/plain"}


@_apply_ext_decorators
def graphiql() -> str:
    return render_template("magql/graphiql.html")


@_apply_ext_decorators
def conveyor(path: str) -> str:
    return render_template("magql/conveyor.html")
