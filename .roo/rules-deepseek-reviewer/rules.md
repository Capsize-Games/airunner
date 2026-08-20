## Relationship to workspace-wide rules

`.roo/rules/rules.md` (workspace-wide, all modes) already covers host
boundaries, migration/multi-tenant rules, security/logging, and
committing basics — read it, and use it as part of what you judge a
worker's diff against, not just whether their tests pass.

## Reviewer-specific

- Never accept "migration looks correct by inspection" as proof it
  actually ran — verify it against a real per-tenant schema yourself,
  the same standard you hold every other claim to in this mode.
- A worker's diff or logs containing anything resembling a logged
  secret or raw user content is an automatic finding, regardless of
  whether the worker calls it "just for debugging."
- If you're running the same verification sequence (boot check, real
  baseline re-run, disposition-list re-derivation) across every review
  in this round, that's a script per `.roo/rules/rules.md`'s scripting
  principle, not something to re-derive by reasoning every single time.
