# Windows Non-ASCII Project Paths and Build Diagnostics

Observed with Unreal Engine 5.7.4 and the Windows toolchain.

## Failure pattern

Some Windows build and response-file paths do not survive non-ASCII characters consistently. The visible error may mention `cl.exe`, a response file, or a missing header even though the source and module dependency are correct. Treat the path encoding as a separate hypothesis before changing Build.cs dependencies.

## Bounded workaround

Use an ASCII-only junction or checkout path for the project during the build diagnostic:

```text
<ASCII_PROJECT_ROOT>\Project.uproject
```

Keep the real project and source files unchanged. Point the build invocation at the ASCII path, and use `-NoUBA` when the goal is to isolate the ordinary compiler/response-file path from Unreal Build Accelerator behavior. Remove the workaround only after a clean build from the original path is independently confirmed.

## Verification order

1. Reproduce the failure from the original path and save the exact compiler/response-file error.
2. Build from the ASCII path with the same target, configuration, and engine version.
3. If the ASCII build passes, classify the issue as path/toolchain handling rather than a module contract failure.
4. Re-run the original path after the environment or toolchain fix; do not claim the junction is a product fix.

Do not place a real user profile, drive path, project name, or machine-specific junction in public documentation. Use placeholders such as `<ASCII_PROJECT_ROOT>`.
