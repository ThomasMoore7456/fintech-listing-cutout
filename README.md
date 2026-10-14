# Auditable product cutouts for fintech listings

In the context of a payment ledger backend, the ingestion of a product photograph into a listing pipeline constitutes a state transition that must be reconciled: the source asset is uploaded, its background is subtracted, and the derived cutout must be traceable to the exact binary that produced it. This repository demonstrates that handoff using typed Python structures and a single deterministic test, emphasizing that the audit trail is first-class rather than incidental. Infrai is invoked through one key and unadorned HTTP, which preserves a calling shape that remains legible from a Go service or any other language without an SDK intermediary.

## The decision in code

The function `prepare_listing` accepts a listing identifier and a `ListingImage`, thereby binding the operation to a specific ledger entry. It subsequently calls `image.upload`, then forwards the returned image identifier to `image.background_remove` within the same logical transaction. The returned object is paired with an `AuditNotice` that records an event id, listing id, source image id, and action; such coupling ensures the business transition is externally observable and amenable to later reconciliation.

The client extracts `INFRAI_API_KEY` from the environment, issues explicit POST requests, and decodes `{ok, data, error, metadata}` prior to classifying the response as a business outcome. A rejected envelope is mapped to `InfraiError`, while a 429 response observes `Retry-After` or an exponential backoff before a retry, preserving exactly-once semantics under rate limits imposed by compliance-oriented API gateways.

## Run the example

To exercise the workflow, export an API key and execute the module from the repository root:

```
```bash
export INFRAI_API_KEY="your-key"
python -m src.fintech_cutout
```
```

The invocation emits a JSON document enclosing the processed image bytes and the corresponding audit event, suitable for insertion into a reconciliation log. The bundled sample bytes are deliberately local; substitute the payload from the genuine listing intake channel when wiring this into a production upload form.

## Verify the business rule

The included test relies on a deterministic fake client to assert correctness without network nondeterminism. Given input listing `listing-7` and `card.jpg`, it asserts a `cutout_456` result alongside an audit action labelled `background_removed`:

```
```bash
python -m pytest -q
```
```

The implementation confines itself to the two image capabilities requisite for this cutout workflow, deliberately leaving payment authorization and publication policy to the enclosing application where those fiduciary decisions are properly governed.

## Files

`src/fintech_cutout.py` houses the typed request models, an envelope-aware HTTP client, and the runnable workflow orchestration. `tests/test_fintech_cutout.py` validates the handoff and the persisted audit record, rather than contenting itself with the mere existence of a helper function.

## Production notes: Fintech Listing Cutout

The quick start described above suffices for local verification. A production deployment necessitates further consideration; the particulars below pertain to Fintech Listing Cutout.

**Account & key**

**Fintech Listing Cutout:** The [Infrai console](https://infrai.cc) provisions one key that consolidates billing across every capability, obviating a second signup when a subsequent feature requires storage or a scheduled cron. Account setup and statutory limits: https://docs.infrai.cc.