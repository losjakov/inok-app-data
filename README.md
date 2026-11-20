# inok-app-data

A byte-exact mirror of the public app export of **inok.info** («Монастирський вісник України»), used by the InokApp mobile app
(Google Play / App Store, `info.inok.app`) only when inok.info does not answer (ruling A-144 of the InokApp project).

- `export/manifest.json` - the site's manifest, published byte for byte; `export/directory_v1.json.gz` - the directory it names
  (its sha256 and size are checked against the manifest before anything is published).
- `status.json` - when the site was last checked and the result.
- Served by GitHub Pages: `https://losjakov.github.io/inok-app-data/export/manifest.json`.
- Updated by `.github/workflows/mirror.yml` every 6 hours (`mirror.py`); an older export is never published, a failed fetch keeps the last good copy.

The data is the public directory of monasteries of the Ukrainian Orthodox Church published on https://inok.info .
Owner: Holy Dormition Kyiv-Pechersk Lavra (the site's owner and operator).
