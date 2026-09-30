# Photo review

See the [repository README](../README.md) for setup, private configuration, and limitations.

The local Python server reads current pinned-contact records and photos from Contacts+ on **Refresh from Contacts+**. Full records are fetched by source ID; a new contact match requires a unique exact email. Images are cached locally. Only current source photos appear in the review; historical originals remain on disk.

Choices are saved locally until **Review changes for this contact** opens a preview and **Apply to Contacts+** is clicked. The preview includes the chosen primary and individual removals. The backend uses the tested photo-update CLI, with a fresh record/version check, backup, and readback verification of photos and other fields. Protected contacts cannot be changed, and the last photo cannot be removed. No Apple Contacts writes happen here.

Confirmed changes update the local catalog atomically. The browser checks every three seconds, clears completed removal decisions, and shows the verified result. Failed or uncertain writes are not retried automatically. Refresh and apply operations are serialized. The server only binds to loopback and validates Host and Origin on mutations.

`prepare.py` is retained for importing older snapshots; it is not required for each refresh. Rebuilding from an old snapshot resets live review metadata, so refresh from Contacts+ afterward.
