// Validation ID: UEKB.Compile.CppFoundations
#include "UEKBCompileCppFoundationsFixture.h"

DEFINE_LOG_CATEGORY_STATIC(LogUEKBCppFoundations, Log, All);

static void ProbeCppFoundations(UUEKBReflectedObject* Object)
{
    const FName RowName(TEXT("Default"));
    const FString DebugLabel = RowName.ToString();
    const FText DisplayName = NSLOCTEXT("UEKB", "DisplayName", "Example");
    UE_LOG(LogUEKBCppFoundations, Verbose, TEXT("Name=%s Text=%s"), *DebugLabel, *DisplayName.ToString());

    TArray<int32> Values;
    Values.Reserve(8);
    Values.Add(10);
    Values.Emplace(20);
    Values.RemoveAtSwap(0);

    TMap<FName, int32> Counts;
    Counts.Add(TEXT("Ammo"), 3);
    (void)Counts.Find(TEXT("Ammo"));
    for (auto It = Counts.CreateIterator(); It; ++It)
    {
        if (It.Value() <= 0)
        {
            It.RemoveCurrent();
        }
    }

    TSet<FName> Tags;
    Tags.Add(TEXT("Ready"));
    (void)Tags.Contains(TEXT("Ready"));

    FUEKBOnValue OnValue;
    OnValue.BindUObject(Object, &UUEKBReflectedObject::HandleValue);
    OnValue.ExecuteIfBound(42);

    FUEKBOnChanged OnChanged;
    const FDelegateHandle Handle = OnChanged.AddUObject(Object, &UUEKBReflectedObject::HandleValue);
    OnChanged.Broadcast(42);
    OnChanged.Remove(Handle);
}
