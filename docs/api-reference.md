# API Reference

Back to the [user guide](guide.md).

```python
from iris_fhirsql import (FHIRSQLClient, TransformSpecBuilder,
                     FHIRSQLError, AuthenticationError, ResourceNotFoundError, ValidationError, APIError)
```

## Contents

- [FHIRSQLClient](#fhirsqlclient)
- [TransformSpecBuilder](#transformspecbuilder)
- [client.credentials](#clientcredentials)
- [client.repositories](#clientrepositories)
- [client.analysis](#clientanalysis)
- [client.transform_specs](#clienttransform_specs)
- [client.projections](#clientprojections)
- [Models](#models)
- [Exceptions](#exceptions)

## FHIRSQLClient

```python
FHIRSQLClient(hostname, port=52773, superserver_port=None, username=None, password=None, verify_ssl=True)
```

| Parameter | Description |
|-----------|-------------|
| `hostname` | IRIS host |
| `port` | Web server port. Base URL is `http://<hostname>:<port>/csp/fhirsql/api/ui` |
| `superserver_port` | Superserver port. Only required for `repositories.find_fhir_servers` |
| `username`, `password` | Fall back to `IRISUSERNAME` / `IRISPASSWORD`. `ValueError` if neither source has both |
| `verify_ssl` | Passed to `requests.Session.verify` |

Attributes: `credentials`, `repositories`, `analysis`, `transform_specs`, `projections`, `session`, `base_url`,
`hostname`, `superserver_port`.

`client.info()` returns the API version info (raises `requests.HTTPError` on failure).

## TransformSpecBuilder

```python
TransformSpecBuilder(name, scan_id, description="")
```

Full guidance: [Transform specs and subtables](transform-specs.md).

### Properties

`name`, `scan_id`, `description`, `resources` (the list of resource dicts, live not a copy).

### Methods

All mutating methods return `self`. All raise `ValidationError` on invalid input.

| Method | Description |
|--------|-------------|
| `add_resource_type(resource_type)` | Add an empty resource entry if missing |
| `add_field(resource_type, path, field_type, name, length=None, index=False, data_index=False)` | Add a column to a resource table. `path` is a full FHIRPath starting with `<resource_type>.` |
| `remove_field(resource_type, name)` | Remove a resource column |
| `add_subtable(resource_type, name, path)` | Add a subtable for a repeating element. `path` is a full FHIRPath starting with `<resource_type>.`. Name must be unique across the spec, case-insensitively |
| `add_subtable_field(resource_type, subtable, path, field_type, name, length=None, index=False, data_index=False)` | Add a column to a subtable. `path` is relative to the subtable path and must not start with `<resource_type>.` |
| `remove_subtable_field(resource_type, subtable, name)` | Remove a subtable column |
| `to_dict()` | Deep copy of the payload |
| `to_json(indent=2)` | JSON string |
| `save(file_path)` | Write JSON to a file |
| `load(file_path)` (classmethod) | Read a saved spec |
| `from_dict(spec_data)` (classmethod) | Build from a payload. Needs keys `name`, `scanId`, `description`, `resources` (`KeyError` if missing) |

### `field_type` values

`"String"`, `"Number"`/`"Integer"` (rounds decimals), `"Boolean"`, `"reference"`, `"%Numeric"` (keeps decimals),
or any IRIS type name passed through unvalidated.

## client.credentials

| Method | Returns | Description |
|--------|---------|-------------|
| `list()` | `list[Credential]` | All credentials |
| `get(credential_id)` | `Credential` | One credential |
| `create(system_name, username=None, password=None)` | `Credential` | Username and password default to the client's own login |
| `update(credential)` | `Credential` | `credential.id` is required |
| `delete(credential_id)` | `bool` | |

## client.repositories

| Method | Returns | Description |
|--------|---------|-------------|
| `list()` | `list[Repository]` | |
| `get(repository_id)` | `Repository` | |
| `create(name, host, fhir_url, port=None, internal_port=None, credentials_name=None, ssl_config=None)` | `Repository` | Port precedence: `internal_port`, then `port`, then the client's port. `credentials_name` is a credential `system_name` |
| `update(repository)` | `Repository` | `repository.id` is required |
| `delete(repository_id)` | `bool` | |
| `find_fhir_servers(namespace=None, include_disabled=False)` | `list[FHIRServer]` | DB API discovery. Needs `superserver_port`. Searches every namespace if none is given. Decommissioned endpoints are always excluded |
| `create_from_fhir_server(server, credentials_name=None, name=None, host="localhost", ssl_config=None)` | `Repository` | Register one discovered server using its internal web port |
| `add_fhir_servers(servers, credentials_name=None, host="localhost")` | `list[Repository]` | Register many; skips those already registered (same host, port, URL) |

## client.analysis

| Method | Returns | Description |
|--------|---------|-------------|
| `list()` | `list[Analysis]` | |
| `get(task_id)` | `Analysis` | Poll `status`: `running` then `completed` |
| `create(repository_id, max_distinct=None, selectivity_percentage=None)` | `Analysis` | Pass only one of `max_distinct` / `selectivity_percentage` (0-100); neither defaults to `selectivity_percentage=100` |
| `update(task_id, action="resume")` | `Analysis` | Uses the `TASKID` parameter (unverified against the server) |
| `delete(task_id)` | `bool` | |
| `get_results(task_id)` | `dict` | Raw analysis output |

## client.transform_specs

| Method | Returns | Description |
|--------|---------|-------------|
| `list()` | `list[TransformSpec]` | |
| `get(spec_id)` | `TransformSpec` | |
| `create(name, scan_id, resources, description="")` | `TransformSpec` | `resources` is the raw list. Must be non-empty; each resource needs columns, or subtables with columns |
| `create_from_builder(builder)` | `TransformSpec` | Preferred. Sends `builder.to_dict()["resources"]` |
| `update(spec)` | `TransformSpec` | `spec.id` is required |
| `delete(spec_id)` | `bool` | |

`create` picks the newest spec with a matching name from the server's list response and raises `ValueError` if
none matches.

## client.projections

| Method | Returns | Description |
|--------|---------|-------------|
| `list()` | `list[Projection]` | |
| `get(projection_id)` | `Projection` | |
| `create(repository_id, spec_id, package_name, users=None, name=None)` | `Projection` | `package_name` becomes the SQL schema. `users` are granted access |
| `update(projection_id, spec_id=None, package_name=None, users=None)` | `Projection` | |
| `delete(projection_id)` | `bool` | |
| `get_status(projection_id)` | `str` | Current status string |
| `poll_until_complete(projection_id, interval=5, max_attempts=60)` | `Projection` | Returns on `Active`/`completed`/`complete`/`success`. `RuntimeError` on `failed`/`error`. `TimeoutError` after `interval * max_attempts` seconds |

## Models

Dataclasses in `iris_fhirsql.models`, translating snake_case fields to the API's camelCase JSON via `to_dict()` and
`from_dict()`.

| Model | Fields |
|-------|--------|
| `Credential` | `id`, `system_name`, `username`, `password` |
| `Repository` | `id`, `name`, `hostname`, `port`, `repository_url`, `credentials_id`, `ssl_config` |
| `Analysis` | `id`, `fhir_repository_id`, `max_distinct`, `selectivity_percentage`, `status` |
| `TransformSpec` | `id`, `name`, `scan_id`, `spec_data` (the raw payload) |
| `Projection` | `id`, `name`, `spec_id`, `fhir_repository_id`, `package_name`, `users`, `status` |
| `FHIRServer` | `namespace`, `csp_url`, `fhir_version`, `web_port`, `is_enabled`, `name` |

## Exceptions

```
FHIRSQLError
  AuthenticationError
  ResourceNotFoundError
  ValidationError          client-side input problems
  APIError                 server status >= 400; has .status_code
```
