"""
Instructor script: download GEDI L2A (GEDI02_A.002) granules and cut them down
to a regional subset with only the datasets used in the course. You upload the
resulting files to a file share (e.g. Zenodo); students download them in the
notebook and clip them to the study area (data/aoi.geojson) themselves.

The output files keep the original GEDI HDF5 layout (METADATA group, BEAMxxxx
groups, geolocation/ and land_cover_data/ subgroups, all attributes), so the
student notebook reads them exactly like a full granule, only much smaller.

Run this ONCE on your own machine (needs an Earthdata login):

    pip install earthaccess h5py numpy
    python prep/prepare_subset.py                      # search + download + subset
    python prep/prepare_subset.py --granules f1.h5 f2.h5   # subset files you already have

Output goes to shared_data/ (upload these to the file share, do NOT commit them).
data/aoi.geojson (the students' clipping area) is written too and IS committed.
"""

import argparse
import json
from pathlib import Path

import h5py
import numpy as np

# --------------------------------------------------------------------------
# Settings: adjust to your study area / season
# --------------------------------------------------------------------------
# Region that is shipped to the students (west, south, east, north).
# Roughly Upper Austria south + northern Styria; students clip this to AOI_BBOX.
REGION_BBOX = (13.3, 47.3, 15.3, 48.2)
# Study area the students clip to: Kalkalpen National Park (approximate box).
# Written to data/aoi.geojson; replace that file with the real park boundary if you have it.
AOI_BBOX = (14.25, 47.68, 14.62, 47.88)
TEMPORAL = ("2022-05-01", "2023-09-30")   # leaf-on seasons recommended
MAX_GRANULES = 3                          # how many subset files to produce
MIN_SHOTS = 200                           # skip granules with fewer shots inside AOI_BBOX

# Datasets copied for every beam (paths relative to the BEAMxxxx group).
BEAM_DATASETS = [
    "shot_number", "beam", "channel", "delta_time",
    "lat_lowestmode", "lon_lowestmode",
    "elev_lowestmode", "elev_highestreturn", "rh",
    "quality_flag", "degrade_flag", "sensitivity", "surface_flag",
    "selected_algorithm", "num_detectedmodes", "solar_elevation",
    "digital_elevation_model", "digital_elevation_model_srtm",
    "land_cover_data/landsat_treecover", "land_cover_data/modis_treecover",
    "land_cover_data/pft_class", "land_cover_data/leaf_off_flag",
]
for a in range(1, 7):  # all six algorithm setting groups
    BEAM_DATASETS += [
        f"geolocation/rh_a{a}",
        f"geolocation/elev_lowestmode_a{a}",
        f"geolocation/elev_highestreturn_a{a}",
        f"geolocation/lat_lowestmode_a{a}",
        f"geolocation/lon_lowestmode_a{a}",
        f"geolocation/sensitivity_a{a}",
        f"geolocation/quality_flag_a{a}",
    ]


def copy_attrs(src, dst):
    for k, v in src.attrs.items():
        try:
            dst.attrs[k] = v
        except OSError as err:  # e.g. attribute too large for the object header
            print(f"  warning: skipped attribute '{k}' on {src.name}: {err}")


def subset_granule(src_path, out_dir, bbox=REGION_BBOX, suffix="region"):
    """Write a spatial subset of one GEDI L2A granule. Returns (path, n_shots) or (None, 0)."""
    w, s, e, n = bbox
    aw, as_, ae, an = AOI_BBOX
    src_path = Path(src_path)
    n_aoi = 0
    stem = src_path.stem.removeprefix("processed_")   # prefix added by the LP DAAC GEDI Subsetter
    out_path = Path(out_dir) / f"{stem}_{suffix}.h5"
    total = 0
    with h5py.File(src_path, "r") as src:
        beams = sorted(k for k in src.keys() if k.startswith("BEAM"))
        masks = {}
        for b in beams:
            if f"{b}/lat_lowestmode" not in src or f"{b}/lon_lowestmode" not in src:
                continue  # empty beam group (e.g. no shots in the subsetter's area)
            lat = src[f"{b}/lat_lowestmode"][()]
            lon = src[f"{b}/lon_lowestmode"][()]
            m = (lon >= w) & (lon <= e) & (lat >= s) & (lat <= n)
            n_aoi += int(((lon >= aw) & (lon <= ae) & (lat >= as_) & (lat <= an)).sum())
            if m.any():
                masks[b] = m
                total += int(m.sum())
        print(f"  {src_path.name}: {n_aoi} shots in study area, {total} in region")
        if n_aoi < MIN_SHOTS:
            return None, total

        with h5py.File(out_path, "w", libver="latest") as dst:   # allows large attributes
            copy_attrs(src, dst)
            if "METADATA" in src:
                src.copy("METADATA", dst)
            dst.attrs["subset_note"] = (
                f"Spatial subset of {src_path.name} to bbox {bbox} (W,S,E,N) "
                "for teaching purposes. Original data: GEDI02_A.002, "
                "doi:10.5067/GEDI/GEDI02_A.002"
            )
            for b in masks:  # only beams with shots in the region
                g_out = dst.create_group(b)
                copy_attrs(src[b], g_out)
                m = masks.get(b)
                for path in BEAM_DATASETS:
                    full = f"{b}/{path}"
                    if full not in src:
                        continue
                    ds = src[full]
                    data = ds[()]
                    if m is not None and data.ndim >= 1 and data.shape[0] == m.size:
                        data = data[m]
                    elif m is None and data.ndim >= 1:
                        data = data[:0]  # beam has no shots in AOI: keep empty dataset
                    parent = g_out.require_group(path.rsplit("/", 1)[0]) if "/" in path else g_out
                    if "/" in path:
                        copy_attrs(src[f"{b}/{path.rsplit('/', 1)[0]}"], parent)
                    kw = dict(compression="gzip", compression_opts=4) if data.size > 0 and data.ndim >= 1 else {}
                    out = parent.create_dataset(path.rsplit("/", 1)[-1], data=data, **kw)
                    copy_attrs(ds, out)
    return out_path, total


def write_aoi(out_dir, bbox=AOI_BBOX):
    w, s, e, n = bbox
    gj = {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Area of interest"},
            "geometry": {"type": "Polygon",
                         "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]]},
        }],
    }
    (Path(out_dir) / "aoi.geojson").write_text(json.dumps(gj))


def download(raw_dir):
    import earthaccess
    earthaccess.login()  # prompts for Earthdata credentials (or uses ~/.netrc)
    results = earthaccess.search_data(
        short_name="GEDI02_A", version="002",
        bounding_box=AOI_BBOX, temporal=TEMPORAL,   # only granules that cross the park
    )
    print(f"Found {len(results)} granules intersecting the AOI.")
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--granules", nargs="*", help="already downloaded GEDI02_A .h5 files")
    ap.add_argument("--raw-dir", default="raw", help="where full granules are downloaded")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument("--out-dir", default=str(root / "shared_data"), help="where subsets are written")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not (root / "data" / "aoi.geojson").exists():
        write_aoi(root / "data")

    written = []
    if args.granules:
        for p in args.granules:
            path, nshots = subset_granule(p, out_dir)
            print(f"{Path(p).name}: {nshots} shots in region" + (f" -> {path.name}" if path else " (skipped)"))
            if path:
                written.append(path)
    else:
        import earthaccess
        results = download(args.raw_dir)
        Path(args.raw_dir).mkdir(exist_ok=True)
        for r in results:  # download one at a time, keep only useful granules
            if len(written) >= MAX_GRANULES:
                break
            f = earthaccess.download([r], local_path=args.raw_dir)[0]
            path, nshots = subset_granule(f, out_dir)
            print(f"{Path(f).name}: {nshots} shots in region" + (f" -> {path.name}" if path else " (skipped)"))
            if path:
                written.append(path)

    for p in written:
        print(f"{p.name}: {p.stat().st_size / 1e6:.1f} MB")
    print(f"Done. Upload the files in {out_dir} to your file share and put their "
          "download links into DATA_URLS in the notebook.")


if __name__ == "__main__":
    main()
