---
description: Use when creating or refreshing a factual Unreal project context for another agent. The output is a project-local snapshot, not public UE knowledge or a substitute for live validation.
---

# Unreal Project Context Workflow

Produce a short, dated snapshot that points to current project facts and preserves unknowns.

## 1. Establish scope

Record the exact project root, requested subsystem, allowed write scope, and excluded assets or external systems. Completion criterion: every inspected path is inside the approved scope.

## 2. Inventory current files

Read the project descriptor, relevant module rules, configuration, source directories, and named assets or maps. Record missing items as unknown. Completion criterion: every factual statement names a current file, asset inspection, command result, or explicit user decision.

## 3. Separate evidence levels

Label direct current inspection, existing artifact evidence, inference, and unknown separately. A configuration entry proves configuration; a successful build proves compilation; neither proves gameplay or human acceptance.

## 4. Capture ownership boundaries

Identify the runtime owner, editor-only owner, data authority, persistence owner, and network authority for the requested subsystem. Completion criterion: ambiguous ownership remains an explicit question.

## 5. Record verification

List commands or editor checks actually run, their time, result, and artifact path. Keep unrun checks under “Not verified”. Completion criterion: no planned check is presented as completed evidence.

## 6. Protect private project knowledge

Store project names, paths, assets, milestones, and acceptance evidence only in the project context or project index. Promote a statement to the public UE corpus only after it is generalized, desensitized, and independently verified.

## Output shape

Use these sections: Scope, Current Facts, Ownership, Evidence, Unknowns, and Next Verification. Keep the snapshot short enough that each fact can be rechecked from its cited source.
