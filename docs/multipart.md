Uploading Files
===============

GraphQL doesn't specify a way to upload file data along with a query. The
[GraphQL multipart request specification][multipart] describes a way to map
`multipart/form-data` files to GraphQL variable values. Magql implements this
spec. See the spec for full details and examples.

Instead of posting JSON data, GraphQL query and variable data is serialized to
JSON and placed in an `operations` form field, which allows files to be uploaded
as well as part of the form data. Variables intended to be file data use `null`
as a placeholder value. An additional `map` form field is a JSON encoded mapping
of file field names to variable paths, and the server replaces the `null` values
with file data before executing the query.

Magql provides the {data}`.Upload` scalar to act as a placeholder type for
uploaded file data in argument and variable types.

```python
import magql

schema = magql.Schema()

@schema.query.field("echo_file", "String!", args={"file": "Upload!"})
def resolve_echo_file(parent, info, **kwargs):
    data = kwargs["file"]
    return data.read().decode()
```

```text
$ echo "Hello, World!" > hello.txt
$ curl http://127.0.0.1:5000/graphql \
    -F operations='{"query": "query($file: Upload!) { echo_file(file: $file) }", "variables": {"file": null}}'
    -F map='{"0": ["variables.file"]}'
    -F 0=hello.txt
{
  "data": {
    "echo_file": "Hello, World!"
  }
}
```

[multipart]: https://github.com/jaydenseric/graphql-multipart-request-spec
