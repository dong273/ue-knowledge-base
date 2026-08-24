// Validation ID: UEKB.Compile.BuildRulesEditor
using UnrealBuildTool;

public class UEKnowledgeValidationEditor : ModuleRules
{
    public UEKnowledgeValidationEditor(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
        PrivateDependencyModuleNames.AddRange(new[]
        {
            "Core",
            "CoreUObject",
            "UEKnowledgeValidation",
            "UnrealEd",
            "PropertyEditor",
            "ToolMenus"
        });
    }
}
