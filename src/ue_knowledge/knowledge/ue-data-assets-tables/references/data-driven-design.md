# Data-Driven Design in Unreal Engine

## Schema and instance

C++ or Blueprint defines a stable schema; assets and table rows provide authored
instances. Runtime systems consume the schema rather than embedding per-item values in
branches.

## Primary asset identity

`UPrimaryDataAsset::GetPrimaryAssetId` supplies a type/name identifier when the asset
is configured as a primary asset. Asset Manager discovery still depends on project
settings or native scan rules; inheritance alone does not prove discovery.

```cpp fragment
const FPrimaryAssetId AssetId = Definition->GetPrimaryAssetId();
if (AssetId.IsValid())
{
}
```

## Row handles

`FDataTableRowHandle` stores a table reference and row name. It is useful when authored
content should select a row without copying it into code.

```cpp fragment
UPROPERTY(EditDefaultsOnly)
FDataTableRowHandle ItemRow;
```

## References between definitions

Prefer stable IDs or soft references when definitions should remain load-independent.
Use hard references when loading and lifetime coupling are intentional.

## Validation

Validate required IDs, non-null references, ranges, and cross-record uniqueness before
shipping. Programmatic validation can prove data invariants; editor clarity and
designer usability remain human outcomes.

## Migration rule

When changing a schema, preserve compatibility deliberately or migrate authored data.
A successful C++ compile does not prove existing assets or CSV imports still deserialize
as intended.
