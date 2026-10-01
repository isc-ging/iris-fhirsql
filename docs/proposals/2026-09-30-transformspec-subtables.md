# Proposal: Subtable support in TransformSpecBuilder

Date: 2026-09-30
Status: Proposed

## Problem

FHIR resources contain repeating elements (e.g. `Patient.address`, `Patient.telecom`). FSB projects these as
subtables: one SQL row per repetition, linked to the parent row. `TransformSpecBuilder` cannot currently
express subtables, so users must hand-write the `subTables` JSON, and the server silently accepts an
incorrect form (see below).

## Verified API behaviour

Source: `HS.HC.FHIRSQL.Utils.FrontEnd` (spec template, `ValidateResource`) and
`HS.HC.FHIRSQL.Utils.ParseSpecificationToGlobal`, confirmed by a throwaway projection on the local instance.

Subtables are nested in the parent resource, not listed in `resources`:

```json
{
  "resourceType": "Patient",
  "columns": [ ... ],
  "subTables": [
    {"name": "PatientAddress", "path": "Patient.address",
     "columns": [{"name": "City", "type": "String", "path": "city", "length": 50}]}
  ]
}
```

- Subtable column paths must be relative to the subtable `path` (`city`). Full paths
  (`Patient.address.city`) are accepted but produce all-NULL columns (17 rows, 0 values in test).
- Generated table `<package>.<name>` gets `Patient` (parent `ID`), `ID` (`<parentID>||<n>`) and
  `<name>Number` columns. Both `JOIN ... ON a.Patient = p.ID` and `a.Patient->FamilyName` work.
- Table names must be unique across the whole spec, case-insensitive, including top-level resources.
- A resource with subtables but no own columns is valid; the parent table is still created.

## Proposed API

```python
builder = TransformSpecBuilder("Patient Demographics", scan_id=analysis.id)
builder.add_field("Patient", "Patient.name.family", "String", name="FamilyName", length=50)
builder.add_subtable("Patient", "PatientAddress", path="Patient.address")
builder.add_subtable_field("Patient", "PatientAddress", "city", "String", name="City", length=50)
builder.add_subtable_field("Patient", "PatientAddress", "postalCode", "String", name="PostalCode", length=10)
```

- `add_subtable(resource_type, name, path)` - creates the parent resource entry if missing.
- `add_subtable_field(resource_type, subtable, path, field_type, name, length=None, index=False, data_index=False)` -
  same column options as `add_field`.
- `remove_subtable_field(resource_type, subtable, name)` for parity with `remove_field`.

## Validation (raise `ValidationError`, fail before the server does)

- `add_subtable`: `path` must start with `<resource_type>.`; `name` must not clash (case-insensitive) with any
  resource type or subtable name already in the spec.
- `add_subtable_field`: subtable must exist; `path` must NOT start with `<resource_type>.` (guards the
  silent-NULL case); column name unique within the subtable.
- `TransformSpecResource.create`: relax the "every resource has columns" check to "columns or subtables
  with columns", matching server behaviour.

## Related changes

- `add_field` docstring: document `%Numeric` for decimals. `Number` maps to `%Integer` and rounds
  (39.696 -> 40); `%Numeric` verified to preserve values.
- `examples/complete_workflow.py`: add a `PatientAddress` subtable and a join query, restoring what the
  original example attempted.
- README step 4: short subtable example.

## Testing

Same approach as the builder rewrite: build a spec with a subtable against the live instance, project to a
throwaway package, check column population and the parent join via the DB API, then delete the
projection, spec and analysis.

## Open questions

- Nested subtables (subtable within a subtable): not in the server template; out of scope unless needed.
- Column `resourceType` field (template: "OPTIONAL STRING if path ends in .reference") - purpose not yet
  verified; not exposed initially.
