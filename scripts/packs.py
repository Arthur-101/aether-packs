"""Package Aether component packs and regenerate the download manifest.

Stdlib only. The archive is written deterministically (sorted entries, fixed
timestamps) so repackaging the same payload produces the same SHA-256.

Usage::

    py -3.12 scripts/packs.py fetch --pack engine-vulkan --url https://.../pack.zip
    py -3.12 scripts/packs.py package --pack engine-vulkan --version 0.1.0
    py -3.12 scripts/packs.py render
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "packs.json"
CHECKSUMS_PATH = ROOT / "checksums.json"
MANIFEST_PATH = ROOT / "components_manifest.json"
STAGING_DIR = ROOT / "packs"
DIST_DIR = ROOT / "dist"
CHUNK = 1024 * 1024


def _load_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default
    return data if isinstance(data, dict) else default


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _catalog() -> Dict[str, Any]:
    data = _load_json(CATALOG_PATH, {"schema": 1, "components": []})
    if not isinstance(data.get("components"), list):
        raise SystemExit(f"{CATALOG_PATH} has no components list")
    return data


def _pack(pack_id: str) -> Dict[str, Any]:
    for entry in _catalog()["components"]:
        if entry.get("id") == pack_id:
            return entry
    known = ", ".join(entry.get("id", "?") for entry in _catalog()["components"])
    raise SystemExit(f"Unknown pack {pack_id!r}. Known: {known}")


def _repo() -> str:
    repo = str(_catalog().get("repo") or "").strip()
    if not repo:
        raise SystemExit("packs.json must set 'repo' (owner/name)")
    return repo


def _tag(pack_id: str, version: str) -> str:
    return f"{pack_id}-v{version}"


def _asset(pack_id: str, version: str) -> str:
    return f"{pack_id}-{version}.zip"


def _url(pack_id: str, version: str) -> str:
    return (
        f"https://github.com/{_repo()}/releases/download/"
        f"{_tag(pack_id, version)}/{_asset(pack_id, version)}"
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_manifest() -> Path:
    """Regenerates components_manifest.json from packs.json + checksums.json."""
    checks = _load_json(CHECKSUMS_PATH, {"schema": 1, "components": {}})
    published = checks.get("components")
    published = published if isinstance(published, dict) else {}

    components: List[Dict[str, Any]] = []
    for entry in _catalog()["components"]:
        pack_id = str(entry["id"])
        record = published.get(pack_id)
        record = record if isinstance(record, dict) else {}
        version = str(record.get("version") or entry.get("version") or "")
        components.append(
            {
                "id": pack_id,
                "name": entry.get("name") or pack_id,
                "kind": entry.get("kind") or "component",
                "backend": entry.get("backend") or "",
                "version": version,
                "url": _url(pack_id, version) if version else "",
                "sha256": str(record.get("sha256") or "").lower(),
                "size": int(record.get("size") or entry.get("size") or 0),
                "installed_size": int(entry.get("installed_size") or 0),
                "min_app_version": entry.get("min_app_version") or "0.1.0",
                "recommended": bool(entry.get("recommended")),
                "description": entry.get("description") or "",
            }
        )

    manifest = {
        "schema": 1,
        "base_url": "",
        "_note": (
            "Optional component packs. A pack is offered for download only once "
            "it has a 64-character sha256; until then it reports state "
            "'unavailable'. URLs point at the aether-packs releases; keep version "
            "in step with the published archive."
        ),
        "components": components,
    }
    _write_json(MANIFEST_PATH, manifest)
    return MANIFEST_PATH


def _flatten_single_root(target: Path) -> None:
    entries = list(target.iterdir())
    if len(entries) != 1 or not entries[0].is_dir():
        return
    inner = entries[0]
    for child in inner.iterdir():
        shutil.move(str(child), str(target / child.name))
    inner.rmdir()


def fetch(pack_id: str, url: str) -> Path:
    """Downloads a source zip and extracts it into packs/<id>."""
    _pack(pack_id)
    target = STAGING_DIR / pack_id
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "source.zip"
        request = urllib.request.Request(url, headers={"User-Agent": "aether-packs"})
        with urllib.request.urlopen(request, timeout=120) as response:
            with archive.open("wb") as handle:
                shutil.copyfileobj(response, handle, CHUNK)
        if not zipfile.is_zipfile(archive):
            raise SystemExit(f"{url} is not a zip archive")

        root = target.resolve()
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                destination = (target / member.filename).resolve()
                if destination != root and root not in destination.parents:
                    raise SystemExit(f"Unsafe path in archive: {member.filename!r}")
            bundle.extractall(target)

    _flatten_single_root(target)
    return target


def _zip_tree(source: Path, destination: Path) -> None:
    files = sorted(path for path in source.rglob("*") if path.is_file())
    if not files:
        raise SystemExit(f"{source} contains no files")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as bundle:
        for path in files:
            name = path.relative_to(source).as_posix()
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            with path.open("rb") as read, bundle.open(info, "w") as write:
                shutil.copyfileobj(read, write, CHUNK)


def package(pack_id: str, version: str = "", source: Path | None = None) -> Dict[str, Any]:
    entry = _pack(pack_id)
    version = version or str(entry.get("version") or "")
    if not version:
        raise SystemExit("No version supplied and packs.json has none")

    payload = source or (STAGING_DIR / pack_id)
    if not payload.is_dir():
        raise SystemExit(f"Payload directory not found: {payload}")
    missing = [
        item for item in entry.get("required") or [] if not (payload / item).exists()
    ]
    if missing:
        raise SystemExit(
            f"{pack_id} is missing required path(s): {', '.join(missing)}"
        )

    name = _asset(pack_id, version)
    archive = DIST_DIR / name
    _zip_tree(payload, archive)
    digest = _sha256(archive)
    size = archive.stat().st_size
    (DIST_DIR / f"{name}.sha256").write_text(
        f"{digest}  {name}\n", encoding="utf-8"
    )

    checks = _load_json(CHECKSUMS_PATH, {"schema": 1, "components": {}})
    components = checks.get("components")
    components = components if isinstance(components, dict) else {}
    components[pack_id] = {
        "version": version,
        "sha256": digest,
        "size": size,
    }
    checks["schema"] = 1
    checks["components"] = components
    _write_json(CHECKSUMS_PATH, checks)
    render_manifest()

    release = {
        "pack": pack_id,
        "version": version,
        "tag": _tag(pack_id, version),
        "asset": name,
        "sha256": digest,
        "size": size,
        "url": _url(pack_id, version),
    }
    _write_json(DIST_DIR / "release.json", release)
    print(json.dumps(release, indent=2))
    return release


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    fetch_parser = sub.add_parser("fetch", help="download and extract a source zip")
    fetch_parser.add_argument("--pack", required=True)
    fetch_parser.add_argument("--url", required=True)

    package_parser = sub.add_parser("package", help="zip a payload and update the manifest")
    package_parser.add_argument("--pack", required=True)
    package_parser.add_argument("--version", default="")
    package_parser.add_argument("--source", type=Path, default=None)

    sub.add_parser("render", help="regenerate components_manifest.json")

    args = parser.parse_args(argv)
    if args.command == "fetch":
        target = fetch(args.pack, args.url)
        print(f"Extracted {args.pack} into {target}")
    elif args.command == "package":
        package(args.pack, args.version, args.source)
    else:
        print(f"Wrote {render_manifest()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())