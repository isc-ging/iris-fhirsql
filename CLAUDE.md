# CLAUDE.md

Keep committing your work! 

## What this is

`iris-fhirsql` (import package `iris_fhirsql`) is a Python client wrapping the InterSystems FHIR SQL Builder (FSB) REST API (`HS.HC.FHIRSQL`, served at `/csp/fhirsql/api/ui`). It drives the FSB workflow programmatically: credentials -> FHIR repository -> analysis -> transformation spec -> projection (generated SQL schema). Background: https://community.intersystems.com/post/fhir-sql-builder-step-step

## Commands

```bash
pip install -r requirements.txt          # requests only
pip install intersystems-irispython      # optional: only for find_fhir_servers()
python examples/complete_workflow.py     # end-to-end workflow against a live IRIS
```

### Tests

```bash
pip install -r requirements-dev.txt
pytest tests/unit                        # no IRIS needed

# integration: throwaway container "iris-ci" (ci/Dockerfile: intersystemsdc/irishealth-community + `zpm install fhir-server`)
export FHIRSQL_HOST=localhost FHIRSQL_PORT=42783 FHIRSQL_SUPERSERVER_PORT=42782 IRISUSERNAME=SuperUser IRISPASSWORD=SYS
docker compose -f docker-compose.ci.yml up -d --build --wait
pytest tests/integration
docker compose -f docker-compose.ci.yml down -v
```

`.github/workflows/ci.yml` runs the same two steps. Integration env vars have no defaults on purpose. There is no linter config or build step.

## Local IRIS environment

- The running container is `iris-fhir` (see `.iris-agentic-dev.toml`), NOT the `iris` service in `docker-compose.yml` (comment there says do not use; same ports).
- Port mapping: web `32783 -> 52773`, superserver `32782 -> 1972`. Namespace `FHIRSERVER`. Default creds `SuperUser` / `SYS`.
- `FHIRSQLClient` reads `IRISUSERNAME` / `IRISPASSWORD` env vars if username/password not passed; raises if neither.
- `iris/` holds the image build: `iris.script` installs the FHIRSERVER foundation namespace and runs `Setup.FSB.RunAll()` (`iris/src/Setup/FSB.cls`), which enables FSB web apps, installs a FHIR endpoint, loads sample bundles from `iris/fhirdata/`, and grants FSB roles.
- ObjectScript in `iris/src/` autocompiles on save.

## Architecture

- `iris_fhirsql/client.py` - `FHIRSQLClient` holds a `requests.Session` (basic auth, JSON headers) and `base_url`, and exposes one resource manager per FSB entity: `credentials`, `repositories`, `analysis`, `transform_specs`, `projections`.
- `iris_fhirsql/resources/base.py` - `BaseResource._make_request` builds URL from `client.base_url + path`, raises `APIError` on status >= 400. All resource managers subclass this.
- `iris_fhirsql/models.py` - dataclasses with `to_dict()` / `from_dict()` translating snake_case Python fields to the API's camelCase JSON (e.g. `repository_url` <-> `repositoryURL`, `spec_id` <-> `specificationId`).
- `iris_fhirsql/transformspec.py` - `TransformSpecBuilder`, local builder for spec JSON with file save/load.
- `Specifications/FHIR/SetupRequestBodies/*.body` - real captured request bodies for each FSB endpoint. Use these as ground truth for payload shapes.

### FHIR server discovery (DB API, not REST)

`RepositoryResource.find_fhir_servers()` uses `intersystems-irispython` (`iris.connect`; optional dependency, import is guarded and the method raises `ImportError` if missing) over the **superserver** port (`FHIRSQLClient(superserver_port=...)`, required for this feature). It reads `^%SYS("WebServer","Port")` for the internal web port and queries `HS_FHIRServer.RepoInstance` in each namespace. `add_fhir_servers()` registers the results as FSB repositories, skipping duplicates.

### FSB API quirks

- `POST` create endpoints return the full list of entities, not the created one; resource `create()` methods pick it out of the list by name.
- Repository `credentialsId` expects the credential **system_name**, not its id.
- Repository port must be the port as seen from inside the FSB instance. For containers, pass `internal_port` (e.g. 52773) while the client itself connects on the mapped external port. If neither `port` nor `internal_port` given, the client's port is used.
- GET/DELETE by id use the `ID` query param (verified for transform specs; `SPECID` returns 406). Analysis update uses `TASKID` (unverified).
- Transform spec payload: `{"name", "scanId", "description", "resources": [{"resourceType", "columns": [{"name", "type", "path", "index", "dataIndex", "length"}]}]}`. `path` is full FHIRPath (`Patient.name.family`). A spec with no `resources` fails with a 500 `<INVALID OREF>ValidateStructure`. The server does not validate `type` or `path`.
- Status strings observed: analysis `running` -> `completed`; projection goes straight to `Active`.
- Projected tables have `ID`, `Key` (`Patient/<id>`, same form as `subject.reference`, so join on it directly) and `RowNum` columns.
- Column `type` goes through the `$$$DataType` macro in `HS.HC.FHIRSQL.inc` (case-insensitive): `string`/`reference` -> `%String`, `number`/`integer` -> `%Integer` (ROUNDS decimals, e.g. 39.696 -> 40), `boolean` -> `%Boolean`. Anything else is passed through as an IRIS type: `%Numeric` verified to keep decimals. `length` is optional (server default String 250).
- Subtables (one row per repeating element) are nested in the parent resource, not listed in `resources`: `"subTables": [{"name", "path": "Patient.address", "columns": [...]}]`. Subtable column paths MUST be relative to the subtable path (`city`); full paths (`Patient.address.city`) are accepted but silently produce all-NULL columns. The generated table `<package>.<name>` has `Patient` (bigint = parent `ID`, so `a.Patient->FamilyName` works), `ID` (`<parentID>||<n>`) and `<name>Number` columns. Table names must be unique across the whole spec, case-insensitive (`HS.HC.FHIRSQL.Utils.FrontEnd.ValidateResource`).

### Existing code vs. project rules

Much existing code uses `data.get(...)`, empty-list fallbacks, and "return last item" fallbacks when parsing API responses. Do not copy that pattern in new code; fail loudly on missing expected fields.
