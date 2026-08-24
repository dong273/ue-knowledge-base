// Validation ID: UEKB.Compile.BuildRules
using UnrealBuildTool;

public class UEKnowledgeValidation : ModuleRules
{
    public UEKnowledgeValidation(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PublicDependencyModuleNames.AddRange(new[]
        {
            "Core",
            "CoreUObject",
            "Engine"
        });
        PrivateDependencyModuleNames.AddRange(new[]
        {
            "AIModule",
            "NavigationSystem",
            "GameplayAbilities",
            "GameplayTags",
            "GameplayTasks",
            "EnhancedInput",
            "UMG",
            "StateTreeModule",
            "GameplayStateTreeModule",
            "MassEntity",
            "MassCommon",
            "MassMovement",
            "MassAIBehavior",
            "GameFeatures",
            "ModularGameplay",
            "Niagara",
            "LevelSequence",
            "MovieScene",
            "Projects",
            "PCG",
            "ProceduralMeshComponent",
            "Slate",
            "SlateCore",
            "CommonUI"
        });
        if (Target.Platform == UnrealTargetPlatform.Win64)
        {
            PrivateDefinitions.Add("UEKB_PLATFORM_WINDOWS=1");
        }
    }
}
