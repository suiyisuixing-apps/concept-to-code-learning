# Runnable examples

Use a minimal reviewed example with expected output. Execute only in an authorized
temporary directory or Git worktree; never edit the enterprise checkout. Record
command, interpreter, input hashes, exit code, stdout/stderr, and expected-result check.
Use a timeout, no shell interpolation, and no inherited secrets. A worktree is not a
security sandbox: arbitrary untrusted repository execution requires separate isolation.
VERIFIED_RUNNABLE requires actual exit zero and the expected result, not plausible code.
