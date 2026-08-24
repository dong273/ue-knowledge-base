using UnrealBuildTool;

public class UEKBNegTagsEditorTarget : TargetRules
{
    public UEKBNegTagsEditorTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Editor;
        DefaultBuildSettings = BuildSettingsVersion.V6;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_7;
        ExtraModuleNames.Add("UEKBNegTags");
    }
}
