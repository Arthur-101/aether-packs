# Pack licences

The scripts, catalog, and generated manifest in this repository are Apache-2.0.
Each downloadable pack is a separate work and keeps its own licence. This file
records the exact terms so a published archive is always accounted for.

| Pack | Licence | Source / notice |
| :--- | :--- | :--- |
| `engine-vulkan` | MIT (llama.cpp / ggml) | https://github.com/ggml-org/llama.cpp |
| `engine-cpu` | MIT (llama.cpp / ggml) | https://github.com/ggml-org/llama.cpp |
| `engine-cuda` | MIT (llama.cpp / ggml) + NVIDIA CUDA redistributable | Include the NVIDIA notice shipped with the CUDA runtime. |
| `espeak-ng` | **GPL-3.0-or-later** | https://github.com/espeak-ng/espeak-ng — include the licence text and a written offer for the corresponding source. |
| `stt-phonon2` | Runtime **Apache-2.0**; model weights **CC-BY-4.0** | See *stt-phonon2* below. |

## engine-* — Prism fork

The Vulkan/CPU/CUDA builds are llama.cpp (MIT) with the **Prism** fork used for
Ternary Bonsai. Record the fork's licence and commit hash in the pack release
notes before publishing, alongside the upstream MIT text. `engine-cuda` also
redistributes NVIDIA CUDA runtime libraries under the NVIDIA CUDA Software
License Agreement; ship that notice with the pack.

## espeak-ng

GPL-3.0-or-later. It is never linked into the app: the backend spawns
`espeak-ng.exe` as an external process, so the base application stays
Apache-2.0. Every release for this pack must include:

- the full GPL-3.0 text, and
- a written offer to provide the corresponding source, or a link to the exact
  espeak-ng source revision the binary was built from.

## stt-phonon2

This pack bundles two separately licensed things.

### Runtime — `fermion-research` (Apache-2.0)

The `fermion`/`phonon` speech engine. Package: `fermion-research==0.2.15`
(https://pypi.org/project/fermion-research/). Declared licence expression:
**Apache-2.0**. Ship its `LICENSE` with the pack.

Its isolated virtual environment also installs transitive dependencies
(PyTorch — BSD-3-Clause, Transformers — Apache-2.0, NumPy, etc.). Their licence
files are already reproduced in the app's `THIRD_PARTY_LICENSES.txt`; when the
pack is built, keep the bundled metadata (`*.dist-info`) so the notices travel
with the archive.

### Models — Phonon-2 weights (CC-BY-4.0)

`FermionResearch/Phonon-2` is released under **CC-BY-4.0**, which permits
redistribution and adaptation for any purpose with **attribution**. Phonon-2 is
built on NVIDIA's **Parakeet TDT 0.6B v3**
(https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3), also **CC-BY-4.0**.

Every release that ships these weights must carry an attribution notice naming
both upstreams, for example:

> This pack includes the Phonon-2 speech model by Fermion Research
> (https://huggingface.co/FermionResearch/Phonon-2), licensed CC-BY-4.0, built
> on NVIDIA Parakeet TDT 0.6B v3
> (https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3), licensed CC-BY-4.0.
> No modifications were made to the model weights. The full CC-BY-4.0 text is
> included as `LICENSE-CC-BY-4.0.txt`.

Include the full CC-BY-4.0 text in the archive, keep the upstream model cards,
and link to the exact model revisions in the release notes. CC-BY-4.0 is not a
copyleft licence and does not affect the Apache-2.0 app.
