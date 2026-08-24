#pragma once

#include "Blueprint/UserWidget.h"
#include "Components/Button.h"
#include "UEKBWidgetFixture.generated.h"

// Validation ID: UEKB.Compile.UIBindWidget

UCLASS()
class UUEKBWidgetFixture : public UUserWidget
{
    GENERATED_BODY()

private:
    UPROPERTY(meta=(BindWidget))
    TObjectPtr<UButton> ConfirmButton;
};
