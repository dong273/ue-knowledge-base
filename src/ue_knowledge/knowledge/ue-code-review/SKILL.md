---
title: ue-code-review
description: UE C++ code review workflow for reflection, lifetime, networking, build boundaries, tests, and evidence.
tags: [ue, code-review, cpp, unreal, security, quality]
---

# UE C++ Code Review

This skill is a review procedure, not a substitute for compiling or running the changed
project on its target Unreal Engine version.

## Establish the review boundary

- Record the diff base and list changed `.h`, `.cpp`, `Build.cs`, config, and assets.
- Identify the target UE version, affected modules, runtime/editor ownership, and test path.
- Load the domain skill for networking, GAS, UI, collision, or another specialized area.

## Review checklist

- Reflection: generated-header placement, `GENERATED_BODY`, export macro, and reflected signatures.
- Lifetime: GC-visible UObject references, ownership, weak-reference checks, and container mutation.
- Networking: authority, ownership, replicated-property registration, RPC direction, and untrusted input.
- Modules: public/private dependency visibility, include ownership, and runtime/editor separation.
- Runtime: failure path, logs, Automation coverage, and any required human result.

Checklist completion is procedural evidence only. It does not prove that a reflected
declaration compiles, that an Automation assertion passed, or that a visual outcome was
accepted.

## Version-sensitive claims

Do not carry an API rule forward from an older UE release by memory. For each changed API,
locate the UE 5.7 declaration or UHT/build-rule implementation and compile a focused
probe. In particular, load the networking skill for Server RPC/`WithValidation`, the GAS
skill for ability signatures, and the module-build skill for `Build.cs` conclusions.

## Report findings

Report actionable findings by severity with a file and narrow line range. Keep baseline
debt, new regressions, compile evidence, runtime evidence, and human acceptance as
separate facts. If no finding is discovered, state which checks actually ran and what
remains unverified.
