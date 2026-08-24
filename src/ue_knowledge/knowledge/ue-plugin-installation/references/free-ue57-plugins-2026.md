# Time-Sensitive Plugin Discovery

The filename is retained for publication compatibility. This page is a verification procedure, not a current catalog of free UE 5.7 plugins.

## Why a static list expires

Price, license, supported engine versions, platform binaries, ownership, and listing availability can change independently. A repository snapshot cannot prove that a third-party offer is still free or compatible.

## Current-source requirement

For each candidate, record the current vendor or marketplace page, access date, license or price, supported UE version, supported platforms, and whether source code is provided. Prefer the vendor's authoritative listing and documentation.

## Local descriptor check

After installation, inspect the .uplugin descriptor and IPluginManager result. Confirm the plugin name, module types, loading phases, dependencies, and platform restrictions.

## Build check

Enable the plugin in an isolated validation project. Compile every target that will ship, including editor and runtime targets when both apply. A prebuilt binary for another engine changelist is not compile evidence.

## Packaging check

Package the intended platform and verify staged files plus runtime startup. Editor visibility alone is insufficient.

## Privacy and provenance

Store public URLs and neutral compatibility facts only. Exclude account identifiers, purchase history, local marketplace cache paths, machine paths, and private project names.

## Review checklist

- Current listing and license captured with an access date.
- UE 5.7 compatibility stated by an authoritative source or proven from source build.
- Runtime or editor module boundary recorded.
- Target platform package tested.
- Expiration or recheck date assigned to time-sensitive facts.
