# Code review: GitHub Actions CI for slideio-python

Date: 2026-10-01

Reviews the branch merged as `674ac3f` (PR #2), implementing
[the design](../specs/2026-10-01-python-ci-design.md) via
[the plan](../plans/2026-10-01-python-ci.md).

The branch was executed task-by-task with a fresh implementer and a fresh
reviewer per task, then this whole-branch review on top. It is kept because the
branch was squash-merged: the per-commit reasoning is not in `main`'s history,
and two of the decisions below read as redundant until you know what they
prevent.

---

# Whole-branch code review — GitHub Actions CI for slideio-python

Range: `dbfe0c6..9e44dd1` (10 commits). Read-only review; HEAD, index and working
tree untouched. Reviewed the final state of every changed file directly plus the
pre-branch originals via `git show`, alongside the spec, the plan and the ledger.

Verdict up front: **ready to merge with fixes.** Two Critical defects break real
paths on the first run; both are small, local edits.

---

## Strengths

- **`ci_version.py` is genuinely good.** Its `PROJECT_VERSION` regex
  (`ci_version.py:31`) matches `setup.py:30`'s in effect character for
  character, so the version check and the wheel name can never disagree. The
  leading-zero rejection (`TAG`, `ci_version.py:27`) catches a real PEP 440 trap
  before it ships. Every error message names `projectVersion` and says what to
  do about it. 15 tests cover the happy path, all four rejection shapes, the
  `None` branch and `main()`'s `$GITHUB_OUTPUT` contract. Moving this out of an
  inline `sed` block, against spec §2, was the right call and the ledger's
  justification holds.
- **The three contested hygiene rulings were resolved correctly.**
  `sets_variable()` (`tests/test_workflows.py:81-104`) measures the actual
  requirement — does any `env:` block, shell assignment or `GITHUB_ENV` append
  *set* this variable — and `TestSetsVariable` (`:203-247`) pins the helper so
  the two tests that can only ever fail cannot pass vacuously.
  `test_each_caches_conan_under_the_submodule_commit` (`:313`) does the same job
  for the cache-key test. This is a better suite than the plan specified, and
  every comment explaining *why* `SLIDEIO_SKIP_MISSING_IMAGES`, `.git/modules`
  and `build-wheels-macos.sh` are absent survives verbatim — which is what a
  future maintainer actually needs.
- **The cache-key fix is correct.** `git rev-parse HEAD:extern/slideio` reads
  the gitlink from the tree, so it works with `fetch-depth: 1`, on a PR merge
  ref, and without the submodule being initialised. The `safe.directory` line is
  in exactly the one job that needs it (container, `--global` writes to
  `/github/home`, same step, same user) and correctly absent from the two that
  do not. Spec §4's analysis of the old `hashFiles()` degradation is accurate.
- **The publish gate is right.** `github.event_name == 'push' &&
  github.ref_type == 'tag'` (`release.yml:130`) genuinely closes the
  dispatch-against-a-tag-ref hole. `needs` lists all four legs plus
  `check-version`, so no leg can be missing. `action-gh-release` defaults its
  token to `github.token`, so no secret is introduced. `draft: true` plus
  `fail_on_unmatched_files: true` make a first release reviewable rather than
  irreversible.
- **The reusable-workflow call surface is exact.** Every `uses:` path, every
  `with:` key and both `os` labels match the called workflows' declared
  `workflow_call.inputs`; artifact names are distinct and all `wheels-`-prefixed,
  matching publish's `wheels-*` glob. Independently re-derived; no mismatch.
- **Dead-variable removal is justified.**
  `docker/manylinux_2_28_x86_64/Dockerfile:3` setting `CONAN_REVISIONS_ENABLED`
  in the image explains where the workflow copies came from, and removing them
  changes nothing.

---

## Issues

### Critical (Must Fix)

#### C1. Manual dispatch of any of the three wheel workflows now uploads with an empty artifact name

`.github/workflows/linux-wheels.yml:106`, `macos-wheels.yml:139`,
`windows-wheels.yml:121` — `name: ${{ inputs.artifact_name }}`.

`artifact_name` is declared only under `on.workflow_call.inputs`. The `inputs`
context is populated from the *triggering event's own* input definitions: on a
`workflow_dispatch` run GitHub builds it from `on.workflow_dispatch.inputs`, and
a `workflow_call` default is not applied. `linux-wheels.yml` and
`windows-wheels.yml` declare no dispatch inputs at all; `macos-wheels.yml`
declares only `os`. So on a manual dispatch `inputs.artifact_name` is
unpopulated and the upload step receives `name: ""` — which `upload-artifact@v4`
rejects as an empty artifact name. (If the runner instead fell through to the
action's own `default: artifact`, all three would collide on `artifact`,
reinstating the exact defect spec §3 set out to remove.) Either way the dispatch
path is broken, and it breaks *after* a 20–40 minute build, at the last step,
with the wheels unrecoverable from the run.

This matters more than it looks: dispatch is the only way wheels are built today
(`v2.7.0`'s wheels were uploaded by hand), and the plan's Global Constraints say
in as many words that "existing `workflow_dispatch` behaviour of the three wheel
workflows must not change". Before this branch `linux-wheels.yml` uploaded as
`wheels` and the other two as `artifact`; after it, none of them upload at all
under dispatch.

Origin is **spec §3 and the plan**, not an implementer slip — both specify
`name: ${{ inputs.artifact_name }}` with a `workflow_call`-only default, and no
task was asked to check the dispatch path.

**Preferred fix: explicit fallbacks at the consumption sites.**

```yaml
name: ${{ inputs.artifact_name || 'wheels-manylinux_2_28-x86_64' }}   # linux-wheels.yml:106
name: ${{ inputs.artifact_name || 'wheels-macos-arm64' }}             # macos-wheels.yml:139
name: ${{ inputs.artifact_name || 'wheels-windows-x86_64' }}          # windows-wheels.yml:121
```

Why this over declaring the same inputs under `on.workflow_dispatch.inputs`: it
keeps the manual form byte-identical, which is what the Global Constraint asks
for; it is one line per site; and the fallback sits where the value is consumed,
so a future third trigger cannot reintroduce the gap. Declaring the inputs twice
also works but changes the dispatch UI and leaves two copies of each default to
drift.

Add one test: every `actions/upload-artifact` step's `name:` is a non-empty
literal or an expression containing `||`.

**`CI_PIPELINE_IID` has the same defect and it is harmless** — the team lead's
read is correct. `linux-wheels.yml:32`, `macos-wheels.yml:42`,
`windows-wheels.yml:28` are unpopulated under dispatch, and `setup.py:36-41`
gates on `if os.environ.get('CI_PIPELINE_IID')`, so `''` falls through to
`vrs_sub = '0'` — the same answer the declared `'0'` default gives. Add `|| '0'`
anyway for symmetry while the files are open; it costs nothing and removes the
need for the next reader to re-derive this.

#### C2. `tests/test_ci_version.py:21` shadows the installed wheel with the source tree for the whole pytest process

```python
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

The new module sorts first in collection, ahead of `test_color.py`,
`test_metadata.py` and `test_public_api.py`, all of which `import slideio` at
module level. Verified on this machine:

```
collection order: test_ci_version.py, test_color.py, test_metadata.py,
                  test_msvcredist.py, test_public_api.py, test_workflows.py
after importing test_ci_version: sys.path[0] = D:\Projects\slideio\slideio-python
slideio resolves to:             D:\Projects\slideio\slideio-python\slideio\__init__.py
```

`cd "$RUNNER_TEMP"` cannot prevent this — the poisoning happens from inside the
suite, after the `cd`. `test_pytest_always_runs_from_outside_the_checkout` now
certifies a guard that no longer guards, which is precisely the failure the
plan's Review Focus item 5 exists to prevent.

In CI it is a hard failure, not merely "tests the wrong tree".
`slideio/core/libs/` is untracked (`git ls-files slideio` returns only four
`.py` files) and `setup.py:197` stages the built binaries into `extdir` — the
`build/lib.*` tree — never into the source tree. So a fresh CI checkout's
`slideio` package cannot import at all: `from .libs.slideiopybind import …`
raises `ModuleNotFoundError`.

**Blast radius (asked for explicitly).** Worse than a per-module failure:
pytest **aborts the entire session** on a collection error. Verified with a
synthetic three-module directory where the middle module raises at import:

```
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.10s
exit=2
```

No tests ran — not even the two healthy modules. So the moment
`SLIDEIO_IMAGES_PATH` is set, every gate job and every release leg's test step
exits 2 having executed **zero** tests, including `test_ci_version.py` and
`test_workflows.py`. Half of this is pre-existing: `tests/test_msvcredist.py:20`
does the same insert and already shadows `test_public_api.py`; that it has never
been observed is itself evidence these test steps have never run.

**Fix:** `sys.path.append(...)` instead of `insert(0, ...)` in
`tests/test_ci_version.py:21` and `tests/test_msvcredist.py:20`, in the same
commit — otherwise the bug survives for `test_public_api.py`.
`tests/test_workflows.py` needs no path manipulation at all (it reads YAML by
path).

**`append` is sufficient (asked for explicitly).** Verified with a synthetic
tree where a stand-in `site-packages` holds an importable `slideio` and the
appended repo root holds a failing `slideio` plus `ci_version`:

```
ci_version imported from: …\ap\repo\ci_version.py
slideio ORIGIN: installed
```

`ci_version` and `msvcredist` are found because nothing in site-packages
provides either name, and the appended entry sits after site-packages so the
installed `slideio` wins. The path is derived from `__file__`, so running from
`$RUNNER_TEMP` by absolute path changes nothing. Consequence for I1: the new
corpus-free job does **not** need any additional fix — with `append` in place it
imports `ci_version` correctly whether or not a wheel is installed.

### Important (Should Fix)

#### I1. The two corpus-free test files never run in CI — **must-fix before merge**

`build-validation.yml:79,143,208` — every pytest step, in every job, in all four
workflows, is gated on `if: vars.SLIDEIO_IMAGES_PATH != ''`. With the variable
unset (its apparent state today) the gate builds three wheels and runs **zero**
tests, so the 61 tests this branch adds are verified by nothing but a
developer's laptop. With the variable set, C2 means the run aborts at collection
and they still do not execute. There is no configuration in which this branch's
own tests run in CI.

Asked directly: **must-fix before merge, not a follow-up.** The branch's central
claim is that the repository now has a per-commit gate, and the thing most
likely to regress — the structural pins on the workflow YAML, which exist
precisely because CI configuration has no other test — is the thing the gate
never checks. The whole point of the corpus gate is the tests that need images;
`tests/test_ci_version.py` and `tests/test_workflows.py` need neither images nor
a wheel, as plan Global Constraint 16 and the new `CLAUDE.md` paragraph both
state. It is also the cheapest job in the file.

Fix: one ungated job — `ubuntu-latest`, `actions/checkout@v4` (no submodules
needed), `actions/setup-python@v5`, `pip install pytest pyyaml`,
`pytest tests/test_ci_version.py tests/test_workflows.py`. Under a minute on
every PR. It changes the job set, so `tests/test_workflows.py:339`
(`test_builds_the_three_shipped_platforms`) must assert the three platform jobs
are *present* rather than that they are the complete set — keep that assertion
strong, since it is also what stops deferred finding 5 from mattering.

#### I2. No workflow-level `permissions:`, so `publish`'s `contents: write` is not least privilege

`release.yml:132-133` scopes `contents: write` to `publish`, but with no
top-level default every other job — including the four called wheel workflows,
which inherit the caller's token scope — receives the repository's default
`GITHUB_TOKEN` permission, which on an older repository is read/write across all
scopes. `test_publish_can_write_releases` encodes an intent the configuration
does not deliver.

Fix: `permissions: { contents: read }` at the top level of
`build-validation.yml` and `release.yml` (the job-level `contents: write` on
`publish` still wins), and ideally the same in the three wheel workflows.
Nothing in this change needs any other scope.

Otherwise the security posture is sound: the gate uses `pull_request`, not
`pull_request_target`, so a fork PR runs with a read-only token and no secrets;
the only thing exposed to a fork run is `vars.SLIDEIO_IMAGES_PATH`, a repository
*variable* rather than a secret, and only as a path string.

#### I3. `CLAUDE.md`'s new CI section states the gate runs `tests/` unconditionally

"each build the C++ library and **one** Python 3.12 wheel, then run `tests/`
against it" — true only when `SLIDEIO_IMAGES_PATH` is set, which the paragraph
never says, while the surrounding document is careful about exactly that gate
for the wheel workflows. With I1 unfixed this is the most misleading sentence in
the new documentation. One clause fixes it.

### Minor (Nice to Have)

- `tests/test_workflows.py:34` — the glob is `*.yml` only, so a workflow added
  as `*.yaml` escapes every hygiene test silently: the same class of invisible
  degradation the cache-key fix was about. Use both patterns.
- `build-validation.yml:56,59,80` — the gate's manylinux steps run under the
  default shell, while the proven `linux-wheels.yml:67,73` uses
  `shell: bash -el {0}` for the same work in the same image. Container `ENV` is
  inherited, so this will probably be fine; it is free to align, and the step it
  would break is the 15–40 minute one.
- `pyproject.toml`'s `[project.optional-dependencies] dev` lists `pillow` but
  not `pyyaml`, while `requirements-dev.txt` now lists both. The two lists have
  drifted; `pyyaml` belongs in whichever is canonical.
- `release.yml:77,86,96,106` — `inputs.platforms || 'all'` relies on the
  `inputs` context being null on a tag push. I believe it is, and Task 4's
  reviewer reached the same conclusion, but `github.event.inputs.platforms ||
  'all'` is the spelling with no doubt attached. If that expression ever yielded
  empty-but-truthy, all four legs would skip, `publish` would skip with them,
  and the run would report success having published nothing — a quiet failure
  mode on the one workflow where quiet is worst.
- `ci_version.py:31` — `PROJECT_VERSION` is unanchored, so a commented-out
  `# set(projectVersion 9.9)` above line 6 would win. Harmless *because*
  `setup.py:30` shares the weakness and would agree with it; worth `^\s*set` in
  both if either is ever touched.
- Deferred finding 6 (below) is the one deferred item worth five minutes.

---

## Deferred Minor Triage

1. **`task-1-report.md`'s two RED transcripts** — **defer.** Confirmed: line 25
   shows `ERROR tests/test_ci_version.py::test_module_import`, a node-id that
   cannot exist for a module-level `ModuleNotFoundError`, so the first block is
   paraphrase formatted as captured output. Report integrity only; the code and
   the GREEN evidence are independently verified. Should stay recorded as a
   report defect rather than be dropped.
2. **`assertTrue(..., sorted(ALL_WORKFLOWS))` at `tests/test_workflows.py:111`** —
   **defer.** A list as `msg` is legal and renders usefully in failure output.
3. **`test_the_wheel_workflows_are_all_present` placement** — **defer.** It is
   the glob's anti-vacuity guard and belongs where the ruling put it;
   "exercises every workflow" is not a property the class name promises.
4. **`actionlint` never run** — **defer**, with one caveat: it is the only check
   that might have independently questioned the `inputs` expressions behind C1.
   Run it once before merge if it can be had; otherwise the first push validates
   the YAML server-side.
5. **Vacuity in `test_no_job_runs_a_full_wheel_script` and
   `test_one_platform_failing_does_not_hide_the_others`** — **defer.** Both are
   masked in a whole-suite run by `test_builds_the_three_shipped_platforms`, and
   `-k`-only runs are a developer convenience, not the gate. Keep that job-set
   assertion strong when fixing I1, for exactly this reason.
6. **Repair-before-test ordering not asserted
   (`tests/test_workflows.py:381-392`)** — **defer, but fix it while in the
   file.** `assertLess(index_of_repair, index_of_test)` is two lines and the
   property is load-bearing: an unrepaired Windows wheel does not import, so a
   reordering would turn the gate green against an uninstallable artifact.
7. **`assertIn('ci_version.py', str(self.jobs['check-version']))` at `:413`** —
   **defer**, and correct the ledger's stated reason: `load()` parses the YAML,
   so comments are absent from the data and cannot satisfy this assertion. The
   real, much narrower loophole is a step `name:` or `description` containing
   the string. Low value either way.

---

## Declined to Judge

- `~/.conan2` as the cache path in container jobs, where `HOME=/github/home` and
  the image's prebuilt Conan cache lives elsewhere — pre-existing in
  `linux-wheels.yml`; the gate copies the proven workflow, and changing it is a
  performance question for its own change.
- `rename-macos-wheels.sh` renaming only `macosx_15_0_*`, so `macos-14` wheels
  keep a `macosx_14_0` tag — pre-existing wheel-script behaviour, now reaching a
  Release page; raising it would make this change own a wheel-naming decision.
- `lib.ps1:53`'s `$extractDir` resolving through PowerShell dynamic scoping from
  `Repair-Naming` — pre-existing, works, and the gate calls it the same way the
  green workflow does.
- `build-wheels-macos.sh:55`'s `generate_python_versions minversion maxversion`
  — spec §8 explicitly observed-not-changed.
- Conan is unpinned in both the conda and the new pip install paths, so a Conan
  release can reject the hardcoded profiles — pre-existing on every platform;
  `CLAUDE.md` already documents the failure mode.
- No PyPI/conda publish step, no Docker image workflow, no s390x, no
  ThreadSanitizer job — spec §7 out of scope.
- No `timeout-minutes` on the new long-running jobs — not in spec or plan, and
  the 360-minute default is above the observed 1h12m worst case.
- Whether `SLIDEIO_IMAGES_PATH` should be set at all, and to what — an operator
  decision the spec deliberately leaves to the repository owner. I1 concerns
  only the tests that need no corpus.

---

## Recommendations

1. One small commit for C1 and C2: three `||` fallbacks on the artifact names
   (plus three on `CI_PIPELINE_IID` for symmetry) and two `insert(0,` →
   `append(`.
2. Same pass for I1 (the ungated corpus-free job, with
   `test_builds_the_three_shipped_platforms` relaxed to a subset assertion) and
   I2 (top-level `permissions: contents: read`). Roughly twenty lines, and they
   are what turns the gate from "it builds" into "it checks".
3. Add one test per Critical so neither can return: every `upload-artifact`
   `name:` is a non-empty literal or contains `||`; and no file in `tests/`
   prepends the repository root to `sys.path` (one regex over `tests/*.py`).
4. Then run the plan's Task 6 as written. The push is still the only thing that
   can prove the macOS/Windows pip-Conan route and the container
   `git rev-parse`; both look sound on inspection and neither is affected by the
   fixes above.
5. Record in the ledger that spec §3 is C1's origin, so the next change adding a
   `workflow_call` input does not repeat it.

---

## Assessment

**Ready to merge?** With fixes.

**Reasoning:** The design is sound, `ci_version.py` and the structural test
suite are better than the plan asked for, and the release orchestration's
interfaces check out end to end — but two defects break real paths on their
first run: a manual dispatch of any wheel workflow now fails at its upload step,
and the new test module shadows the installed wheel with the source tree, which
aborts the whole pytest session the moment the corpus variable is set. With
those two fixed plus the ungated corpus-free job and a `permissions` default,
this is ready.

---

## Decisions taken during execution

Nine rulings made while the plan was executed, in order. Each was a point where
the plan, the spec and the code disagreed and something had to be decided; they
are recorded because the squash merge left no other trace of them.

**1. The workflow list in `tests/test_workflows.py` is discovered by glob.**
The plan named `build-validation.yml` and `release.yml` in a fixed tuple, but
later tasks create those files, so the task that wrote the module would have
committed a knowingly-failing test. Globbing `.github/workflows/*.yml` (and
`*.yaml`) covers whatever exists at any point, and picks up a future workflow
added without the hygiene properties for free.
*Cost if wrong:* the hygiene tests no longer assert a named file exists;
`test_the_wheel_workflows_are_all_present` covers that instead.

**2. "`fail-fast: false`" is three jobs with no `needs`.**
The design asked for it, but the gate has no matrix for `strategy.fail-fast` to
attach to. Independent top-level jobs are the correct expression.
*Cost if wrong:* none to behaviour.

**3. No git worktree.** A worktree needed `pybind11`, `extern/slideio` and its
four submodules re-initialised plus a fresh C++ build -- 14-40 minutes -- for a
change touching YAML, one script and two test files.
*Cost if wrong:* a bad task is undone with git rather than by discarding a
worktree.

**4. The first push waited for the repository owner.** First outward-facing
action. *Cost if wrong:* a delay before CI evidence existed.

**5. The hygiene assertions measure parsed structure, not raw file text.** The
consequential one, and the reason this document exists. The plan specified three
tests as `assertNotIn(<string>, <whole file text>)` -- and the same plan
mandated workflow comments containing exactly those strings, because the
workflows name `SLIDEIO_SKIP_MISSING_IMAGES`, `hashFiles() on .git/modules` and
`build-wheels-macos.sh` precisely to explain why each is absent or unused. A
substring check over the file forbids the explanation along with the mistake.
The collision surfaced three separate times; two implementers resolved it by
euphemising the comment and were overruled. The tests now read `env:` blocks,
shell assignments in `run:` steps, `actions/cache` key fields and each job's own
`run:` text, and every comment stands verbatim.
*Cost if wrong:* the tests catch a variable being **set** rather than merely
mentioned -- which is the actual requirement. Do not simplify them back.

**6. Five of the review's Minor findings were taken into the fix wave, seven
deferred** (the seven were cleared afterwards at the owner's request).
*Cost if wrong:* all were test hygiene; none touched a shipped artifact.

**7. `ci_version.py`'s `projectVersion` regex was left unanchored** despite the
review raising it. It is harmless *because* `setup.py:30` shares the identical
weakness and therefore always agrees with it; anchoring one alone would let the
version the tag check validates and the version the wheel gets disagree.
Clearing it properly means changing `setup.py` too.
*Cost if wrong:* a commented-out `set(projectVersion ...)` above line 6 of
`CMakeLists.txt` would be read by both, consistently. **Still open.**

**8. The three `TestBuildValidation` assertions that quantified over every job
were scoped to a `PLATFORM_JOBS` constant, not weakened,** when the new ungated
`tooling` job broke them. *Cost if wrong:* loose scoping would stop them pinning
the platform jobs.

**9. Three residual test-strength regressions were fixed rather than parked.**
All three were created by the fix wave itself, all were one to three lines and
fully specified, and parking them would have shipped guards that no longer
guarded -- the same defect class ruling 5 addressed.
*Cost if wrong:* they landed without an independent review seat.

---

## Still open after merge

- Ruling 7's unanchored regex, which needs `setup.py` touched to clear properly.
- `actionlint` has never run against these workflows: it is not installed on the
  author's machine, and it is the one check that might independently have caught
  the dispatch upload-name defect (C1) before CI did.
- The `tests/` step in all four workflows is gated on the `SLIDEIO_IMAGES_PATH`
  repository variable, which is unset. CI therefore proves the wheels build, not
  that they work. Setting it is the operator decision the design leaves open.
- The gate has no `paths-ignore`, so a documentation-only commit costs a full
  build on three platforms (~45 minutes of runner time).
