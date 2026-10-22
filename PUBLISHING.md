# Preparing a GitHub upload

Use a clean public export, not this development checkout's Git history or a ZIP
of its working folder. The latter can include private snapshots, copyrighted
game art and local-only editorial models. Historical branches/recovery records
stay in the development repository.

```sh
python -m unittest discover -s tests -p test_publication.py
python -m tools.publication.export --output build/github-upload
python -m tools.publication.export --verify build/github-upload
```

The exporter refuses an existing output directory, copies only exact paths from
`release/public-files.txt` plus the hash-pinned build inputs in
`release/publication.json`, and writes `PUBLICATION_MANIFEST.json`. No source
file, Git index/ref, model selection or device is changed. Each exported file has
a SHA-256; the sibling audit report is local, not part of the upload. The audit
checks common credential/private-target patterns, forbidden file categories,
asset hashes and GitHub's 100 MiB per-file ceiling. It is a bounded check, not a
guarantee about every possible secret or third-party right.

Exported code/document text follows Git's checkout line endings (LF, CRLF for
PowerShell). Licensed asset families, package metadata and authored scene JSON
are preserved byte for byte using explicit `-text` attributes. This keeps the
asset pins and snapshot manifest valid after cloning on Windows or Linux.

Review `LICENSE_SCOPE.md`, `CREDITS.md`, `release/model-licenses.json` and the
manifest before uploading. Some selected assets are NonCommercial/ShareAlike.
Do not describe the full asset bundle as unrestricted or all-MIT. The local
NeilVFX SP remains selected locally when present but is absent from this export.
No alternate model is silently substituted in the working project or device.

The public asset pack supplies prepared room assets that otherwise live only
under ignored `build/`, plus source furniture GLBs. Full-detail masters and
alternative models already under the shared theme are retained. Original source
archives and ignored research stay local; creator URLs, source hashes and
modification records remain in the export. Reuse of historical original importer
inputs may require obtaining the original files from their creators.

## First upload

Create an **empty** repository on your GitHub account, then run the following
inside the exported directory, replacing the remote with that repository's URL:

```sh
git init -b main
git add --pathspec-from-file=UPLOAD_PATHS.txt
git diff --cached --stat
git commit -m "Publish Slotted source and licensed assets"
git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_REPOSITORY.git
git push -u origin main
```

`UPLOAD_PATHS.txt` is the exact exported-file list, including itself and the
manifest. This is a new publication repository; it does not discard or rewrite
the development repository's history. No repository is created and nothing is
pushed by the export command.

Use Git for this upload. Some model sources exceed the browser uploader's
25 MiB limit. Files above 50 MiB produce a Git warning; all exported files must
remain below 100 MiB. Larger future originals belong in Git LFS or separately
licensed release assets. See [GitHub's documented size limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).

## Updating the allowlist

Review new files and their licenses before adding their exact relative paths to
`release/public-files.txt`. Do not replace it with a broad directory glob.
Build-only assets additionally need a destination, restore path and expected
SHA-256 in `release/publication.json`. A changed protected asset hash requires
reviewing the new source and updating its credits, not bypassing verification.
User-imported room textures need their own provenance before inclusion.

Public-only artwork corrections are pinned separately in
`release/asset-derivatives.json`. The exporter substitutes the reviewed files
from `assets/publication-derivatives/` without changing development originals;
those staging copies are not independently added to the upload list. A public
clone already has the corrected destinations and can re-export without private
inputs. Asset restore hashes and byte counts are updated in the exported
configuration. Changed originals or derivative files fail validation.
See [public asset derivatives](docs/PUBLIC_ASSET_REMEDIATION.md) for scope,
source rebuild protection and the retained third-party license conditions.

Exports made from a public clone use its `assets/` copies when the original
build input is absent. Verification rejects changed, missing or extra files,
including symlinks. Initialize Git only after verification. Local `.git`,
`__pycache__`, `.venv`, `build/` and `research/` are ignored by later verification;
they are never publication inputs except for the explicitly pinned asset copies.
