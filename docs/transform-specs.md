# Transform Specs and Subtables

A transform spec says which FHIR paths become which SQL columns. `TransformSpecBuilder` builds the spec JSON
locally, validates it as you go, and can save and load it as a file.

Back to the [user guide](guide.md). Runnable versions of these examples are in the [cookbook](cookbook.md).

## Contents

1. [Anatomy of a spec](#anatomy-of-a-spec)
2. [Resource tables](#resource-tables)
3. [Column types](#column-types)
4. [Subtables](#subtables)
5. [Joining tables](#joining-tables)
6. [Editing, saving and loading](#editing-saving-and-loading)
7. [Validation rules](#validation-rules)
8. [Troubleshooting](#troubleshooting)

## Anatomy of a spec

```json
{
  "name": "Patient Demographics",
  "scanId": 12,
  "description": "",
  "resources": [
    {
      "resourceType": "Patient",
      "columns": [
        {"name": "LastName", "type": "String", "path": "Patient.name.family",
         "index": false, "dataIndex": false, "length": 50}
      ],
      "subTables": [
        {"name": "PatientAddress", "path": "Patient.address",
         "columns": [{"name": "City", "type": "String", "path": "city",
                      "index": false, "dataIndex": false, "length": 50}]}
      ]
    }
  ]
}
```

- `scanId` is the analysis id the spec is based on (`analysis.id`).
- Each entry in `resources` becomes one SQL table, named after the `resourceType`.
- `subTables` live inside their parent resource. They are never listed in `resources`.

You normally never write this by hand. `builder.to_json()` prints it.

## Resource tables

```python
from iris_fhirsql import TransformSpecBuilder

builder = TransformSpecBuilder("Patient Demographics", scan_id=analysis.id)

builder.add_field("Patient", "Patient.name.family", "String", name="LastName", length=50)
builder.add_field("Patient", "Patient.name.given",  "String", name="FirstName", length=50)
builder.add_field("Patient", "Patient.gender",      "String", name="Gender", length=10, index=True)
builder.add_field("Patient", "Patient.birthDate",   "String", name="BirthDate", length=10)
```

`add_field(resource_type, path, field_type, name, length=None, index=False, data_index=False)`

| Argument | Meaning |
|----------|---------|
| `resource_type` | FHIR resource type. The resource entry is created on first use |
| `path` | Full FHIRPath, starting with `<resource_type>.` (`Patient.name.family`) |
| `field_type` | See [Column types](#column-types) |
| `name` | SQL column name, unique within the resource |
| `length` | Max length for String columns. Optional; the server default is 250 |
| `index` | Create an index on the column. Use for columns you filter or join on |
| `data_index` | Create a data index on the column |

All builder methods return the builder, so calls can be chained:

```python
(TransformSpecBuilder("Obs", scan_id=analysis.id)
    .add_field("Observation", "Observation.status", "String", name="Status", length=10)
    .add_field("Observation", "Observation.subject.reference", "String", name="Patient", length=50, index=True))
```

Note that a path that hits a repeating element (such as `Patient.name.family`, where `name` repeats) is
flattened into a single column. If you need every repetition, use a [subtable](#subtables).

## Column types

The server passes `type` through a case-insensitive macro:

| Type you give | SQL type | Notes |
|---------------|----------|-------|
| `String`, `reference` | `%String` | Give `length` |
| `Number`, `Integer` | `%Integer` | ROUNDS decimals: 39.696 is stored as 40 |
| `Boolean` | `%Boolean` | |
| `%Numeric` | `%Numeric` | Keeps decimals. Use this for measurements |
| any other value | passed through as an IRIS type | Unvalidated; only `%Numeric` has been verified |

```python
# Wrong for a lab value: 39.696 becomes 40
builder.add_field("Observation", "Observation.valueQuantity.value", "Number", name="ValueRounded")

# Right: decimals kept
builder.add_field("Observation", "Observation.valueQuantity.value", "%Numeric", name="Value")
```

## Subtables

FHIR resources contain repeating elements: a patient has several addresses, several phone numbers, several
names. A resource table can only hold one value per column, so FSB projects each repeating element as a
**subtable** with one row per repetition, linked back to the parent row.

### API

```python
builder.add_subtable(resource_type, name, path)
builder.add_subtable_field(resource_type, subtable, path, field_type, name,
                           length=None, index=False, data_index=False)
builder.remove_subtable_field(resource_type, subtable, name)
```

- `add_subtable` creates the parent resource entry if it is missing. `path` is the full FHIRPath of the
  repeating element and must start with `<resource_type>.`.
- `add_subtable_field` takes the same column options as `add_field`, but `path` is **relative to the subtable
  path**.

### Example: one row per address

```python
builder = TransformSpecBuilder("Patient With Addresses", scan_id=analysis.id)

# Patient table: one row per patient
builder.add_field("Patient", "Patient.name.family", "String", name="LastName", length=50)
builder.add_field("Patient", "Patient.gender", "String", name="Gender", length=10)

# PatientAddress table: one row per Patient.address
builder.add_subtable("Patient", "PatientAddress", path="Patient.address")
builder.add_subtable_field("Patient", "PatientAddress", "city",       "String", name="City", length=50)
builder.add_subtable_field("Patient", "PatientAddress", "state",      "String", name="State", length=50)
builder.add_subtable_field("Patient", "PatientAddress", "postalCode", "String", name="PostalCode", length=10)
builder.add_subtable_field("Patient", "PatientAddress", "country",    "String", name="Country", length=10)

spec = client.transform_specs.create_from_builder(builder)
```

### Paths must be relative

This is the single most important rule. For a subtable at `Patient.address`:

| Column path | Result |
|-------------|--------|
| `city` | Correct |
| `Patient.address.city` | Accepted by the server but **every value is silently NULL** |

The builder refuses the second form:

```python
builder.add_subtable_field("Patient", "PatientAddress", "Patient.address.city", "String", name="City")
# ValidationError: subtable path 'Patient.address.city' must be relative to the subtable path,
#                  not start with 'Patient.'
```

### Several subtables on one resource

```python
builder = TransformSpecBuilder("Patient Contact Details", scan_id=analysis.id)
builder.add_field("Patient", "Patient.name.family", "String", name="LastName", length=50)

builder.add_subtable("Patient", "PatientAddress", path="Patient.address")
builder.add_subtable_field("Patient", "PatientAddress", "city", "String", name="City", length=50)

builder.add_subtable("Patient", "PatientTelecom", path="Patient.telecom")
builder.add_subtable_field("Patient", "PatientTelecom", "system", "String", name="System", length=10)
builder.add_subtable_field("Patient", "PatientTelecom", "value",  "String", name="Value", length=50)

builder.add_subtable("Patient", "PatientName", path="Patient.name")
builder.add_subtable_field("Patient", "PatientName", "use",    "String", name="NameUse", length=10)
builder.add_subtable_field("Patient", "PatientName", "family", "String", name="Family", length=50)
```

### Subtable-only resources

A resource does not need columns of its own. A spec whose only content is subtable columns is valid, and the
parent table is still created (with just the system columns):

```python
builder = TransformSpecBuilder("Addresses Only", scan_id=analysis.id)
builder.add_subtable("Patient", "PatientAddress", path="Patient.address")
builder.add_subtable_field("Patient", "PatientAddress", "city", "String", name="City", length=50)
```

### What the server generates

For a subtable named `PatientAddress` in package `patientdata`, the table is `patientdata.PatientAddress`:

| Column | Meaning |
|--------|---------|
| `Patient` | The parent row's `ID` (a bigint) |
| `ID` | `<parentID>\|\|<n>` |
| `PatientAddressNumber` | The repetition number: `<name>Number` |
| your columns | As defined |

### Removing a subtable column

```python
builder.remove_subtable_field("Patient", "PatientAddress", "Country")
```

There is no `remove_subtable`; to drop one, rebuild the spec or edit `builder.resources` directly.

### Only one level of nesting

A subtable inside a subtable is not part of the server's spec template and is not supported.

### Verification status

The `Patient.address` subtable pattern was verified against a live instance (relative paths populate,
absolute paths give NULLs, the parent link and `->` join work). Other repeating elements such as
`Patient.telecom` and `Patient.name` follow the identical mechanism, but check the projected data the first
time you use a new path.

## Joining tables

### Subtable to parent

The `Patient` column of a subtable holds the parent `ID`, so both of these work:

```sql
-- explicit join
SELECT p.LastName, a.City, a.PostalCode
FROM patientdata.PatientAddress a
JOIN patientdata.Patient p ON a.Patient = p.ID

-- implicit join through the reference column
SELECT a.Patient->LastName, a.City
FROM patientdata.PatientAddress a
```

### Resource to resource

Use the `Key` column. It has the same `Patient/<id>` form as a `subject.reference`, so no string manipulation
is needed. This needs the reference projected as a column, and indexing it makes the join fast:

```python
builder.add_field("Observation", "Observation.subject.reference", "String",
                  name="Patient", length=50, index=True)
```

```sql
SELECT p.LastName, o.Value
FROM clinicalwarehouse.Patient p
JOIN clinicalwarehouse.Observation o ON o.Patient = p.Key
```

### Counting repetitions

```sql
SELECT p.LastName, COUNT(*) AS Addresses
FROM patientdata.Patient p
JOIN patientdata.PatientAddress a ON a.Patient = p.ID
GROUP BY p.LastName
```

## Editing, saving and loading

```python
builder.save("patient_spec.json")                         # plain JSON; commit it to version control
builder = TransformSpecBuilder.load("patient_spec.json")  # includes subtables

builder.remove_field("Patient", "Gender")
builder.to_dict()      # deep copy of the payload
builder.to_json()      # pretty printed string
```

Properties: `builder.name`, `builder.scan_id`, `builder.description`, `builder.resources`.

`load` and `from_dict` require `name`, `scanId`, `description` and `resources` and raise `KeyError` if any is
missing.

A spec is bound to the analysis in its `scanId`. When reusing a saved spec against a new repository, run a new
analysis and update `scanId` (`TransformSpecBuilder.from_dict({**data, "scanId": analysis.id})`).

## Validation rules

Checked by the builder before the server sees anything. Each raises `ValidationError`.

| Method | Rule |
|--------|------|
| `add_field` | `path` starts with `<resource_type>.`; column name unique on the resource |
| `remove_field` | Resource and column must exist |
| `add_subtable` | `path` starts with `<resource_type>.`; `name` must not clash, case-insensitively, with any resource type or subtable name already in the spec |
| `add_subtable_field` | Subtable must exist; `path` must NOT start with `<resource_type>.`; column name unique within the subtable |
| `remove_subtable_field` | Subtable and column must exist |
| `transform_specs.create` | Name and scan id present; at least one resource; each resource has columns, or subtables with columns |

Table names must be unique across the entire spec, case-insensitively, including top-level resource types.
`PatientAddress` and `patientaddress` collide. So does a subtable named `Patient` in a spec that also has a
`Patient` resource, wherever that subtable is nested.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Subtable column is all NULL | Absolute path used (older hand-written JSON) | Use the path relative to the subtable path |
| Decimal values rounded to whole numbers | Type `Number` maps to `%Integer` | Use `%Numeric` |
| `APIError` 500 `<INVALID OREF>ValidateStructure` | Spec had no `resources` | Add at least one field |
| `ValidationError: table name ... already used` | Duplicate table name, ignoring case | Rename the subtable |
| Column exists but is all NULL | Path does not exist in the data; the server does not validate paths | Compare with `client.analysis.get_results(analysis.id)` |
| Parent join returns nothing | Joined on `Key` instead of `ID`, or the reverse | Subtable `Patient` column is the parent `ID`; the `Key` column is `Patient/<id>` |
