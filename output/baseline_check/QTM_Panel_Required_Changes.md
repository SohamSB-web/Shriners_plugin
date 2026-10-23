# QTM Panel Required Changes

## Reported Issues

- Most measurement fields in the QTM panel reset to zero after leaving the field.
- The QTM panel currently allows unit changes, but the workflow should be locked to meters to avoid mismatch with `settings.paf`.

## Required Changes

1. Fix the measurement field persistence bug.
   - Ensure values remain after `Enter`, `Tab`, and focus changes.
   - Review the QTM panel load/save/bind logic for any fields that are being overwritten or reinitialized.
   - Preserve entered values for all measurement fields, not just `Body Mass` and `ASIS Trochanter Distance`.

2. Lock QTM panel measurement units to meters.
   - Remove the unit dropdown from the QTM panel.
   - Display meter-based units only in the UI.
   - Prevent users from switching to `mm` or `cm` in the panel.

3. Keep unit handling consistent with the model inputs.
   - If downstream code still needs `mm`, convert from meters in the processing layer instead of exposing unit choices in the UI.
   - Ensure the QTM panel and `settings.paf` use the same expected units.

4. Update persisted settings and defaults.
   - Verify the saved values written to `settings.paf` match the new meter-only workflow.
   - Make sure the settings file does not reintroduce editable unit selection.

## Acceptance Criteria

- All measurement fields retain their values after leaving the field.
- The QTM panel no longer shows a unit dropdown for measurements.
- Users can only enter measurements in meters in the QTM panel.
- The processing pipeline still receives values in the format it expects.
- The UI and `settings.paf` stay aligned.

## Suggested Verification

- Open the QTM panel and enter values in each measurement field.
- Press `Enter`, `Tab`, and click into another field to confirm values remain.
- Confirm the unit selector is gone.
- Run a representative analysis and verify the saved settings and downstream results still work correctly.
