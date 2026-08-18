# Fresh PIE Negative Scenarios and Human Evidence

Use a fresh PIE session when proving that a gameplay guard rejects an invalid route or interaction.

## Fresh-session contract

- Start from the documented PlayerStart or checkpoint.
- Move a real Pawn through the route using the same input path a player uses.
- Do not teleport, inject coordinates, mutate gameplay variables, disable gravity/collision, or call the success function directly.
- Do not count a scripted state edit or a synthetic overlap as human gameplay evidence.
- End the run explicitly and preserve a structured result and post-baseline log tail.

The negative test should demonstrate both the attempted invalid action and the protected outcome: no unintended signal, no duplicate completion, no illegal restore, no early ending, or no checkpoint corruption.

## Separate evidence layers

| Layer | Question answered | Evidence |
|---|---|---|
| State/route automation | Did the contract evaluate correctly? | Structured JSON and deterministic assertions |
| Machine visual gate | Was the expected content visible in the game window? | Real PIE window pixels and capture metadata |
| Human walkthrough | Can a person perform and understand the interaction? | Physical input, recording, screenshots, and review notes |

These layers are complementary. A passing fresh-PIE negative test does not prove first-player discoverability, and a visible screenshot does not prove that the input was genuinely performed. Report each result independently.

## Minimum structured log

Record the scenario name, fresh-session identifier, start state, input events, forbidden-action checks, expected guard result, actual result, screenshot/video references, runtime errors after the log baseline, and whether the human walkthrough ran. Keep `NOT_RUN` explicit when the human layer was not executed.
