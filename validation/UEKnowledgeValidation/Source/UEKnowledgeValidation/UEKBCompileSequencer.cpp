#include "LevelSequence.h"
#include "LevelSequenceActor.h"
#include "LevelSequencePlayer.h"
#include "MovieSceneObjectBindingID.h"
#include "MovieSceneSequencePlaybackSettings.h"
#include "MovieSceneSequencePlayer.h"

// Validation ID: UEKB.Compile.Sequencer

namespace UEKBSequencer
{
void CompilePlayerSurface(UObject& WorldContext, ULevelSequence& Sequence)
{
    ALevelSequenceActor* SequenceActor = nullptr;
    ULevelSequencePlayer* Player =
        ULevelSequencePlayer::CreateLevelSequencePlayer(
            &WorldContext,
            &Sequence,
            FMovieSceneSequencePlaybackSettings{},
            SequenceActor);
    if (Player)
    {
        Player->Play();
        Player->Pause();
        Player->Stop();
        Player->SetPlaybackPosition(
            FMovieSceneSequencePlaybackParams(2.0f, EUpdatePositionMethod::Jump));
    }
}

void CompileBindingSurface(
    ALevelSequenceActor& SequenceActor,
    FMovieSceneObjectBindingID Binding,
    AActor& Actor)
{
    TArray<AActor*> Actors{&Actor};
    SequenceActor.SetBinding(Binding, Actors, false);
    SequenceActor.AddBinding(Binding, &Actor, false);
    SequenceActor.ResetBinding(Binding);
}
} // namespace UEKBSequencer
