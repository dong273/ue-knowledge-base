---
description: Use for UE 5.7 PCG graphs, PCG components, deterministic generation, and procedural mesh runtime ownership.
---

# UE Procedural Generation

Choose PCG graphs for data-driven spatial generation and procedural mesh components for code-owned triangle geometry.

## PCG component

`UPCGComponent` owns a graph interface and exposes generation and cleanup requests.

```cpp fragment
PCGComponent->SetGraph(Graph);
PCGComponent->Generate();
PCGComponent->Cleanup();
```

A request returning is not proof that expected actors, components, or points were produced.

## Graph authoring

`UPCGGraph` contains nodes backed by settings objects. Connect compatible pins explicitly and treat graph mutation as editor or construction-time ownership unless runtime authoring is a deliberate feature.

## Determinism

Control seeds and input data, then compare stable output properties. Equal seeds cannot make external world state or nondeterministic inputs equal.

## Generated resources

Define who triggers regeneration and cleanup. Avoid leaving generated actors or components after their source component is removed or its graph changes.

## Runtime boundary

Runtime generation has scheduling, streaming, replication, and performance costs. Test the intended world and packaging configuration rather than relying on editor preview.

## Focused references

- [PCG node reference](references/pcg-node-reference.md)
- [Procedural mesh patterns](references/procedural-mesh-patterns.md)

## Verification boundary

Compilation proves PCG API and module visibility. Runtime tests must observe generated data and cleanup; visual quality requires human review.
