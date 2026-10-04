# Blueprint Graph Authoring Pitfalls

Programmatic Blueprint graph editing fails in specific, repeatable ways.
Verified on UE 5.7 editor automation; the reliable path is per-node authoring
with read-back, plus per-layer compile gates.

## Batch creation does not scale

- Bulk create/connect operations are create-only and cap out on large graphs
  (a 512-step ceiling was hit in practice).
- Batch appliers can fail with "target pin not found" even though the node
  exists, because the applier's node-id resolution disagrees with the ids the
  creation call returned.
- Reliable shape: create one node, keep the returned node id, re-read the
  graph to get the node's real pin names, then connect only pins that were
  proven to exist. Each step is independently observable, and a failed step
  leaves a dirty asset you can continue from instead of scrapping the graph.

## Exec wiring rules

- Pure nodes (e.g. a float comparison) have no execute pin; using one as an
  exec target fails with a missing-execute-pin error.
- One exec output drives exactly one exec input; multi-driving a single exec
  input is illegal.
- After repeated incremental patches, a chain can end up mis-wired (dangling
  `then`, a comparison used as exec). Deleting the whole chain and rebuilding
  it as one clean run is safer than more edge surgery.

## Cold-load node conversion (UE 5.7)

On cold load the engine auto-converts deprecated Vector MakeStruct /
BreakStruct nodes to native Make/Vector nodes (`ConvertDeprecatedNode`), and
the old node GUIDs stop resolving. Re-discover nodes from the current graph
after a cold load; never reuse identities captured before it. Prefer native
function nodes in authored graphs.

## Named CreateDelegate pin order

Connecting the object pin before the delegate-signature pin on a named
CreateDelegate node lets the engine clear the selection. Wire all pins first,
then restore the explicit function name. Applies to newly created nodes only;
do not rewrite delegates on pre-existing nodes.

## Redirector cleanup order

1. Run fixup-redirectors so nothing references the stub.
2. Check actual remaining references (e.g. which class paths the map
   instances really use) before deleting the file.
3. Deleting the `.uasset` can fail with "being used by another process" while
   the editor holds it; release the handle first.
4. Finish with an editor restart and map reopen: actor counts, key instance
   class paths, mobility, and protected-file hashes unchanged.

## Compile and save gates

Compile each dependency layer to 0 errors / 0 warnings before the next.
When done: explicit single-asset save → close and reload the package →
recompile to 0/0 again. A save that was never explicitly issued is not
durable; unchanged on-disk hashes across a compile prove no auto-save fired.
