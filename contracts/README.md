# Consumer contract snapshots

`consumer-matrix.json` is the single registry for the Platform, World Intelligence, and TSIC consumer contracts. A `pass` entry must point to a full, lowercase 40-character commit SHA and a checked-in fixture whose embedded revision matches. Mutable refs such as `main`, branch names, tags, and abbreviated commits are rejected by validation.

The current external repository history in TWI documentation records merge commits but does not provide a verified immutable consumer checkout and accepted contract snapshot for this branch. Entries therefore remain `not_evidenced`; the fixtures explicitly record why. Do not convert an entry to `pass` based on a TWI-side manifest or workflow definition.

To refresh a snapshot, obtain the exact consumer commit and the contract artifact reviewed by that repository's owner, add the fixture under the corresponding consumer directory, update revision and evidence reference, and run:

```bash
python scripts/validate_consumer_contracts.py --matrix contracts/consumer-matrix.json
pytest tests/test_consumer_contracts.py tests/test_platform_tool_catalog.py tests/test_world_intelligence_client.py -q
```

Record compatibility review and consumer approval as separate owned evidence. A valid matrix can still contain `not_evidenced` consumers and does not mean ecosystem approval has passed.
