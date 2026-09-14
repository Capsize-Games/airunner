# One-issue execution prompt

Implement ONLY ISSUE_URL in its named repository. Read the issue, its prerequisite outcomes, and applicable repository instructions. Do not ingest the full project history or all sibling issues.

1. Confirm required prerequisites are complete and identify the current baseline. Preserve unrelated edits; use an isolated worktree for implementation when available.
2. Read the named files. Summarize the expected behavior change in one sentence. If facts contradict the ticket, report the specific mismatch before expanding scope.
3. Make only the scoped change and the explicitly requested regression checks. Do not weaken tests, disable features, add unrelated dependencies, or refactor neighboring code.
4. Use the ticket's targeted validation. For web code use Docker; never target the running application's database. No real inference, paid API calls, production credentials, deployment, or GUI launch in a normal implementation session.
5. Stop when this issue's acceptance conditions are met. If the change requires more than roughly five production files or a new architectural choice, return a concise proposed split. Do not start sibling issues or delegate.
6. Return: changed behavior; files; exact checks/results; unresolved risks; whether ready for review. Do not claim manual/hardware/legal/safety efficacy checks passed without evidence. Do not close the issue until its required review/acceptance is complete.

Use a small model selected by the owner. Spark is separately limited; Luna consumes the normal pool at a lower documented rate. Neither is unlimited. Do not automatically escalate, purchase credits, or use an API key.
