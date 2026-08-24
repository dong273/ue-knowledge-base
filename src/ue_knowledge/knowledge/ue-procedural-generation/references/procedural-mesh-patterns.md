# Procedural Mesh Patterns

`UProceduralMeshComponent` builds renderable mesh sections from caller-owned arrays.

## Module and plugin

Enable the Procedural Mesh Component plugin and depend on the `ProceduralMeshComponent` module in code that uses it.

## Create a section

Vertices and triangle indices define geometry. Optional normals, UVs, colors, tangents, and collision data must align with the vertex contract.

```cpp fragment
Mesh->CreateMeshSection(
    SectionIndex,
    Vertices,
    Triangles,
    Normals,
    UV0,
    Colors,
    Tangents,
    bCreateCollision);
```

## Update a section

Use an update API only when topology is unchanged. Recreate the section when vertex or index topology changes.

## Collision

Collision cooking is separate work and can be expensive. Choose collision creation deliberately and test the target runtime configuration.

## Normals and tangents

Provide or calculate normals and tangents appropriate to the material and topology. A successful section call does not prove shading is correct.

## Ownership

Keep source data or a regeneration recipe when the mesh must be rebuilt. Define section indices and cleanup ownership instead of relying on call order.

## Verification boundary

Compile the section API and runtime-test section counts and collision state. Inspect topology, winding, UVs, and shading visually.
