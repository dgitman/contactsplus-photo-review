# Photo review

See the [repository README](../README.md) for setup, architecture, private configuration, and current limitations.

The interface is a compact native HTML/CSS/JavaScript frontend served by Python's standard library. Review choices are atomically saved in `choices.json`; browser saves are queued. Exports contain provenance for selected candidates. Removal selections only record intent; they do not delete anything remotely. Existing exclusion decisions are not automatically converted into removal instructions.

Use `prepare.py` to import local candidates, then `refresh-presence.py` to reconcile them with current source photos. Preparation rebuilds the catalog from the original snapshot; reconcile again afterward before reviewing source removals. Neither operation deletes source data.
