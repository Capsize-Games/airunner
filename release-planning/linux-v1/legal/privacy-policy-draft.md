# AI Runner Desktop privacy policy -- DRAFT FOR COUNSEL REVIEW

> DRAFT FOR COUNSEL REVIEW. This is a working draft prepared from
> the L01 evidence inventory. It is not legal advice, not an
> effective notice, and must not replace the live policy until
> qualified counsel and the owner approve it. Bracketed OWNER and
> COUNSEL items below are unresolved.

- Document: `release-planning/linux-v1/legal/privacy-policy-draft.md`
- Version: 0.1 (2026-10-09)
- Issues: L02 (https://github.com/Capsize-Games/airunner/issues/2126),
  grounded in L01 (#2121,
  `release-planning/linux-v1/privacy-facts.md`)
- Structure: mirrors the canonical Capsize policy
  (`web/src/legal/privacy.ts` in the WXRQ production kit) per
  HQ `DEPLOYMENT.md`. Desktop has no accounts, so the account
  lines are dropped; the message lines cover purchase/support
  contact. Desktop sets no cookies and runs no analytics, so
  those sections are replaced by explicit no-cookie /
  no-analytics statements.
- Controller: Capsize LLC, a Colorado limited liability company.
  [OWNER: confirm entity, address, and contact channel.]

---

# Privacy policy

**Updated: [UNSET -- set on counsel approval]**

AI Runner Desktop runs on your computer with no account, no
analytics, and no advertising trackers. Your chats, files, voice,
and settings stay on your device unless you use an optional
feature that connects to someone else's service, buy the
software, or contact support.

## Privacy features

- No accounts: the Desktop application has no sign-in and no
  user database on our servers.
- No analytics, telemetry, or crash uploads in the
  application. Crash logs stay in your local data directory,
  and the optional diagnostics export only writes a file for
  you to review and share yourself.
- No cookies or advertising trackers in the application.
- The application core works offline. Online features are
  off by default and only connect after you set them up or
  explicitly use them.
- The app's internal services talk to each other only on
  your own machine (loopback) using a per-user secret token.

## What stays on your device

Chats, prompts, generated images and audio, documents you
import, voice processing, application settings, and downloaded
models live in your local data directory (by default
`~/.local/share/airunner/` on Linux; you can choose other
folders for some data). Microphone audio is transcribed on
your machine and is not saved as a recording by the
application; the resulting text is handled like anything you
type. ZIP-code to coordinates lookup uses a file shipped with
the application, not an online lookup.

Your data directory also holds your settings file, API keys
you enter, conversation history, logs, and automatic database
backups made before upgrades. These files are stored as plain
data on your computer: they are protected only by your own
device security, and you are responsible for backups.

## Optional online features

Each feature below connects only when you set it up or use
it. Your network address is visible to the other end of any
connection, as with any internet use. [COUNSEL: confirm this
characterization and whether IP-address-as-personal-data
wording is needed per territory.]

- Model downloads. Downloading models connects to
  Hugging Face and/or CivitAI. They receive which models
  you request. If you enter an access token or API key, it
  is sent to that service to authorize the download. See
  their policies: Hugging Face <https://huggingface.co/privacy>,
  CivitAI <https://civitai.com/content/privacy>.
- Web search and page reading. The search tools send your
  query to DuckDuckGo and return titles, links, and
  snippets. The page-reading and research tools fetch the
  pages you or the assistant choose, so those site
  operators see the visit. Search and research can be
  turned off in Privacy Settings.
- Weather. If you enable the weather prompt and enter your
  location, your latitude and longitude are sent to the
  Open-Meteo weather service to get current conditions.
  Results are cached on your device for one hour. See
  <https://open-meteo.com/en/terms>. This feature is off
  unless you enable it in two places: Privacy Settings and
  the assistant's weather-prompt option.
- External AI providers. If you configure OpenRouter or
  OpenAI and enter an API key, your prompts and
  conversation context are sent to that provider for
  processing under that provider's terms and policy.
  These providers are off unless you configure them.
- Local-network AI (Ollama). The Ollama option talks to
  the address you configure, normally your own machine.
  [OWNER: confirm whether a remote address is exposed in
  the shipped UI; if so, state here that prompts go to
  that address.]
- Offline library (Kiwix). Browsing the catalog and
  downloading library files connects to Kiwix library
  servers, which see what you browse and download.
- Images from links. Dropping an image link onto the
  canvas, or giving the assistant an image link, fetches
  that image from its host, which sees the request.
- Software updates. [OWNER: the in-app update check is
  designed as explicit opt-in but no update server is
  wired in this release; confirm the statement below
  before it ships.] The application does not check for
  updates on its own. If you install through the Capsize
  package repository (`apt.airunner.art`), routine package
  downloads necessarily reveal your network address to
  that server. [OWNER: state that server's log retention
  or point to the infrastructure notice.]
- Bug reports. The application links to the public issue
  tracker for bug reports; anything you write there is
  published by you on GitHub under GitHub's terms.

A research-paper search option exists in the code but is not
connected to any feature in this release; it sends nothing.
[OWNER: confirm it stays unwired, or remove the code before
release.]

## Local application storage

Your data directory holds the database, settings, models,
media, logs, backups, and the internal loopback token. There
is no export-to-us function: nothing leaves the directory
except through the optional features above or files you
share yourself (for example, a diagnostics export you send
to support).

Uninstalling the application does NOT delete your data
directory: models, media, the database, settings, logs, and
backups remain so a reinstall keeps working. To remove data,
delete it in the application (for example, delete
conversations you no longer want), delete the data directory
yourself, or use the uninstaller's explicit data-deletion
option, which removes only the listed database, settings,
and service-log files. [OWNER: confirm the exact deletion
list in the shipped uninstaller; backups, logs, models, and
custom-folder data currently survive even explicit deletion
-- see L01 section 5.]

## Purchases and messages

The application has no accounts and no in-app purchases.
[OWNER: describe the actual storefront: who sells the
software, which payment processor handles the transaction,
what buyer information Capsize receives, how long it is
kept, and where buyers exercise privacy rights. Do not ship
this section with placeholders.]

When you contact support, we receive whatever you send --
typically your name, email address, and message, plus any
files you attach such as a diagnostics export -- so we can
read it and respond. [OWNER: name the support tooling,
retention period, and whether diagnostics attachments get
special handling.]

## Service providers

- Package hosting for the Capsize repository [OWNER:
  confirm host and logging].
- Hugging Face, CivitAI, DuckDuckGo, Open-Meteo, OpenRouter,
  OpenAI, Kiwix, and any site you ask the research tools to
  read, each acting under its own terms and policy for the
  data you send it.
- The storefront and payment processor for purchases, and
  the support tooling for messages [OWNER: name them].
- We may also disclose information when the law requires it.
  [COUNSEL: confirm scope and add any required
  territory-specific disclosure language.]

## Retention and your choices

We keep purchase and support records as described above
[OWNER: state periods]. Everything else described here lives
only on your device, where it stays until you delete it;
database backups made before upgrades accumulate until you
remove them.

Your choices:

- Run fully offline: skip the optional online features and
  the application makes no external connections of its own.
- Use Privacy Settings to disable model downloads, search,
  weather, and external providers. [OWNER: the GUI toggles
  for search, weather, and external providers do not
  currently reach the background-service enforcement --
  see L01 section 3. Fix the wiring or narrow this claim
  before release.]
- Delete conversations, facts the assistant remembers,
  documents, and media in the application, or delete the
  data directory.
- Ask us about purchase or support records through the
  contact below. [OWNER: confirm the request channel and
  response process.]

## Age

AI Runner Desktop is for people 18 or older (or the age of
majority where they live). The application does not ask for
a date of birth. [COUNSEL: confirm the age line matches the
terms draft and any territory-specific age-assurance rules.]

## Region notes

[COUNSEL: the current live policy asserts Colorado Privacy
Act rights against a no-collection posture. Confirm what
this draft must say for Colorado residents, whether other
US state laws or the EU/UK GDPR or other regimes apply to
worldwide sales of a no-account desktop app plus
storefront/support processing, and supply the required
rights, legal-basis, transfer, and complaint-authority
language. Do not invent legal bases, retention periods,
encryption guarantees, or compliance certifications.]

## Changes and contact

If we change this policy, we will update the date above and
[OWNER: state how users are told -- in-app notice, website,
or both]. Questions about this policy or about purchase and
support records: [OWNER: confirm address -- current text
uses `contact@capsizegames.com`].

---

## Owner checklist (must clear before this replaces the live notice)

1. Confirm controller identity, address, contact channel.
2. Supply purchase-flow facts (seller, processor, buyer data,
   retention, rights channel) and support-flow facts
   (tooling, retention, diagnostics handling).
3. Confirm `apt.airunner.art` operator and log retention.
4. Confirm remote-Ollama UI exposure; confirm the update
   server statement.
5. Fix or narrow the Privacy Settings effectiveness claim
   (L01 section 3) and the uninstaller deletion list (L01
   section 5).
6. Decide the change-notification channel.

## Counsel questions

1. What must the policy say for Colorado, other US states,
   and non-US buyers (rights, bases, transfers, authorities)?
2. Is consent-by-use sufficient for locally processed voice
   characteristics and agent adaptation, or is explicit
   consent copy required?
3. Is the age-18 line sufficient as drafted, or is
   territory-specific age wording required?

## Reviewer fields

- Owner reviewer: PENDING -- Owner date (UTC): PENDING
- Counsel reviewer: PENDING -- Counsel date (UTC): PENDING
- Approved version and effective date: PENDING
- Acceptance: PENDING (issue #2126 stays open until
  counsel-approved text replaces the live notice)
