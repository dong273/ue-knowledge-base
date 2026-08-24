# Query Optimization

Optimize retrieval with representative queries and explicit failure classes rather than one aggregate recall number.

## Use grounded terms

Include the relevant API or engine concept when known. Natural Chinese queries may be expanded by the maintained glossary and spoken-language dictionary.

## Evaluate sections

A document-level hit can still miss the required answer. Record the expected source and, for collision-prone cases, the expected heading within Top 3.

## Confusable queries

Test requests where a command being accepted is not the same as the intended outcome: scheduled versus completed, active versus visible, or request success versus gameplay success.

## Unsupported queries

Maintain public questions with no public coverage. The false-positive rate measures whether the system invents support from a merely high relative score.

## Score boundary

Use normalized ranking only within one index. Keep `raw_score` for diagnostics and never compare it across public and project indexes.

## Regression loop

Freeze the dataset, rebuild the target index, run the evaluator, and inspect Top 3 before changing a query or expectation. Change the dataset only when the semantically correct source or heading differs from the recorded contract.

## Performance

Measure MCP startup, first query, and hot query against a same-machine baseline with an explicit regression allowance.
