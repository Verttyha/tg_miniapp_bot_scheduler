# Active Context

Current priorities:

- keep the repository minimal without losing production behavior
- maintain a clear server-first deployment path
- keep backend structure consistent with `core` and `domain`
- keep the frontend decomposed by responsibility instead of returning to single-file screens

Open follow-ups:

- decide whether frontend and backend lockfiles should be committed or regenerated only in CI
- if the UI expands further, consider extracting frontend copy/constants into a dedicated localization layer
- re-run the full backend pytest suite after recreating the Python virtual environment
