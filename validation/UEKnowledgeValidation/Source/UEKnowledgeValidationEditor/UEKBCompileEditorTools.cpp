#include "CoreGlobals.h"
#include "DetailLayoutBuilder.h"
#include "IDetailCustomization.h"
#include "Misc/App.h"
#include "Modules/ModuleManager.h"
#include "PropertyEditorModule.h"
#include "ScopedTransaction.h"
#include "ToolMenus.h"

// Validation ID: UEKB.Compile.EditorTools

namespace UEKBEditorTools
{
class FDetails final : public IDetailCustomization
{
public:
    static TSharedRef<IDetailCustomization> MakeInstance()
    {
        return MakeShared<FDetails>();
    }

    virtual void CustomizeDetails(IDetailLayoutBuilder& DetailBuilder) override
    {
        TSharedRef<IPropertyHandle> Property =
            DetailBuilder.GetProperty(TEXT("Value"), UObject::StaticClass());
        DetailBuilder.HideProperty(Property);
        DetailBuilder.EditCategory(TEXT("UEKB"));
        DetailBuilder.ForceRefreshDetails();
    }
};

void CompileRegistrationAndTransaction(UObject& Object)
{
    FPropertyEditorModule& PropertyEditor =
        FModuleManager::LoadModuleChecked<FPropertyEditorModule>("PropertyEditor");
    PropertyEditor.RegisterCustomClassLayout(
        TEXT("UEKBObject"),
        FOnGetDetailCustomizationInstance::CreateStatic(&FDetails::MakeInstance));
    PropertyEditor.UnregisterCustomClassLayout(TEXT("UEKBObject"));

    const FScopedTransaction Transaction(NSLOCTEXT("UEKB", "EditObject", "Edit Object"));
    Object.Modify();
    (void)UToolMenus::Get();
    (void)FApp::IsUnattended();
    (void)IsRunningCommandlet();
}
} // namespace UEKBEditorTools
