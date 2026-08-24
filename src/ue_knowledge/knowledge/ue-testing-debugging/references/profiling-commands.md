# Profiling Commands

Use profiling commands to capture evidence from a fixed workload and configuration.

## Frame overview

```command
stat unit
stat game
```

Use the overview to choose a narrower CPU, GPU, or frame-pacing investigation.

## GPU timing

```command
stat gpu
profilegpu
```

GPU results depend on hardware, resolution, render settings, and the captured frame.

## Unreal Insights

Start a trace with only the channels required by the question, reproduce the workload, then stop and preserve the trace artifact.

```command
trace.start cpu,frame,bookmark
trace.stop
```

## Memory

```command
memreport -full
obj list
```

Compare equivalent points in the workload and retain the report, build identity, and configuration.

## Asset loading

Use load-time and asset traces when the question concerns streaming or startup. Editor cache state can materially change results.

## Network

Use network profiling for replicated traffic and RPC volume. Record player count, authority layout, and test duration.

## Evidence boundary

Console command acceptance proves only that the command was recognized. Performance conclusions require captured artifacts, reproducible conditions, and a stated comparison.
