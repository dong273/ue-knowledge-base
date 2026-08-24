# Detail Customization Patterns

Use detail customizations to adapt editor presentation without moving runtime ownership into editor code.

## Class customization

Implement `IDetailCustomization`, return a shared instance from `MakeInstance`, and build rows in `CustomizeDetails`.

```cpp fragment
TSharedRef<IDetailCustomization> FMyDetails::MakeInstance()
{
    return MakeShared<FMyDetails>();
}
```

## Property lookup

Resolve properties through `IDetailLayoutBuilder::GetProperty`. Check the returned handle before using metadata or values.

```cpp fragment
TSharedRef<IPropertyHandle> Property =
    DetailBuilder.GetProperty(GET_MEMBER_NAME_CHECKED(UMyObject, Value));
```

## Categories and rows

Use `EditCategory` to select a category and add property or custom rows deliberately. Hiding a property changes editor presentation, not serialization or runtime behavior.

## Property-type customization

Use `IPropertyTypeCustomization` when the presentation belongs to a struct or property type rather than one UObject class.

## Refresh

Call `ForceRefreshDetails` only when the visible layout must be rebuilt. Avoid refresh loops from callbacks that the rebuild itself triggers.

```cpp fragment
DetailBuilder.ForceRefreshDetails();
```

## Lifetime

Customization delegates and shared widgets can outlive the immediate function call. Capture UObject state weakly where lifetime is not guaranteed.

## Verification boundary

Compile registration and property-handle APIs. Inspect the intended selection in the editor and exercise undo/redo before claiming the customization is usable.
