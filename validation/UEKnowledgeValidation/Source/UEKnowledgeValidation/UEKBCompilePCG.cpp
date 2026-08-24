#include "PCGComponent.h"
#include "PCGGraph.h"
#include "PCGSettings.h"
#include "ProceduralMeshComponent.h"

// Validation ID: UEKB.Compile.PCG

namespace UEKBPCG
{
void CompilePCGSurface(
    UPCGComponent& Component,
    UPCGGraph& Graph,
    TSubclassOf<UPCGSettings> SettingsClass,
    FName SourcePin,
    FName TargetPin)
{
    Component.SetGraph(&Graph);
    Component.Generate();
    Component.Cleanup();

    UPCGSettings* SourceSettings = nullptr;
    UPCGSettings* TargetSettings = nullptr;
    UPCGNode* Source = Graph.AddNodeOfType(SettingsClass, SourceSettings);
    UPCGNode* Target = Graph.AddNodeOfType(SettingsClass, TargetSettings);
    Graph.AddEdge(Source, SourcePin, Target, TargetPin);
    Graph.RemoveNode(Target);
}

void CompileMeshSection(
    UProceduralMeshComponent& Mesh,
    const TArray<FVector>& Vertices,
    const TArray<int32>& Triangles,
    const TArray<FVector>& Normals,
    const TArray<FVector2D>& UV0,
    const TArray<FColor>& Colors,
    const TArray<FProcMeshTangent>& Tangents)
{
    Mesh.CreateMeshSection(0, Vertices, Triangles, Normals, UV0, Colors, Tangents, false);
}
} // namespace UEKBPCG
