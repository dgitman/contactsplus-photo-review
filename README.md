# Contacts+ Photo Review

Private, single-user photo cleanup for Contacts+. Review current photos, choose a primary photo, and remove unwanted images while preserving other contact fields.

Contacts+ is the only contact source and destination. The tool does not read or write the macOS Contacts database, use AppleScript, or synchronize with iCloud. Local JSON and images are a review cache, saved choices, and recovery backups—not a separate address book. Earlier Apple Contacts prototypes have been removed from maintained source; private copies remain in ignored `outputs/retired-prototypes/`.

## Run

The existing private configuration is in `config.local.json`. Requires macOS, Python 3.10+, the 1Password CLI, and macOS `sips` for preview conversion.

```sh
python3 photo-review/server.py
```

Open http://127.0.0.1:8766 in the in-app browser. The server binds only to loopback. It initializes the review cache from the configured contact list if needed; no vCard, database export, or old snapshot is required.

## Workflow

1. **Refresh from Contacts+** loads full records by saved Contacts+ ID, or by a unique exact email match on first use, and caches current images.
2. Select **Use as primary** and mark unwanted photos.
3. **Review changes for this contact** shows the chosen primary and each removal.
4. **Apply to Contacts+** saves that preview once, backs up the record, rejects stale versions, and verifies the resulting photos and all other fields.

At least one photo must remain. Protected contacts can be displayed and refreshed but cannot be edited. Completed removals disappear from the review; downloaded originals remain available privately. Failed or uncertain writes are never retried automatically. Refresh and apply are serialized by the server. A checkmark means a saved review matches the current Contacts+ record version, not necessarily that pending changes have been applied. Checkmarks survive reopening the tool. Refreshing a changed contact replaces its checkmark with “Review again”; confirmed changes applied through this tool advance the saved review to the new version. Existing choices are adopted as the initial baseline when first loaded after this update. There is no background update checker yet.

## Credentials and local files

OAuth credentials remain in 1Password and are used only by the backend. `photo-review/authorize.py` sets up read access; `--write` requests read/write access. The callback is `http://127.0.0.1:8765/oauth/callback`. Completed authorization should not be rerun casually because it creates another token item. Set `oauth_item` and `write_oauth_item` in private configuration to the corresponding 1Password item IDs.

Contact entries use a local review `key`, display `name`, optional `fullName`, and either a Contacts+ `contactId` or an `email`. `protected: true` blocks writes. `config.example.json` contains placeholders only.

Private configuration, credentials, choices, cached contact metadata, images, and `outputs/` are ignored by Git. Backups of applied photo changes are under `outputs/photo-removals/`. No personal data belongs in commits. OAuth refresh and unattended execution are not yet implemented; 1Password may prompt for access.

## Validation

```sh
python3 -m unittest discover -s tests
node tests/test_review_state.cjs
```

Tests cover source identity, stale plans, primary selection, preserving other fields, protected contacts, single-use previews, verified catalog updates, and operation-state transitions. Live removals and source reads have been verified separately. Tests do not change real contacts.

This remains a private, locally run tool. There is no SaaS deployment, public registration, multi-user account system, or scheduled sync.
