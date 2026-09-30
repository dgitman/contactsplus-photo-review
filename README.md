# Contacts photo tools

Local macOS tools for reviewing contact photos and testing photo-only updates while preserving notes and other contact data.

## Status

- Local photo review: candidate comparison, enlargement, source-presence labels, persistent choices, JSON export, and pending removal decisions.
- Contacts+ OAuth: read/write authorization has been verified. Secrets stay in 1Password.
- AppleScript: a single missing-photo update was saved and read back successfully; notes and related fields remained unchanged.
- Swift Contacts framework prototype: reads succeed after app authorization, but the tested save failed with Cocoa error 134092. It is retained for investigation, not as the working sync path.
- Contacts+ photo removal: a supervised single-contact test removed three historical photos, retained the current photo, and verified all other contact fields and metadata unchanged. Removal checkboxes still only queue decisions; the CLI applies an explicit reviewed plan. Automatic full sync and hourly scheduling are **not implemented/enabled**.

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
- `photo-review/authorize.py`: one-time OAuth callback on `http://127.0.0.1:8765/oauth/callback`. Reads Client ID/Client Secret from a 1Password item, requests `contacts.read` (or `contacts.read,contacts.write` with `--write`), stores tokens in a separate 1Password item, and verifies a read. Do not rerun completed setup casually; each successful run creates a token item. Set `oauth_item` for read access or `write_oauth_item` for write access in local config to the saved item's ID.
- `photo-review/prepare.py`: builds browser previews from local downloaded-candidate metadata and local configuration.
- `photo-review/refresh-presence.py`: reconciles candidate URLs with the full `contacts.get` photo list (search results can omit historical photos) and downloads missing current previews. Requires an unexpired token and interactive 1Password authorization; token refresh and unattended access are not yet implemented.

## Data handling

Private configuration, original photos, previews, contact snapshots, backup databases/vCards, review choices, exports, OAuth state, generated screenshots and binaries are ignored by Git. The repository contains source code and generic documentation only. Credentials are never written into source. Source updates should use exact IDs, fresh source state, and backups before enabling any write path. Do not edit Address Book SQLite directly.

## Validation

Python modules compile; AppleScript compiles without executing a contact write. Browser verification covered selection/reload persistence, conflict clearing, photo enlargement, search, JSON export, historical-photo removal disabling, and pending-removal persistence. Mobile layout was checked at 390px with no page overflow. The working photo-save pilot was tested separately before this repository was created; no contact mutation is part of repository validation.

## Supervised source-photo removal

`photo-review/remove-photos.py --plan PATH` backs up and previews a private JSON plan. Add `--apply` to execute an explicitly reviewed plan with the write token. The plan contains `contactId`, the fresh record's `etag`, `keepUrls`, and `removeUrls`. Both URL lists must account for the entire current photo set, and at least one photo must remain. Plans and backups belong in ignored `outputs/`, never in Git.

The tool fetches the full record, rejects stale plans, saves a backup, updates only the photo list using the existing contact data, then reads the record again to verify the remaining photos, other fields, and metadata. It does not retry uncertain writes automatically. Review `outputs/photo-removals/` if verification fails before taking any further action.

Run the removal safeguards with `python3 -m unittest discover -s tests`. OAuth token refresh and unattended access remain future work.
