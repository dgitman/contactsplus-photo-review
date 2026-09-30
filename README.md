# Contacts photo tools

Local macOS tools for reviewing contact photos and testing photo-only updates while preserving notes and other contact data.

## Status

- Local photo review: candidate comparison, enlargement, source-presence labels, persistent choices, JSON export, and pending removal decisions.
- Contacts+ OAuth: read-only authorization and a successful API read have been verified. Secrets stay in 1Password.
- AppleScript: a single missing-photo update was saved and read back successfully; notes and related fields remained unchanged.
- Swift Contacts framework prototype: reads succeed after app authorization, but the tested save failed with Cocoa error 134092. It is retained for investigation, not as the working sync path.
- Contacts+ deletion, automatic full sync, and hourly scheduling are **not implemented/enabled**. Removal checkboxes only queue decisions. Historical candidate URLs may already be absent from the source.

## Start the review tool

Requires macOS and Python 3.10+ (standard library only). From this repository:

```sh
python3 photo-review/server.py
```

Open http://127.0.0.1:8766. The server binds only to loopback. It does not modify Contacts or Contacts+. The local `photo-review/public/data.json` and `public/images/` must already exist; neither is committed.

Copy `config.example.json` to `config.local.json` for a fresh setup. Configure 1Password item references and the review contact list locally. The existing installation already has this private configuration.

## Files

- `contact-photo-sync/test-photo.applescript`: working single-contact photo-update pilot. Requires six arguments: exact local contact ID, TIFF image path, new backup vCard path, expected first name, expected last name, and expected email. Refuses an existing photo and mismatched identity. Backs up the vCard and verifies the note and image after saving. Use a new backup path for each run and independently verify the saved record. This is a pilot, not a batch synchronizer.
- `contact-photo-sync/PhotoSync.swift`: experimental Contacts-framework CLI, dry-run by default. See its authorization and save limitations above.
- `photo-review/authorize.py`: one-time OAuth callback on `http://127.0.0.1:8765/oauth/callback`. Reads Client ID/Client Secret from a 1Password item, requests `contacts.read`, stores tokens in a separate 1Password item, and verifies a read. Do not rerun completed setup casually; each successful run creates a token item. Set `oauth_item` in local config to the saved item's ID.
- `photo-review/prepare.py`: builds browser previews from local downloaded-candidate metadata and local configuration.
- `photo-review/refresh-presence.py`: reconciles candidate URLs with the current Contacts+ photo list and downloads missing current previews. Requires an unexpired token and interactive 1Password authorization; token refresh and unattended access are not yet implemented.

## Data handling

Private configuration, original photos, previews, contact snapshots, backup databases/vCards, review choices, exports, OAuth state, generated screenshots and binaries are ignored by Git. The repository contains source code and generic documentation only. Credentials are never written into source. Source updates should use exact IDs, fresh source state, and backups before enabling any write path. Do not edit Address Book SQLite directly.

## Validation

Python modules compile; AppleScript compiles without executing a contact write. Browser verification covered selection/reload persistence, conflict clearing, photo enlargement, search, JSON export, historical-photo removal disabling, and pending-removal persistence. Mobile layout was checked at 390px with no page overflow. The working photo-save pilot was tested separately before this repository was created; no contact mutation is part of repository validation.
