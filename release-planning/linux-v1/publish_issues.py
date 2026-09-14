"""Publish the owner-requested issue handoff with resumable local receipts."""
import json
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
items=json.loads((ROOT/'issues.json').read_text())
receipt_path=ROOT/'github-receipts.json'
receipts=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}

def gh(*args):
    return subprocess.run(['gh',*args],check=True,capture_output=True,text=True).stdout.strip()

def save():
    temp=receipt_path.with_suffix('.tmp')
    temp.write_text(json.dumps(receipts,indent=2)+'\n')
    temp.replace(receipt_path)

# Reconcile an uncertain previous request before creating another issue.
def ensure_issue(key,repo,title,body_path):
    if key in receipts:
        return receipts[key]['url']
    existing=json.loads(gh('issue','list','--repo',repo,'--state','all','--limit','200','--json','number,title,url'))
    matches=[i for i in existing if i['title']==title]
    if len(matches)>1:
        raise RuntimeError(f'Duplicate issue titles for {key}; inspect before continuing')
    if matches:
        url=matches[0]['url']
    else:
        url=gh('issue','create','--repo',repo,'--title',title,'--body-file',str(body_path),'--label','linux-v1')
    receipts[key]={'repo':repo,'url':url,'number':int(url.rsplit('/',1)[1])}
    save()
    print(key,url,flush=True)
    return url

for repo in sorted({i['repo'] for i in items}):
    names=json.loads(gh('label','list','--repo',repo,'--limit','100','--json','name'))
    if not any(x['name']=='linux-v1' for x in names):
        gh('label','create','linux-v1','--repo',repo,'--color','276749','--description','Linux NVIDIA offline Desktop release handoff')

master_path=ROOT/'TRACKER.md'
requirements=(ROOT/'REQUIREMENTS.md').read_text()
master_path.write_text(requirements+'\n\n## Execution checklist\n\nChild issue links are being filed; this tracker is updated after publishing.\n')
master=ensure_issue('TRACKER','Capsize-Games/airunner','[Linux v1] Release specification and execution tracker',master_path)

kinds={
    'code':'Scoped implementation; review the resulting diff before release.',
    'webcode':'Scoped web implementation; no production database or deployment.',
    'docs':'Documentation-only; no runtime changes.',
    'design':'Bounded design/mapping gate; reviewer must resolve the interface before dependent code starts.',
    'experiment':'Isolated evidence-gathering; do not mark a product working merely because a build succeeds.',
    'review':'Evidence/review gate; a coding agent cannot approve efficacy or licensing itself.',
    'legal':'Legal draft, not effective published terms or legal certification.',
    'owner':'Owner/reviewer gate; prepare artifacts only until required decisions are recorded.',
    'manual':'Operator acceptance; a small-model session prepares scenarios, not fabricated results.'}

def body(i):
    deps='None; may start independently.' if not i['deps'] else '\n'.join('- '+receipts[k]['url'] for k in i['deps'])
    files='\n'.join('- `'+f+'`' for f in i['files'])
    checks='\n'.join('- [ ] '+c for c in i['acceptance'])
    if i['kind']=='code':
        test=f"services/tests/test_release_{i['key'].lower()}.py"
        validation=f"Add the focused regression file `{test}` (or extend the named existing suite and report its exact equivalent command). Use real data contracts with fake external/runtime boundaries, no actual model/network/database side effects.\n\n```bash\nAIRUNNER_TEST_NO_GUI_LAUNCH=1 AIRUNNER_HEADLESS=1 venv/bin/python -m pytest {test} -o addopts='' -q\n```\n\nRun directly relevant existing tests as well; list them in the result. Explicit temporary SQLite databases only. If the checkout environment cannot run the check, report the unmet prerequisite rather than install into or alter the owner's active environment."
    elif i['kind']=='webcode':
        validation="Add/run `projects/uwuchat/server/tests/test_test_database_guard.py` in an isolated Docker test process:\n\n```bash\ndocker compose run --rm --no-deps --entrypoint python -e AIRUNNER_DATABASE_URL= -e AIRUNNER_TEST_DATABASE_URL= server -m pytest projects/uwuchat/server/tests/test_test_database_guard.py -o addopts='' -q -p no:cacheprovider\n```\n\nUse doubles for database setup; do not connect to the application database."
    elif i['kind'] in {'manual','owner','review','legal'}:
        validation='Deliver the named document/results artifact with a checklist, source references, reviewer/operator fields and explicit pending results. No new app tests needed just to mirror prose. The issue remains open until its specified acceptance evidence/review exists. Never claim manual, legal or safety efficacy checks passed from static analysis.'
    else:
        validation='Verify all cited source paths and commands against this checkout; inspect the diff for scope and consistency. For an experiment record exact isolated build/check commands, outputs and artifact identities. For documentation/design, no runtime launch or new tests merely mirroring the document.'
    review='Security/policy changes require an independent review before release. ' if i['key'].startswith(('S','T')) else ''
    rendered = f"""Parent/specification: {master}

Repository: **{i['repo']}**. Work type: {kinds[i['kind']]}

## Outcome

{i['change']}

## Prerequisites

{deps}

## Read/change boundary

{files}

Paths marked new are deliverables. The `companion/` module is introduced by B01; release evidence files may be introduced by prerequisite issues. Directory entries identify a subsystem, not permission to refactor it. Normally limit implementation to five production files plus directly relevant tests; if more is needed, return a proposed split with exact files and do not omit requirements.

## Acceptance

{checks}

## Validation

{validation}

## Guardrails / handoff

Linux + NVIDIA 16 GB minimum; retain Qt and offline core; no Electron/Windows work. Preserve existing features and user data. Do not co-install the two `airunner_services` implementations. No private policy vocabulary, credentials, customer content or sensitive test imagery in source, issues or logs. No GUI/model launch, paid API call, live DB change or deployment in an ordinary coding session. Read applicable repository instructions; preserve unrelated edits. {review}One issue per session; no subagents, automatic follow-on issues or model escalation. Return behavior change, files, exact checks/results and unresolved facts. Do not close until required review/acceptance is complete.
"""


    if i['key'] in {'R01', 'B15', 'T01', 'C02', 'W04'}:
        rendered = rendered.replace(
            'no subagents, automatic follow-on issues or model escalation.',
            'no subagents, automatic follow-on implementation or model escalation. Follow-up defect/split issues explicitly required by this ticket may be filed, but not implemented in this session.')
    return rendered


remaining=[i for i in items if i['key'] not in receipts]
# Regenerate files for already-created items too so the local handoff is complete.
for i in items:
    if i['key'] in receipts and all(k in receipts for k in i['deps']):
        (ROOT/'issues'/f"{i['key']}.md").write_text(body(i))
while remaining:
    ready=[i for i in remaining if all(k in receipts for k in i['deps'])]
    if not ready:
        raise RuntimeError('Unresolved dependency graph')
    for i in ready:
        path=ROOT/'issues'/f"{i['key']}.md"
        path.write_text(body(i))
        ensure_issue(i['key'],i['repo'],i['title'],path)
        remaining.remove(i)

checklist='\n'.join(f"- [ ] [{i['key']}: {i['title'].split('] ',2)[-1]}]({receipts[i['key']]['url']}) — {i['kind']}" for i in items)
existing='''
## Existing web issues (linked, not duplicated)

- [Billing provider extraction](https://github.com/Capsize-Games/airunnerweb/issues/210) and [auth storage extraction](https://github.com/Capsize-Games/airunnerweb/issues/212): adjacent work; do not transplant this SaaS infrastructure into Desktop.
- [Hosted output moderation](https://github.com/Capsize-Games/airunnerweb/issues/112): hosted-service work; Desktop publication gates have separate ownership.
- [Existing owner OSS checklist](https://github.com/Capsize-Games/airunnerweb/issues/172): reconcile with hosted legal review.

## First small-model session

Start R03 (documentation guidance repair) only. Owner authorized one GPT-5.3-Codex-Spark session using its finite separate allowance. No autonomous implementation queue was authorized. After it returns, inspect its result and select another ready issue manually.
'''
master_path.write_text(requirements+'\n\n## Execution checklist\n\n'+checklist+'\n'+existing)
gh('issue','edit',str(receipts['TRACKER']['number']),'--repo','Capsize-Games/airunner','--body-file',str(master_path))
index=['# Linux v1 issue index','',f'Tracker: {master}','','| ID | Repository | Work type | Depends on | Issue |','|---|---|---|---|---|']
for i in items:
    index.append(f"| {i['key']} | {i['repo']} | {i['kind']} | {', '.join(i['deps']) or 'None'} | {receipts[i['key']]['url']} |")
(ROOT/'README.md').write_text('\n'.join(index)+'\n\nSee REQUIREMENTS.md for the architecture, AGENT-HANDOFF.md for the one-issue prompt, and issues/ for exact filed bodies. AUDIT.md preserves the initial evidence. No release readiness is implied by filing these issues.\n')
print('DONE',len(items),'children + tracker',flush=True)
