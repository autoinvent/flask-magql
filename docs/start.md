Getting Started
===============


A Simple Example
----------------

After defining a Magql schema, create an instance of {class}`.MagqlExtension` with it.
Then call {meth}`.MagqlExtension.init_app` when creating your Flask application.

```python
# app.py
from flask import Flask
import magql
from flask_magql import MagqlExtension

schema = magql.Schema()

@schema.query.field(
    "greet", "String!", args={"name": magql.Argument("String!", default="World")}
)
def resolve_greet(parent, info, **kwargs):
    name = kwargs.pop("name")
    return f"Hello, {name}!"

magql_ext = MagqlExtension(schema)

def create_app():
    app = Flask(__name__)
    magql_ext.init_app(app)
    return app
```

Run Flask's development server.

```text
$ flask -A app.py run --debug
```

You can post queries, for example with with curl:

```text
$ curl http://127.0.0.1:5000/graphql --json '{"query": "{ greet }"}'
{
  "data": {
    "greet": "Hello, World!"
  }
}
```

Navigate to <http://127.0.0.1:5000/graphiql> to get the GraphiQL UI.

Navigate to <http://127.0.0.1:5000/schema.graphql> to get a text representation of
the GraphQL schema document.


Changing the Blueprint
---------------------

After creating the {class}`.MagqlExtension`, you can modify it before adding it
to the Flask application.

It will use a {class}`flask.Blueprint` to manage the views it adds. You can
modify the blueprint's properties before it is registered. For example, you
could move the URLs under the `/api` path:

```python
magql_ext.blueprint.url_prefix = "/api"
```


View Decorators
---------------

You may want apply some decorators to the Magql views. For example, you might be
using Flask-Login to manage authentication, and want to limit the API to logged
in users. You can pass them in as a list to the `decorators` param, or modify
the {attr}`.MagqlExtension.decorators` list after.

```python
from flask_login import login_required

magql_ext = MagqlExtension(schema, decorators=[login_required])
```

```python
from flask_login import login_required

magql_ext.decorators.append(login_required)
```

Decorators are applied in order, so the last in the list is equivalent to the
outermost when using `@decorator` syntax.

```python
decorators=[b, a]

# is equivalent to

@a
@b
def view():
    ...
```


Execution Context
-----------------

In order to share data between resolvers, you can pass context data when
executing a query. Some examples include passing a database connection or a
cache. Since this data can be arbitrary, you'll define a function that returns
that context you know your resolvers need. Decorate the function with
{meth}`.MagqlExtension.context_provider`.

```python
@magql_ext.context_provider
def gql_context():
    return {"sa_session": db.session}
```

If you're using [Flask-SQLAlchemy][] and don't set your own context provider,
Flask-Magql will automatically provide the context `{"sa_session": db.session}`,
which matches what [Magql-SQLAlchemy][] needs. If you use Magql-SQLAlchemy
without Flask-SQLAlchemy, or set your own context provider, remember to add the
`sa_session` key.

[Flask-SQLAlchemy]: https://flask-sqlalchemy.palletsprojects.com
[Magql-SQLAlchemy]: https://magql-sqlalchemy.autoinvent.dev
