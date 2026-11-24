# GEDI L2A Introduction

A hands-on introduction to the GEDI Level 2A Elevation and Height Metrics product
([GEDI02_A.002](https://doi.org/10.5067/GEDI/GEDI02_A.002)) with Python.
It runs entirely in the browser, with no installation and no account.

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/GITHUB_USER/gedi-l2a-intro/HEAD?labpath=notebooks%2FGEDI_L2A_Intro.ipynb)

## For students

1. Click the **launch binder** button above.
2. Wait until JupyterLab opens. This usually takes under a minute, sometimes a few.
3. Open `notebooks/GEDI_L2A_Intro.ipynb` (it should open automatically) and run the cells
   one by one with `Shift + Enter`. The first cells download the data.

Notes:
- The session is **temporary**. It stops after ~10 minutes of inactivity, and changes are not saved.
  Use *File → Download* to keep your notebook, and right-click → *Download* on files in `output/`.
- If Binder does not start, reload the page or try again a minute later.

## Contents

| Path | What |
|---|---|
| `notebooks/GEDI_L2A_Intro.ipynb` | student notebook (downloads data, clips to the study area, analysis) |
| `data/aoi.geojson` | study area the students clip to (Kalkalpen National Park, approximate box) |
| `prep/prepare_subset.py` | instructor script that makes the regional data files |
| `environment.yml` | software environment used by Binder |

## For instructors: preparing the data

The GEDI files are **not** stored in this repository. They live on a file share, and the
notebook downloads them.

1. Collect the GEDI L2A `.h5` files for the study area (original GEDI structure, e.g. as downloaded
   from NASA). Optionally slim them with `prep/prepare_subset.py --granules <files>`, which keeps
   only the datasets the course uses and a regional cut (see the settings at the top of the script).
2. Upload them to a file share that gives **direct download links without login**, either as
   single `.h5` files or as one `.zip`. The notebook unpacks zips automatically. Options:
   [Zenodo](https://zenodo.org) (link format `https://zenodo.org/records/<id>/files/<name>?download=1`)
   or a public Nextcloud link (append `/download` to the share link).
3. Put the links into `DATA_URLS` in the first data cell of the notebook.
4. Optional: replace `data/aoi.geojson` with the real national park boundary (EPSG:4326).
5. Replace `GITHUB_USER` in the Binder badge above, push to a **public** GitHub repo,
   and click the badge once before class to build the image (5–10 min the first time).

## Credits and license

Adapted from the LP DAAC tutorial *Getting Started with GEDI L2A Version 2 Data in Python*
([nasa/GEDI-Data-Resources](https://github.com/nasa/GEDI-Data-Resources)), Apache License 2.0.
See [`NOTICE`](NOTICE) for details of changes and the data citation, and [`LICENSE`](LICENSE) for the license text.
