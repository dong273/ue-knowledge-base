#include "UEKBWidgetFixture.h"

#include "Blueprint/UserWidget.h"
#include "Blueprint/WidgetBlueprintLibrary.h"
#include "CommonActivatableWidget.h"
#include "Components/Button.h"
#include "Components/PanelWidget.h"
#include "Components/TextBlock.h"
#include "Components/Widget.h"
#include "Widgets/SWidget.h"

// Validation ID: UEKB.Compile.UI

namespace UEKBUI
{
void CompileWidgetSurface(
    UObject& WorldContext,
    TSubclassOf<UUserWidget> WidgetClass,
    APlayerController& PlayerController,
    UUserWidget& ExistingWidget)
{
    UUserWidget* Widget =
        UWidgetBlueprintLibrary::Create(&WorldContext, WidgetClass, &PlayerController);
    if (Widget)
    {
        Widget->AddToViewport(0);
        Widget->RemoveFromParent();
        UWidgetBlueprintLibrary::SetInputMode_GameAndUIEx(
            &PlayerController,
            Widget,
            EMouseLockMode::DoNotLock);
    }
    ExistingWidget.RemoveFromParent();
}

void CompileCommonUISurface(UCommonActivatableWidget& Screen)
{
    Screen.ActivateWidget();
    (void)Screen.IsActivated();
    Screen.DeactivateWidget();
}

static_assert(TIsDerivedFrom<UUserWidget, UWidget>::Value);
static_assert(TIsDerivedFrom<UPanelWidget, UWidget>::Value);
static_assert(TIsDerivedFrom<UTextBlock, UWidget>::Value);
static_assert(TIsDerivedFrom<UButton, UWidget>::Value);
static_assert(TIsDerivedFrom<UCommonActivatableWidget, UUserWidget>::Value);
} // namespace UEKBUI
