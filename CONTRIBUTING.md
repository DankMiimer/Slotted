# Contributing

Original code and documentation contributions use the root MIT license.
Contribute only material you have permission to share, and identify third-party
material and its terms separately.

Model/texture contributions need creator, title, original source URL, license
URL/text, source hash and modification notes. Update `CREDITS.md`,
`release/model-licenses.json` and the shipped `MODEL_CREDITS.txt`. A purchased or
freely downloadable model is not automatically redistributable. Preserve NC and
ShareAlike conditions. Do not submit ROMs, BIOS, fixed game artwork, credentials
or local-only editorial models.

Preserve authored `scene-layouts`, history, originals, full-detail models and
alternative settings. Avoid rebuilding every model for a code-only change.

Describe the problem, behavior change and checks in pull requests. Report host
tests, device trials and installation separately. Retain normal frontend launch
validation and exactly one launch per press: first A inserts, a separate A
launches. Use existing snapshot/restore/audit tooling for device mutations and
preserve saves/settings.

Publication checks: `python -m unittest discover -s tests -p test_publication.py`.
See [development setup](docs/DEVELOPMENT.md) for broader checks and limitations.
