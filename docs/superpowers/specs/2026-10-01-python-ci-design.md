# Design: GitHub Actions CI for slideio-python

Date: 2026-10-01

## Goal

Give this repository the two CI halves the C++ repository already has, adapted to
a Python wheel project:

1. A **per-commit gate** (`build-validation.yml`) that builds the C++ library, a
   wheel and runs `tests/` on all three shipped platforms for every push and pull
   request against `main`.
2. A **tag-driven release** (`release.yml`) that checks the tag against
   `projectVersion`, builds the full wheel set for every platform, and attaches
   the wheels to a draft GitHub Release.

PyPI upload stays manual. Nothing in this design uploads to an index.

## Where the two repositories stand

`../slideio/.github/workflows/` has `build-validation.yml` (push/PR gate,
concurrency with `cancel-in-progress`, Linux/macOS/Windows/manylinux builds plus a
ThreadSanitizer job), a tag-driven `release.yml` (version check, dynamically
assembled platform matrix, `fail-fast: false`, consumer smoke tests, artifacts with
`if-no-files-found: error`, draft Release gated so a manual run cannot publish),
and a manual Docker image workflow.

`.github/workflows/` here has three `workflow_dispatch`-only wheel workflows and
nothing else. Concretely missing or wrong:

- **Nothing runs on push or pull request.** Every check is a manual button press.
- **No concurrency control**, so two pushes to the same branch both build.
- **No tag trigger, no version check, no Release publishing.** `v2.7.0` is the
  only tag in the repository and the wheels it produced were uploaded by hand.
- **Two of three `upload-artifact` steps have no `name:`**
  (`macos-wheels.yml:102`, `windows-wheels.yml:90`), so both default to
  `artifact`; none sets `if-no-files-found: error`, so an empty upload is green.
- **No way to build every platform in one run**; the three files duplicate ~80% of
  their steps with no shared entry point.

The three workflows themselves are healthy — the last four dispatches of each were
green (2026-09-30), at 14–40 min Linux, 20–35 min Windows, 13–27 min macOS arm64
and up to 1h12m for the second macOS leg. This design does not rewrite what works;
it adds the two missing triggers and makes the existing files callable.

## Decisions

| Decision | Taken | Alternative, and why not |
|---|---|---|
| Gate coverage | 3 platforms (manylinux, macOS arm64, Windows), **one** Python (3.12) | The full 3.9–3.14 loop is ~6x the cost per push; a plain `ubuntu-latest` job as `../slideio` has adds a toolchain this project never ships |
| Release shape | `release.yml` **orchestrates** the three wheel workflows via `workflow_call` | A single matrix job as in `../slideio` needs heavy `if: runner.os == ...` branching, because container/conda/pwsh share almost no steps; duplicating the steps into `release.yml` means every platform fix lands twice |
| Patch version | The **tag** supplies it: `v2.10.3` → `CI_PIPELINE_IID=3` | `github.run_number` makes a re-run produce a different version for the same tag; moving the full version into `CMakeLists.txt` costs a commit per patch release and churns `setup.py` |
| macOS at release | **Both** `macos-14` (arm64, 3.9–3.14) and `macos-15-intel` (x86_64, 3.9–3.13) | arm64 only leaves Intel users without wheels; `continue-on-error` on the Intel leg lets a release ship silently incomplete |
| PyPI | Out of scope, upload stays manual | Bundling index credentials into this change widens the blast radius of a first CI run; §6 is written so a `pypa/gh-action-pypi-publish` job can be added to `publish` later without touching anything else |

## 1. `build-validation.yml`

```yaml
on:
  push:         { branches: [main] }
  pull_request: { branches: [main] }
  workflow_dispatch:
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

Three independent jobs under `fail-fast: false`, so one platform's failure does not
hide whether the other two build. Each performs the same five steps:

1. `actions/checkout@v4` with `submodules: recursive` — `recursive`, not `true`:
   the C++ library is `extern/slideio` and carries four submodules of its own.
2. Conan cache, keyed on the submodule commit (see §4).
3. `python build-slideio.py -c release`.
4. `python -m build --wheel` — one wheel, not the platform's wheel script.
   `--wheel` and not a bare `python -m build`: the sdist ships no `extern/`, so a
   wheel built from an unpacked sdist finds no install prefix and fails.
5. Install that wheel into a clean interpreter, `cd` outside the checkout, and
   `pytest tests/`.

Step 5 is gated on `vars.SLIDEIO_IMAGES_PATH != ''`, exactly as the wheel
workflows gate their own test step: without the corpus there is nothing to read.
`SLIDEIO_SKIP_MISSING_IMAGES` is left unset, as `CLAUDE.md` requires — in CI a
missing image must fail the run rather than quietly skip the test that needed it.
The `cd` matters for the same reason `CLAUDE.md` records: the repository root holds
a `slideio/` package directory, so `import slideio` from inside the checkout
resolves to the source tree and silently tests whatever the last build left there.

"A clean interpreter" means a fresh `venv` created from the job's own Python —
`/opt/python/cp312-cp312/bin/python` inside the container, the `setup-python` 3.12
elsewhere — into which `pytest`, `pillow` and `numpy` are installed along with the
built wheel via `pip install --no-index --find-links <dist>`, exactly as the three
wheel workflows' existing test steps do it. Pillow is required, not optional:
`tests/test_color.py` round-trips the raw ICC bytes through `PIL.ImageCms`.

### Per-platform specifics

**manylinux.** `container: booritas/slideio-manylinux_2_28_x86_64:2.10.0` with
`/opt/python/cp312-cp312/bin/python`, following `linux-wheels.yml:13-17` rather
than `../slideio`'s `docker run`. The container form is already green in this
repository, and unlike the C++ repo this job has no corpus-free C++ suite that
would need a shell inside the image. After the build it runs
`auditwheel repair -L /core/libs` on the single wheel and installs the repaired
one: that costs seconds, and auditwheel rejecting a wheel is a real failure mode
worth catching on a pull request rather than at release.

**macOS.** `macos-14`, `actions/setup-python@v5` at 3.12,
`pip install conan distro build`, and the `jwlawson/actions-setup-cmake@v2` pin at
`3.31.9` that `macos-wheels.yml` already carries. arm64 only; the Intel leg is
release-only. This job does not use conda — `build-wheels-macos.sh` needs it to
create one environment per Python version, and the gate builds exactly one.

**Windows.** `windows-2022`, `setup-python` 3.12, `conan distro build`, then after
`python -m build --wheel` it dot-sources `lib.ps1` and calls `Repair-Naming`
(`lib.ps1:69`). This is load-bearing, not tidiness: `Repair-Wheel` (`lib.ps1:47`)
renames `slideiopybind*.pyd` inside the wheel to the name the package imports, so
an unrepaired Windows wheel does not import. A gate that skipped it would be
testing an artifact that never ships. `Repair-Naming` iterates `.\dist\*.whl` and
is therefore safe to call with a single wheel present.

### Expected cost

The C++ library build dominates and `build-slideio.py` runs once either way, so
one wheel instead of five or six should put each job near 15–25 min against the
14–40 min the full wheel workflows take. The three run in parallel. This is an
estimate from the existing run history, to be replaced with measured numbers once
the gate has run.

## 2. `release.yml`

```yaml
on:
  push: { tags: ['v*'] }
  workflow_dispatch:
    inputs:
      platforms: { type: choice, options: [all, windows, macos, manylinux] }
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: false
```

`cancel-in-progress: false`, unlike the gate: a half-cancelled release is worse
than two of them.

### `check-version`

Reads `set(projectVersion 2.10)` (`CMakeLists.txt:6`) with a `sed` tolerant of
trailing arguments, since `CLAUDE.md` documents the form as
`set(projectVersion MAJOR.MINOR ...)`:

```sh
version=$(sed -n 's/^set(projectVersion[[:space:]]\+\([0-9]\+\.[0-9]\+\).*/\1/p' CMakeLists.txt)
```

An empty result is a hard failure. Then:

- **Tag push.** `${GITHUB_REF_NAME#v}` must match `^[0-9]+\.[0-9]+\.[0-9]+$`, and
  its `MAJOR.MINOR` must equal `projectVersion`. Outputs `version=2.10.3` and
  `patch=3`. A `v2.11.0` tag against `projectVersion 2.10`, or a bare `v2.10`,
  fails here — before four platforms spend an hour producing wrongly-named wheels.
- **Dispatch.** No tag to check against; `patch=0`,
  `version=<projectVersion>.0`.

Outputs: `version`, `patch`.

### Build jobs

Four jobs, each `uses:` one of the reusable workflows from §3:

| Job | Workflow | Extra `with` | Artifact |
|---|---|---|---|
| `wheels-manylinux` | `linux-wheels.yml` | — | `wheels-manylinux_2_28-x86_64` |
| `wheels-macos-arm64` | `macos-wheels.yml` | `os: macos-14` | `wheels-macos-arm64` |
| `wheels-macos-x86_64` | `macos-wheels.yml` | `os: macos-15-intel` | `wheels-macos-x86_64` |
| `wheels-windows` | `windows-wheels.yml` | — | `wheels-windows-x86_64` |

All four also pass `ci_pipeline_iid: ${{ needs.check-version.outputs.patch }}`, and
all four are gated with
`if: contains(fromJson('["all","<platform>"]'), inputs.platforms || 'all')` —
`macos` selects both macOS legs. A tag push carries no inputs, so `|| 'all'` makes
a release always build everything.

### `publish`

`needs: [check-version, wheels-manylinux, wheels-macos-arm64, wheels-macos-x86_64, wheels-windows]`,
`permissions: contents: write`, and:

```yaml
if: github.event_name == 'push' && github.ref_type == 'tag'
```

Both halves are load-bearing, for the reason
`../slideio/.github/workflows/release.yml` documents at its own publish job: the
dispatch API accepts a tag ref as readily as a branch, so
`github.ref_type == 'tag'` alone would let a manual run started against `v2.10.3`
publish a release built from one platform. Requiring `event_name == 'push'` is what
makes "a manual run cannot publish" true rather than usually true. The `platforms`
input therefore only ever shortens a rehearsal.

Steps: `actions/download-artifact@v4` with `pattern: wheels-*`,
`merge-multiple: true` into `dist/`; list it; then `softprops/action-gh-release@v2`
with `files: dist/*`, `draft: true`, `generate_release_notes: true`,
`fail_on_unmatched_files: true`, and a body naming the four platform/architecture
combinations and the supported Python range.

## 3. The three wheel workflows become reusable

Each gains `on: workflow_call` alongside its existing `workflow_dispatch`:

| Input | Type | Default | Purpose |
|---|---|---|---|
| `ci_pipeline_iid` | string | `''` | Becomes job-level `env: CI_PIPELINE_IID`, which `setup.py:38-41` turns into the wheel's patch component |
| `artifact_name` | string | per-platform | Distinct artifact per leg |
| `os` (macOS only) | string | `macos-14` | Which runner image |

`ci_pipeline_iid` has to be an **input**, not an inherited environment variable:
workflow-level `env` in the caller does not cross into a called workflow.

`macos-wheels.yml:22` must change from `runs-on: ${{ github.event.inputs.os }}` to
`runs-on: ${{ inputs.os }}`. Under `workflow_call` the `github.event.inputs`
context is empty and the job would fail to start; the `inputs` context resolves
under both triggers. The `workflow_dispatch` input keeps `type: choice` with the
same two options, so the manual experience is unchanged.

All three uploads become:

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: ${{ inputs.artifact_name }}
    path: <unchanged>
    if-no-files-found: error
    retention-days: 30
```

The naming is not cosmetic. `macos-wheels.yml:102` and `windows-wheels.yml:90`
upload with no `name:` today, so both default to `artifact`, and two unnamed
uploads in one release run collide under `upload-artifact@v4`.

Note that `build-validation.yml` necessarily repeats some of these steps rather
than calling these workflows: they build the whole 3.9–3.14 set, which is exactly
what a gate must not do. `../slideio` carries the same duplication between its own
two files for the same reason.

## 4. Cleanups included

**Dead environment variables.** All three workflows set `SLIDEIO_HOME`,
`CONAN_REVISIONS_ENABLED` and `CONAN_DISABLE_CHECK_COMPILER` at workflow level.
All three are removed:

- `SLIDEIO_HOME` is read by nothing — not in this repository, not in the pinned
  `extern/slideio`, not in the `../slideio` working copy (verified by grep over
  `*.py`, `*.txt`, `*.cmake`, `*.hpp`, `*.cpp`). It is also actively misleading:
  it is set to `${{ github.workspace }}/slideio`, the Python repository root, as
  if the C++ build read it. `build-slideio.py` passes `-bd`/`-pr` explicitly to
  the submodule's `install.py` instead (`build-slideio.py:142-146`).
- `CONAN_DISABLE_CHECK_COMPILER` is set as a CMake variable
  (`CMakeLists.txt:48`, `extern/slideio/CMakeLists.txt:85`), not read from the
  environment.
- `CONAN_REVISIONS_ENABLED` is a Conan 1 knob; this is a Conan 2 build.

**Conan cache key.** The key is
`hashFiles('slideio/.git/modules/extern/slideio/HEAD')`. If that glob matches
nothing, `hashFiles` returns an empty string, the key degrades to the bare prefix,
and `restore-keys` still produces a hit — so the failure is invisible and the cache
silently stops tracking the submodule commit. Replaced with an explicit step:

```sh
echo "sha=$(git rev-parse HEAD:extern/slideio)" >> "$GITHUB_OUTPUT"
```

keyed as `conan-<platform>-${{ steps.slideio.outputs.sha }}` with
`restore-keys: conan-<platform>-`. `git rev-parse HEAD:<path>` reads the gitlink
from the tree, so it works without the submodule being initialised.

**Documentation.** `CLAUDE.md:109` says `build-wheels-win.ps1` "loops over Python
3.8–3.14"; the script sets `$minversion = 9` (`build-wheels-win.ps1:2`), as do
`build-wheels-manylinux.sh:2` and `build-wheels-macos.sh:7` (capped at 13 on macOS
Intel). Corrected to 3.9–3.14, and the CI section is rewritten to describe both new
workflows and the `workflow_call` interface.

## 5. Version derivation

`setup.py:30` reads `MAJOR.MINOR` from `CMakeLists.txt` and `setup.py:38-41`
appends `CI_PIPELINE_IID` as the patch, defaulting to `0`. Nothing in `setup.py`
changes. The tag becomes the single source of the patch number:

```
tag v2.10.3  ->  check-version: projectVersion 2.10 == 2.10  OK
                 patch=3
             ->  each build job: env CI_PIPELINE_IID=3
             ->  slideio-2.10.3-cp312-cp312-*.whl
```

A dispatch produces `2.10.0` wheels, which are rehearsal artifacts and never
published. Cutting a patch release requires no file edit — only a tag. Bumping
`MAJOR.MINOR` still means editing `CMakeLists.txt:6`, which is also what
`CLAUDE.md` already prescribes when the `extern/slideio` pin moves.

## 6. Verification plan

CI YAML has no unit test, so verification is staged and nothing is claimed working
before the corresponding stage has run:

1. **Syntax.** `yaml.safe_load` every file under `.github/workflows/`; run
   `actionlint` if it is available on the machine.
2. **The version logic.** `check-version`'s shell block is the only real logic in
   this change. Run it locally against the real `CMakeLists.txt` with
   `GITHUB_REF_TYPE`/`GITHUB_REF_NAME` set to each of: `v2.10.3` (expect pass,
   `patch=3`), `v2.11.0` (expect fail), `v2.10` (expect fail), `v2.10.3.1`
   (expect fail), and no tag (expect `patch=0`). Record the output.
3. **The gate tests itself.** Push the branch and open the pull request against
   `main`; `build-validation.yml` then runs on all three platforms. Both the
   trigger and the three builds are verified by that run.
4. **Release rehearsal, after merge.** Dispatch `release.yml` with
   `platforms: all`. It builds and uploads all four artifacts and cannot publish.

Stage 4 cannot happen before merge: GitHub offers "Run workflow" only for workflow
files present on the default branch, a limitation `../slideio` records in its own
`release.yml`. The first real publish is therefore the first `v*` tag pushed after
this lands, and it produces a **draft** Release, which is reviewable before it is
visible.

## 7. Out of scope

- **PyPI and conda upload.** Still manual.
  `docs/superpowers/plans/2026-09-13-conda-packaging.md` §2 lists automating PyPI
  as an open question; this design neither answers nor blocks it — a publish step
  is added to one job when that is decided.
- **A Docker image workflow.** `docker/manylinux_2_28_x86_64/` and
  `docker/manylinux_2_28_s390x/` have no workflow here, while `../slideio` has one
  for its image. The image the wheels actually use
  (`booritas/slideio-manylinux_2_28_x86_64:2.10.0`) is built by that C++-side
  workflow, so adding a second publisher for the same tag would be worse than
  having none. Whether these two Dockerfiles are still needed is a separate
  question.
- **The s390x platform.** No workflow builds it today and none is added.
- **A ThreadSanitizer job.** `../slideio` has one; it instruments C++ test
  binaries this repository does not build.

## 8. Observed, not changed

`build-wheels-macos.sh:55` calls `generate_python_versions minversion maxversion`
— the literal names, not `$minversion`/`$maxversion`. It works only because bash
arithmetic evaluates a variable whose value is a name recursively, so
`((version=min_version))` resolves `min_version` → `"minversion"` → `9`. The loop
is correct today and the macOS workflow is green, but the construction is one
`local` away from silently building Python 3.0. Worth fixing separately; changing
it here would mean this design also owns a wheel-script behaviour change.
