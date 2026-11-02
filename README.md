# Aether Packs

Optional component packs for [Aether](https://github.com/Arthur-101/aether).

The base app ships with no inference engine, no voice data, and no speech
runtime. This repository publishes those pieces as GitHub Releases so the app
can stay small and the packs can be updated independently.

Pack payloads are **never committed to git**. `scripts/packs.py` writes a
deterministic archive, the workflow uploads it, and the app verifies its
SHA-256 before installing.

## Packs

| ID | Contents | Layout inside the archive |
| :--- | :--- | :--- |
| `engine-vulkan` | llama.cpp Vulkan runtime | `bin/llama-server.exe` + runtime DLLs |
| `engine-cpu` | llama.cpp CPU runtime | `bin/llama-server.exe` + runtime DLLs |
| `engine-cuda` | llama.cpp CUDA 12.4 runtime (not built yet) | `bin/llama-server.exe` + CUDA DLLs |
| `espeak-ng` | GPL-3.0 G2P tool and data | `espeak-ng.exe` + `espeak-ng-data/phontab` |
| `stt-phonon2` | Local speech runtime and model | `bin/stt-runtime/python.exe` + `models/phonon2/` |

A pack is extracted by the app into:

```text
%LOCALAPPDATA%\Aether\components\<id>\<version>\
```

so the archive root must contain the layout above directly, not an extra
top-level folder. The packaging script flattens a single top-level directory if
one is present.

## How a pack is built

`packs.json` records a `build` block per pack, so the source of every archive is
in version control next to its checksum:

```json
"build": { "type": "llama.cpp", "repo": "ggml-org/llama.cpp", "ref": "b12032", "backend": "vulkan" }
"build": { "type": "msi", "url": "https://.../espeak-ng.msi", "sha256": "..." }
"build": { "type": "manual" }
```

| Type | Meaning |
| :--- | :--- |
| `llama.cpp` | The workflow compiles that repository at `ref` for `backend`. |
| `msi` | The workflow downloads and unpacks the pinned MSI (espeak-ng). |
| `manual` | The workflow downloads a prebuilt zip from `source_url` (stt-phonon2). |
| `disabled` | Dispatch is refused with the recorded `reason`. |

### Engine build

The engine archives are llama.cpp with every x86 CPU backend variant, built by
clang-cl 20:

```bat
cmake -S llama.cpp -B build -G Ninja ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_C_COMPILER=clang-cl -DCMAKE_CXX_COMPILER=clang-cl ^
  -DBUILD_SHARED_LIBS=ON ^
  -DGGML_BACKEND_DL=ON -DGGML_CPU_ALL_VARIANTS=ON -DGGML_NATIVE=OFF ^
  -DGGML_RPC=ON -DGGML_OPENMP=ON -DGGML_OPENMP_FETCH=ON -DGGML_CCACHE=OFF ^
  -DGGML_VULKAN=ON ^
  -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF ^
  -DLLAMA_BUILD_SERVER=ON
cmake --build build --config Release --parallel
```

- `GGML_CPU_ALL_VARIANTS` + `GGML_BACKEND_DL` produce the 14
  `ggml-cpu-*.dll` variants; five of them (and therefore the `libomp` runtime)
  only exist for a non-MSVC compiler, which is why the workflow installs
  clang-cl 20 to match the published archives.
- `GGML_OPENMP_FETCH` downloads LLVM's `libomp.dll` (pinned to LLVM 20.1.8) and
  its licence; both land in `bin/`.
- `LLAMA_CONNECT` stays off. It downloads a prebuilt third-party binary at build
  time, resolves to "latest", and Aether never runs it.
- `bin/` is staged from `*.exe`, `*.dll`, and `LICENSE-*` only. The workflow
  adds `LICENSE-llama.cpp.txt` at the archive root.

## Publishing a pack

Run the **release-pack** workflow:

- `pack` — one of the IDs above.
- `version` — optional; defaults to `packs.json`.
- `source_url` — only for `stt-phonon2`.
- `dry_run` — build, package, and smoke-test, then upload the archive as a
  workflow artifact without creating a release or committing. Use it first for
  every new source pin.

The workflow packs the payload, smoke-tests the binaries, refuses an existing
tag, creates the release, and commits `packs.json`, `checksums.json`, and
`components_manifest.json`. It never overwrites published bytes.

### Building locally

Put the unpacked payload in `packs/<id>/` (ignored by git), then:

```bat
py -3.12 scripts\packs.py package --pack engine-vulkan
```

This writes `dist/<id>-<version>.zip`, its `.sha256`, updates
`checksums.json` and the real sizes in `packs.json`, and regenerates
`components_manifest.json`. Upload the archive and checksum to a new release:

```bat
gh release create engine-vulkan-v0.2.0 ^
  dist\engine-vulkan-0.2.0.zip ^
  dist\engine-vulkan-0.2.0.zip.sha256 ^
  --title "engine-vulkan-v0.2.0"
```

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
- Record each pack's licence in `PACK_LICENSES.md` before publishing it, and
  keep the licence files under `assets/` in step with what the archive ships.

## Development

```bat
py -3.12 scripts\packs.py plan --pack engine-vulkan
py -3.12 scripts\packs.py render
py -3.12 -m py_compile scripts\packs.py
```