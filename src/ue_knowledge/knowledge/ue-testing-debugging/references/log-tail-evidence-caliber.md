# Log Tail Evidence Caliber

A log gate is only as wide as the window it actually scanned. State the window
explicitly; never let a clean window imply a clean session.

## Bounded windows, not whole-session claims

- Define log scans as byte-offset (or timestamp) intervals: e.g. "scan bytes
  X→Y for fatal errors, blueprint errors, ensures, crashes, and access
  exceptions".
- A scan that finds nothing in the tail window proves only that window. It is
  not "the final log gate passed" — that phrase is reserved for the gate that
  covers the final save/final validation baseline.
- Handled ensures and historical fatals stay in the log. Keep them with their
  original timestamps and line numbers; do not erase or rewrite history to
  make a report cleaner.

## Baseline invalidation

After an editor restart the old log baseline no longer describes the session.
Re-take the baseline before any claim that depends on "since startup".

## RED then GREEN keeps both

A fix is proven by two records: the failure reproduced on the pre-fix state,
and the same test passing after the fix. Keep the RED record; a GREEN result
does not retire it. Summaries that only report GREEN overstate the evidence.

## Tool summaries vs real diagnostics

A tool may report `warning_count=0` while its detailed diagnostics still list
warnings. Fix against the detailed diagnostics until empty; the summary counter
is not the acceptance surface. Single odd warnings (e.g. one external HTTP
notice) are reported as-is, not rounded down to zero.
