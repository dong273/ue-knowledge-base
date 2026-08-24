using UnrealBuildTool;

public class UEKnowledgeValidationEditorTarget : TargetRules
{
    public UEKnowledgeValidationEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V6;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_7;
        ExtraModuleNames.Add("UEKnowledgeValidation");
    }
}
