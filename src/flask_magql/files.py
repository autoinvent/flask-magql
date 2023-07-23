from __future__ import annotations

import typing as t


def map_files_to_operations(
    operations: dict[str, t.Any] | list[dict[str, t.Any]],
    file_map: dict[str, list[str]],
    files: dict[str, t.Any],
) -> None:
    """Implement the `multipart spec`_, mapping file data to variables in the
    GraphQL operation. Modifies the operation's variables in place, replacing
    null values with file data.

    Arguments with the ``Upload`` type will be null in the operation's
    ``variables`` map. Multipart file keys are mapped to the position of each
    variable to replace with the file. For batched operations, each path will
    start with an integer, the index into the list of operations. For list-type
    variables, each path will end with an integer, the index into the list of
    values.

    .. _multipart spec: https://github.com/jaydenseric/graphql-multipart-request-spec

    :param operations: A single GraphQL operation, or a list of batched
        operations.
    :param file_map: Map of multipart keys to lists of dotted paths to variables
        to replace.
    :param files: Map of multipart keys to files. Flask's ``request.files``.
    """
    for files_key, paths in file_map.items():
        for path_str in paths:
            *path, last = path_str.split(".")
            current = operations

            for part in path:
                if isinstance(current, list):
                    # The first part in the path for multiple operations is an index
                    # into the list of operations.
                    current = current[int(part)]
                else:
                    current = current[part]

            # Replace the null value pointed to by the path with the file.
            if isinstance(current, list):
                # The last part in a path pointing at a list-type argument is an index
                # into the list of values.
                current[int(last)] = files[files_key]
            else:
                current[last] = files[files_key]
