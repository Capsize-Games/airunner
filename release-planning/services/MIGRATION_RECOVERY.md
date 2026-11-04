# Migration recovery dispositions

This page records the current downgrade behavior for the revisions named by [GitHub issue #2358](https://github.com/Capsize-Games/airunner/issues/2358) and related data-integrity revisions. It describes the migration source in this repository; it does not establish whether a particular database has applied those revisions or has a usable backup.

| Revision | Upgrade operation | Downgrade disposition |
|---|---|---|
| `2d6569089de6` | Drops `tts_settings`. | Rejects downgrade before mutation. Restore a pre-upgrade backup to recover dropped rows. |
| `3b1030ac9b9c` | Drops `splitter_settings`. | Rejects downgrade before mutation. Restore a pre-upgrade backup to recover dropped rows. |
| `50e125c2e188` | Drops `window_settings`. | Rejects downgrade before mutation. Restore a pre-upgrade backup to recover dropped rows. |
| `5dbbe8800572` | No-op historical marker in the current source. | No-op; reversible because the paired upgrade changes no schema or data. |
| `7e840c47b899` | Drops `tabs` if the table exists. | Rejects downgrade before mutation. Restore a pre-upgrade backup to recover dropped rows. |
| `9d76c1e50d8f` | Drops `rag_settings.enabled`. | Rejects downgrade before mutation. Restore a pre-upgrade backup to recover column values. |
| `b96406b64944` | Drops `conversations.bot_mood`. | Rejects downgrade before mutation. The current migration removes only `bot_mood`; the historical filename also mentions `bot_mood_emoji`. |
| `c0f6743e26e9` | No-op historical marker in the current source. | No-op; reversible because the paired upgrade changes no schema or data. |
| `c42b9a3d807a` | Drops `application_settings.show_nsfw_warning` and `application_settings.nsfw_filter`. | Rejects downgrade before mutation. Restore a pre-upgrade backup to recover column values. |

Related revisions have separate dispositions:

- `449cbcdca2c4` inserts missing bootstrap color-balance rows without overwriting existing values. Its downgrade rejects because the migration has no per-row provenance to distinguish inserted rows from later user edits.
- `dffe1636eeaf` drops `speech_t5_settings` and does not create an XTTS table. Its downgrade rejects rather than creating an empty SpeechT5 table.
- `201952ffe80a` replaces `llm_generator_settings.current_conversation` with `current_chatbot`. The exact conversation ID cannot be reconstructed from a chatbot ID: multiple conversations can reference the same chatbot. The migration now rejects upgrade before mutation when the legacy column contains any non-NULL value, and rejects downgrade because the old conversation pointer cannot be restored. A NULL-only legacy column can be removed; unrelated settings rows remain. If this historical revision already ran before the guard was added, editing the revision does not recover values it previously discarded; a pre-upgrade backup is needed if those values matter.

The migration tests run on temporary SQLite databases. They verify that rejected operations leave table structure and stored values unchanged, no-op revisions remain schema/data-neutral, bootstrap rows are preserved, and the `201952ffe80a` NULL and absent-column paths create the expected `current_chatbot` column and foreign key without changing unrelated settings rows.
