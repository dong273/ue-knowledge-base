using UnrealBuildTool;

public class UEKBNegTags : ModuleRules
{
    public UEKBNegTags(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine" });
        // GameplayAbilities is deliberately absent. The source file must not compile.
    }
}
