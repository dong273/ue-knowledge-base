// Validation ID: UEKB.Compile.CppReflection
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "UEKBCompileCppFoundationsFixture.generated.h"

DECLARE_DELEGATE_OneParam(FUEKBOnValue, int32);
DECLARE_MULTICAST_DELEGATE_OneParam(FUEKBOnChanged, int32);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FUEKBOnChangedDynamic, int32, Value);

USTRUCT(BlueprintType)
struct FUEKBReflectedValue
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere)
    int32 Count = 0;
};

UCLASS()
class UUEKBReflectedObject : public UObject
{
    GENERATED_BODY()

public:
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="Config")
    float MaxSpeed = 600.0f;

    UPROPERTY(VisibleInstanceOnly, BlueprintReadOnly, Category="State")
    float CurrentSpeed = 0.0f;

    UPROPERTY()
    TObjectPtr<UObject> ReferencedObject;

    UPROPERTY()
    TArray<TObjectPtr<UObject>> Objects;

    UPROPERTY(BlueprintAssignable)
    FUEKBOnChangedDynamic OnChangedDynamic;

    UFUNCTION(BlueprintCallable, Category="Example")
    void ResetState() { CurrentSpeed = 0.0f; }

    UFUNCTION(BlueprintPure, Category="Example")
    int32 GetCount() const { return 0; }

    void HandleValue(int32) {}
};
