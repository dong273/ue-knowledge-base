# Common UBT and Module Errors

## Header not found

Locate the header in the target UE source tree, identify its owning module, then add that
module to the correct public/private dependency list. The negative validation fixture
deliberately includes `AbilitySystemComponent.h` without declaring `GameplayAbilities` and must
fail with the registered compiler diagnostic.
Do not confuse this include failure with an `unresolved external symbol` linker error.

## Works only with unity or shared PCH

This usually indicates an undeclared include or dependency. Include the owning header
directly and run a clean build; do not add a broad include directory merely to preserve
accidental transitive visibility.

## Editor dependency in a runtime module

Move editor-only code and dependencies to an Editor module. Validate both the Editor
target and the non-editor game target when the change affects module boundaries.

## Generated header or reflection failure

Keep the `.generated.h` include last among a reflected header's includes and match the
reflected declaration expected by UHT. Read the first UHT error rather than treating a
later compiler cascade as the root cause.

## Expected-failure evidence

A negative probe passes only when UBT fails and the output matches the registered
diagnostic. The probe ID is reported separately and is never added to successful compile
validation IDs.
