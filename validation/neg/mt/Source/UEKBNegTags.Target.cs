using UnrealBuildTool;

public class UEKBNegTagsTarget : TargetRules
{
    public UEKBNegTagsTarget(TargetInfo Target) : base(Target)
    {
        Type = TargetType.Game;
        DefaultBuildSettings = BuildSettingsVersion.V6;
        IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_7;
        ExtraModuleNames.Add("UEKBNegTags");
    }
}
