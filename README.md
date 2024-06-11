# Magql-SQLAlchemy

[Magql] is a [GraphQL] framework for Python. It's pronounced "magical", and
it is! This extension allows generating a complete API from [SQLAlchemy]
database models. After the schema is generated, it can be modified to add,
remove, or change any behavior. Here's some of the features Magql-SQLAlchemy
provides:

-   `item` and `list` queries, and `create`, `update`, and `delete`
    mutations for each model.
-   Database queries are efficient, using SQLAlchemy's relationship loading
    techniques to eagerly load relationships that are present anywhere in the
    operation structure.
-   The list query can be filtered using multiple rules. Attributes can be
    filtered across relationships. Rules can be grouped and joined using AND and
    OR. Lists can be sorted by any column and paginated.
-   The create mutation recognizes null and default column values. The update
    mutation allows updating any field independently.
-   The create and update mutations validate unique constraints.
-   A universal `search` query to search all string columns of all models.
-   A `check_delete` query to check the effects of deleting a row before doing so.

[Magql]: https://magql.autoinvent.dev
[GraphQL]: https://graphql.org
[SQLAlchemy]: https://sqlalchemy.org
