# Aether Packs

Optional component packs for [Aether](https://github.com/Arthur-101/aether).

The base app ships with no inference engine, no voice data, and no speech
runtime. This repository publishes those pieces as GitHub Releases so the app
can stay small and the packs can be updated independently.

Pack payloads are **never committed to git**. They are built elsewhere, packaged
by `scripts/packs.py`, and uploaded as release assets under 2 GiB each.

## Packs

| ID | Contents | Layout inside the archive |
| :--- | :--- | :--- |
| `engine-vulkan` | llama.cpp Vulkan runtime | `bin/llama-server.exe` + runtime DLLs |
| `engine-cpu` | llama.cpp CPU runtime | `bin/llama-server.exe` + runtime DLLs |
| `engine-cuda` | llama.cpp CUDA 12.4 runtime | `bin/llama-server.exe` + CUDA DLLs |
| `espeak-ng` | GPL-3.0 G2P tool and data | `espeak-ng.exe` + `espeak-ng-data/phontab` |
| `stt-phonon2` | Local speech runtime and model | `bin/stt-runtime/Scripts/python.exe` |

A pack is extracted by the app into:

```text
%LOCALAPPDATA%\Aether\components\<id>\<version>\
```

so the archive root must contain the layout above directly, not an extra
top-level folder. The packaging script flattens a single top-level directory if
one is present.

## Publishing a pack

### Locally

1. Put the unpacked payload in `packs/<id>/` (ignored by git), or point
   `--source` at it.
2. Bump `version` in `packs.json`.
3. Run:

```bat
py -3.12 scripts\packs.py package --pack engine-vulkan
```

This writes `dist/<id>-<version>.zip`, its `.sha256`, updates
`checksums.json`, and regenerates `components_manifest.json`.

4. Upload the archive and checksum to a new release:

```bat
gh release create engine-vulkan-v0.1.0 ^
  dist\engine-vulkan-0.1.0.zip ^
  dist\engine-vulkan-0.1.0.zip.sha256 ^
  --title "Engine - Vulkan 0.1.0"
```

### GitHub Actions

Run the **release-pack** workflow with:

- `pack` — one of the IDs above.
- `version` — optional; defaults to `packs.json`.
- `source_url` — an HTTPS URL to the built zip.

The workflow downloads the source, repacks it deterministically, uploads the
new release, updates `checksums.json` + `components_manifest.json`, and commits
the manifest. It never overwrites an existing tag.

## Manifest

`components_manifest.json` is generated from `packs.json` plus
`checksums.json`. The app only offers a pack for download when its `sha256` is a
64-character value. Until then the pack is listed as `unavailable`.

After publishing, copy the generated manifest into the app repository as
`aether/components_manifest.json` for the next app release. A future change can
fetch this file at runtime instead.

Release URL pattern:

```text
https://github.com/Arthur-101/aether-packs/releases/download/<id>-v<version>/<id>-<version>.zip
```

## Rules

- Never commit archives; use Releases.
- Never replace an asset under an existing tag. Bump the version and publish a
  new tag so a manifest checksum always describes immutable bytes.
- Keep every asset below GitHub's 2 GiB per-file limit. If a pack outgrows it,
  move that pack to object storage (Cloudflare R2) or add multi-part support.
- The app verifies SHA-256 after download; the manifest is the trust anchor.
  Treat changes to `checksums.json` as security-sensitive.
- Record each pack's licence in `PACK_LICENSES.md` before publishing it.

## Development

```bat
py -3.12 scripts\packs.py render
py -3.12 -m py_compile scripts\packs.py
```