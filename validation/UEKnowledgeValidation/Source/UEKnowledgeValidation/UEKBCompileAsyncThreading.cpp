#include "Async/Async.h"
#include "Async/AsyncWork.h"
#include "HAL/CriticalSection.h"
#include "HAL/PlatformAtomics.h"
#include "Misc/ScopeLock.h"
#include "Tasks/Task.h"
#include "UObject/WeakObjectPtr.h"

// Validation ID: UEKB.Compile.AsyncThreading

namespace UEKBAsyncThreading
{
void CompileAsyncSurface(UObject* Owner)
{
    TFuture<int32> Future = Async(EAsyncExecution::ThreadPool, []
    {
        return 1;
    });
    (void)Future;

    TWeakObjectPtr<UObject> WeakOwner(Owner);
    AsyncTask(ENamedThreads::GameThread, [WeakOwner]
    {
        (void)WeakOwner.Get();
    });

    UE::Tasks::TTask<int32> Task = UE::Tasks::Launch(
        UE_SOURCE_LOCATION,
        [] { return 1; }
    );
    (void)Task;
}

void CompileSynchronizationSurface(FCriticalSection& StateLock, int32& SharedResult)
{
    FScopeLock Guard(&StateLock);
    SharedResult = 1;
    TAtomic<bool> Completed(false);
    Completed.Store(true);
    (void)Completed.Load();
}
} // namespace UEKBAsyncThreading
