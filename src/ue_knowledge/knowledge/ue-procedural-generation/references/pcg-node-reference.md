# PCG Node Reference

PCG nodes wrap settings and exchange tagged data through named pins.

## Add a node

Create or provide a `UPCGSettings` object and add it through `UPCGGraph`.

```cpp fragment
UPCGSettings* DefaultSettings = nullptr;
UPCGNode* Node = Graph->AddNodeOfType(SettingsClass, DefaultSettings);
```

## Connect nodes

Use `AddEdge` with the source and destination pin labels. The call requires compatible graph nodes and labels.

```cpp fragment
Graph->AddEdge(SourceNode, SourcePin, TargetNode, TargetPin);
```

## Remove nodes

Remove graph nodes through graph APIs so edges and graph state are updated consistently.

```cpp fragment
Graph->RemoveNode(Node);
```

## Settings ownership

A node references settings behavior. Decide whether settings are shared, instanced, or copied before mutating them.

## Data contracts

Spatial, parameter, and attribute data have different contracts. Confirm the input pin type and required attributes at each boundary.

## Seed flow

Treat seed combination as part of the graph contract. Record component, node, and input seeds used by a deterministic regression.

## Verification boundary

Compile node and edge APIs. Execute a small graph with fixed inputs and compare stable output data before claiming graph behavior.
