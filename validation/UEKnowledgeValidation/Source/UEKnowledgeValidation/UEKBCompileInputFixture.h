// Validation ID: UEKB.Compile.InputTypes
#pragma once

#include "CoreMinimal.h"
#include "InputActionValue.h"
#include "UObject/Object.h"
#include "UEKBCompileInputFixture.generated.h"

UCLASS()
class UUEKBInputReceiver : public UObject
{
    GENERATED_BODY()

public:
    void HandleMove(const FInputActionValue& Value)
    {
        (void)Value.Get<FVector2D>();
    }
};
