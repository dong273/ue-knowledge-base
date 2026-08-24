# Unattended Editor Automation

Unattended execution is a process contract: deterministic inputs, explicit outputs, and an observable exit status.

## Detect the environment

Use `IsRunningCommandlet()` and `FApp::IsUnattended()` to branch away from interactive editor behavior when necessary.

## Avoid interaction

Replace modal dialogs, file pickers, and focus-dependent operations with parameters and deterministic paths. Log actionable errors.

## Save explicitly

When automation mutates packages, define which packages are dirty, which are saved, and what failure means. In-memory mutation is not durable evidence.

## Exit contract

Return a non-zero process result for failure and preserve the relevant log category. A launched command or a quiet log is not proof of success.

## Validation boundary

Run the automation from a fresh process with fixed inputs, inspect the produced artifacts, and verify the exit code. Interactive success does not substitute for unattended evidence.
