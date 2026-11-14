# AI Usage Note

## Tool used
Claude (claude.ai chat). No other AI tool was used. All my prompts are in `PROMPT_HISTORY.md`.

## Where AI accelerated my work
- Understanding the problem statement and splitting it into small steps.
- Drafting the data dictionary, `generate_data.py`, `validate_data.py`, `export_sql.py`, `verify_reproducibility.py`, the README and the assumptions file.

## Where I relied heavily on AI
- The code for the generator, the recall trace, the edge-case injection and the validator was written by Claude, one part at a time.
- The layout of the validation report and the recall metrics.

## What I personally did, reviewed and validated
- Set up the environment, the GitHub repository and the folders, and made all commits.
- Ran every part and compared the output with the expected row counts before moving on.
- Found and fixed my own mistakes: an unsaved file that stopped the edge cases from running, and an old README block left above the new one.
- Confirmed that `validate_data.py` passes all 75 integrity checks and finds every planted anomaly (146 planted, 146 matched, 0 missed, 0 false alarms).
- Confirmed that two runs with seed 20261022 give identical files (14 of 14).
- Checked that the 20 foreign-key violations in the SQL export are exactly the 20 planted MISSING_INPUT_LOT rows.

## Limits of my review
- I did not write the code line by line myself. I reviewed it by running it, reading the outputs and tracing the flow.
- I can explain the logic: master data first, raw lots, production by BOM, finished lots, shipments and deliveries, the downstream recall trace, edge-case injection after the clean data, then validation against a separate ground truth.
- Known limitations are in `docs/ASSUMPTIONS.md`.