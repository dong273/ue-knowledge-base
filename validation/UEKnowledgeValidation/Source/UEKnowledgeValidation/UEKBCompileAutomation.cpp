#include "Misc/AutomationTest.h"

// Validation ID: UEKB.Compile.Automation

DEFINE_LATENT_AUTOMATION_COMMAND(FUEKBNoopLatentCommand);

bool FUEKBNoopLatentCommand::Update()
{
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(
    FUEKBAutomationApiSurfaceTest,
    "UEKnowledgeValidation.AutomationApiSurface",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FUEKBAutomationApiSurfaceTest::RunTest(const FString& Parameters)
{
    TestTrue(TEXT("True assertion"), true);
    TestFalse(TEXT("False assertion"), false);
    TestEqual(TEXT("Equal assertion"), 1, 1);
    ADD_LATENT_AUTOMATION_COMMAND(FUEKBNoopLatentCommand());
    return true;
}

namespace UEKBAutomation
{
void CompileExpectedErrorSurface(FAutomationTestBase& Test)
{
    Test.AddExpectedError(
        TEXT("UEKB expected diagnostic"),
        EAutomationExpectedErrorFlags::Contains,
        1,
        false);
}
} // namespace UEKBAutomation
