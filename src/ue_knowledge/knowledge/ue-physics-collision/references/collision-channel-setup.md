# Collision Channel Setup

## Project-defined channels

Custom object and trace channels are project configuration. Generated `ECC_GameTraceChannelN` values are only meaningful together with the project's channel mapping; do not copy a numeric channel alias from another project and assume the same semantics.

## Profiles and overrides

A collision profile supplies an object type, collision mode, and response container. Runtime response calls can override part of that state. When diagnosing drift, record both the selected profile name and the current response values.

## Query channel versus object type

A channel trace asks each shape how it responds to the trace channel. An object query filters by object types. Choose the query family that matches the gameplay question rather than translating between them by guesswork.

## Focused runtime override

The following fragment changes one primitive component. It does not define project channels or collision geometry:

```cpp fragment
// Fragment: TargetComponent and TraceChannel are validated project inputs.
TargetComponent->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
TargetComponent->SetCollisionResponseToChannel(TraceChannel, ECR_Block);
```

## Verification

Read back the component collision mode and response, then perform the intended query against a controlled fixture. If an event is required, verify overlap/hit notification flags separately.
