---
title: ue-data-assets-tables
description: Use for DataAsset, PrimaryDataAsset, DataTable, soft references, Asset Manager, and data-driven schemas. See references/asset-loading-patterns.md and references/data-driven-design.md.
---

# UE Data Assets and Tables

## Data assets

`UDataAsset` is a UObject asset for typed configuration. `UPrimaryDataAsset` supplies a
primary asset identity and participates naturally in Asset Manager rules.

```cpp fragment
UCLASS(BlueprintType)
class UItemDefinition : public UPrimaryDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly)
    FText DisplayName;
};
```

Source: `Engine/Source/Runtime/Engine/Classes/Engine/DataAsset.h`.

## Data tables

A `UDataTable` stores rows described by a `UScriptStruct`, commonly derived from
`FTableRowBase`. `FindRow` returns a pointer to row storage owned by the table; do not
retain it after the table can unload or change.

```cpp fragment
USTRUCT(BlueprintType)
struct FItemRow : public FTableRowBase
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere)
    int32 Cost = 0;
};
```

## Hard and soft references

A hard UObject reference loads and keeps the referenced object reachable according to
GC ownership. `TSoftObjectPtr` stores an asset path and can remain unresolved until a
load is requested. Soft does not mean asynchronous by itself.

```cpp fragment
UPROPERTY(EditDefaultsOnly)
TSoftObjectPtr<UTexture2D> Icon;
```

## Selection rule

Use a data asset for authored object-like configuration and inheritance-friendly
schemas. Use a data table for many homogeneous keyed rows and spreadsheet workflows.
Use primary assets when explicit Asset Manager discovery, bundles, or load policy is
part of the contract.

## Validation boundary

Compilation proves the schema and API. Asset discovery rules, cooked availability,
and designer data quality require Asset Manager, cook, or editor validation evidence.
