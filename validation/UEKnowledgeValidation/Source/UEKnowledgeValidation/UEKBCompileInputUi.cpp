// Validation ID: UEKB.Compile.InputUi
#include "Blueprint/UserWidget.h"
#include "Components/InputComponent.h"
#include "UEKBCompileInputFixture.h"
#include "EnhancedInputComponent.h"
#include "EnhancedInputSubsystems.h"
#include "InputAction.h"
#include "InputActionValue.h"
#include "InputMappingContext.h"
#include "InputModifiers.h"
#include "InputTriggers.h"

static_assert(TIsDerivedFrom<UUserWidget, UWidget>::Value, "UserWidget must remain a Widget type");
static_assert(TIsDerivedFrom<UInputComponent, UActorComponent>::Value, "InputComponent must remain an actor component");
static_assert(TIsDerivedFrom<UEnhancedInputComponent, UInputComponent>::Value, "Enhanced input must remain an input component");
static_assert(TIsDerivedFrom<UInputModifierDeadZone, UInputModifier>::Value, "Dead zone remains an input modifier");
static_assert(TIsDerivedFrom<UInputTriggerHold, UInputTrigger>::Value, "Hold remains an input trigger");

class FUEKBEnhancedInputProbe
{
public:
    static void Bind(
        UEnhancedInputComponent* Component,
        const UInputAction* Action,
        UUEKBInputReceiver* Receiver)
    {
        Component->BindAction(
            Action,
            ETriggerEvent::Triggered,
            Receiver,
            &UUEKBInputReceiver::HandleMove);
    }

    static void AddContext(
        UEnhancedInputLocalPlayerSubsystem* Subsystem,
        const UInputMappingContext* Context)
    {
        Subsystem->AddMappingContext(Context, 0);
        Subsystem->RemoveMappingContext(Context);
    }
};
