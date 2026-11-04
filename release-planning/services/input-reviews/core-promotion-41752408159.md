# CORE promotion receipt repair

Reviewed source: `689c48d4b3f48a3c49b70b93a58163c7259be867`.
The exact revision is preserved in the owner-controlled private
`Capsize-Games/airunner-maintenance` repository on the reserved repair branch.
GitHub reported that repository private with Actions disabled.

The bounded review covered the installed interruption controller, CORE asset
preparation, candidate-run verification, release identity checks, the associated
promotion tests and CORE workflow. These scripts use Python's standard library.
The controller launches an explicitly selected executable with an isolated
environment, confines fixtures and backups to its temporary directory, probes
loopback HTTP and tracks owned process identities before cleanup. The focused
regression uses process and HTTP doubles; it does not execute the frozen package.
No dependencies, install hooks or external service destinations are added by this
repair. Existing pinned release dependencies remain unchanged; this review does
not establish full ML runtime acceptance. The GPL-3.0-only license and notices
are preserved.

Run `41752408159` rejected candidate `41751412030`: the installed interruption
probe wrote a successful receipt without `status`, although the console summary
reported `passed`. Asset preparation requires `status: passed` in the receipt.
The repair writes that field only after all existing acceptance checks succeed.
Failure receipts and promotion's rejection of incomplete evidence remain intact.
The regression passes the producer's persisted receipt into asset preparation
and separately checks rejection of absent, failed and incomplete statuses.

The service version advances to `6.1.10` so the repaired source can use a new
annotated version tag and the existing CORE candidate/promotion workflow without
moving `v6.1.9`. CI, merge and release evidence is tracked on the shared incident
card for run `41752408159`.

Follow-up review at `e80ae8c2d8d604671d0226ef53a48d5d12a1ea46`:
the private maintenance branch preserves this revision and Actions remains
disabled. Candidate run `41754243801` passed the installed upgrade probe but
failed clean-install version identity: Debian still identified the package as
`6.1.9-1` while the service reported `6.1.10`. Advance the Debian changelog
to `6.1.10-1` and check its upstream version against the service release in
the distribution compatibility tests. The version identity gate stays intact.
Review covered Debian rules/changelog, service version lookup and setup
metadata, pytest bootstrap, and the focused tests. No executable hooks or
dependency changes are introduced; GPL notices remain intact. The focused
tests read source and use local fixtures without executing adopted ML inputs.
