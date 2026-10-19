# Consumer contract snapshots

`consumer-matrix.json` is the single registry for the Platform, World Intelligence, and TSIC consumer contracts. A pinned `pass` or `fail` entry must point to a full, lowercase 40-character commit SHA and a checked-in fixture whose embedded revision and status match. `not_evidenced` can retain an exact revision when the source contract is known but external conformance is not. Mutable refs such as `main`, branch names, tags, and abbreviated commits are rejected by validation.

The Platform adapter at `db8473b452701d9b3807797ab1bc178b58feb96d` lacks all six monitor tools required by this W15 API, so that consumer is a confirmed failure. World Intelligence schema `1.0.0` at `a564816faffa5be8e970eae5127f3a504d0a1729` is pinned and validates an actual TWI export payload, including rejection of unknown properties. TSIC requirements are pinned at `d30d5a6ec9a19c6de7d373cba578cbd9cdc26451`, but no external conformance result is available. These snapshots establish contract compatibility only; they do not establish consumer approval or deployment readiness.

To refresh a snapshot, obtain the exact consumer commit and the contract artifact reviewed by that repository's owner, add the fixture under the corresponding consumer directory, update revision and evidence reference, and run:

```bash
python scripts/validate_consumer_contracts.py --matrix contracts/consumer-matrix.json
pytest tests/test_consumer_contracts.py tests/test_platform_tool_catalog.py tests/test_world_intelligence_client.py -q
```

Record compatibility review and consumer approval as separate owned evidence. A valid matrix may contain failures and unevidenced consumers; neither means ecosystem approval has passed.
