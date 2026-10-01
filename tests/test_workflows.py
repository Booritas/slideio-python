"""Structural tests for the GitHub Actions workflows.

These cover CI configuration rather than the built wheel, so they read the YAML
from the repository root instead of importing the installed package -- the same
arrangement tests/test_msvcredist.py uses for build tooling. The suite is run
from outside the checkout (see CLAUDE.md), so paths are derived from this file's
own location. It needs neither a built wheel nor SLIDEIO_IMAGES_PATH.

Each assertion stands for a failure that is otherwise invisible until a release:
an unnamed artifact that collides with another platform's, a cache key that has
silently stopped tracking the submodule commit, a publish job a manual run could
reach, a test step that runs pytest from inside the checkout and so imports the
source tree instead of the wheel.
"""
import glob
import os
import re
import unittest

import yaml

WORKFLOW_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    '.github', 'workflows')

WHEEL_WORKFLOWS = ('linux-wheels.yml', 'macos-wheels.yml',
                   'windows-wheels.yml')
# Discovered rather than listed, so the hygiene tests below cover whatever
# workflows exist -- including build-validation.yml and release.yml once
# later work adds them, and any workflow a future change adds without these
# properties.
ALL_WORKFLOWS = tuple(sorted(
    os.path.basename(path)
    for path in glob.glob(os.path.join(WORKFLOW_DIR, '*.yml'))))


def read(name):
    with open(os.path.join(WORKFLOW_DIR, name), encoding='utf-8') as handle:
        return handle.read()


def load(name):
    return yaml.safe_load(read(name))


def triggers(workflow):
    """Return the `on:` block.

    YAML 1.1 resolves the bare key `on` to the boolean True, which is what
    PyYAML hands back -- so `workflow['on']` raises KeyError for a reason that
    has nothing to do with CI. Both spellings are accepted here because a
    quoted `"on":` in a future edit would parse as the string.
    """
    if 'on' in workflow:
        return workflow['on']
    return workflow[True]


def steps_of(workflow):
    """Yield (job_name, step) for every job that defines steps.

    Jobs that only `uses:` a reusable workflow have no steps and are skipped.
    """
    for job_name, job in workflow.get('jobs', {}).items():
        for step in job.get('steps') or []:
            yield job_name, step


def env_blocks(workflow):
    """Yield every `env:` mapping in the workflow -- workflow, job and step."""
    if isinstance(workflow.get('env'), dict):
        yield workflow['env']
    for job in workflow.get('jobs', {}).values():
        if isinstance(job.get('env'), dict):
            yield job['env']
        for step in job.get('steps') or []:
            if isinstance(step.get('env'), dict):
                yield step['env']


def sets_variable(workflow, variable):
    """True if anything in the workflow sets `variable`.

    Deliberately conservative: a guard against a variable silently coming
    back should err towards failing.
    """
    if any(variable in env for env in env_blocks(workflow)):
        return True
    # `VAR=x`, `export VAR=x`, `VAR=x cmd`, and the same after a ; && || pipe.
    assignment = re.compile(
        r'(?:^|[;&|]|\bexport\s+)\s*' + re.escape(variable) + r'\s*=',
        re.MULTILINE)
    for _job, step in steps_of(workflow):
        run = str(step.get('run', ''))
        if assignment.search(run):
            return True
        # The Actions idiom that exports a variable to every later step by
        # appending to the file $GITHUB_ENV names -- `echo VAR=x >>
        # "$GITHUB_ENV"`, or a heredoc into the same file. A step that
        # mentions both the variable and GITHUB_ENV is treated as setting it;
        # there is no other reason for one step to name both.
        if 'GITHUB_ENV' in run and variable in run:
            return True
    return False


class TestEveryWorkflow(unittest.TestCase):
    def test_the_wheel_workflows_are_all_present(self):
        # ALL_WORKFLOWS is discovered by glob; this is what stops every test in
        # this class passing vacuously if the glob ever finds nothing.
        self.assertTrue(set(WHEEL_WORKFLOWS) <= set(ALL_WORKFLOWS),
                        sorted(ALL_WORKFLOWS))

    def test_all_parse(self):
        for name in ALL_WORKFLOWS:
            with self.subTest(workflow=name):
                self.assertIsInstance(load(name), dict)

    def test_triggers_are_reachable(self):
        # Without this, the `on:`/True trap above could make every other
        # trigger assertion in this file pass vacuously.
        for name in ALL_WORKFLOWS:
            with self.subTest(workflow=name):
                self.assertTrue(triggers(load(name)))

    def test_no_dead_environment_variables(self):
        # SLIDEIO_HOME is read by nothing in this repository, the pinned
        # extern/slideio, or the C++ working copy; CONAN_DISABLE_CHECK_COMPILER
        # is a CMake variable (CMakeLists.txt:48), not an environment one; and
        # CONAN_REVISIONS_ENABLED is a Conan 1 knob in a Conan 2 build.
        #
        # Structural rather than textual, for the reason given in
        # test_skip_missing_images_is_never_set.
        for name in ALL_WORKFLOWS:
            for dead in ('SLIDEIO_HOME', 'CONAN_REVISIONS_ENABLED',
                         'CONAN_DISABLE_CHECK_COMPILER'):
                with self.subTest(workflow=name, variable=dead):
                    self.assertFalse(sets_variable(load(name), dead))

    def test_skip_missing_images_is_never_set(self):
        # CLAUDE.md: CI must leave it unset, so a missing image fails the run
        # instead of quietly skipping the test that needed it.
        #
        # Checked against env: blocks and shell assignments rather than the
        # file text. The test steps name this variable in a comment precisely
        # to explain why it is absent, and a substring check would forbid
        # saying so -- which is the one thing a reader of those steps most
        # needs to know.
        for name in ALL_WORKFLOWS:
            with self.subTest(workflow=name):
                self.assertFalse(
                    sets_variable(load(name), 'SLIDEIO_SKIP_MISSING_IMAGES'))

    def test_cache_keys_do_not_hash_the_git_directory(self):
        # hashFiles() on a glob that matches nothing returns an empty string,
        # restore-keys then papers over the degraded key, and the cache stops
        # tracking the submodule commit with nothing in the log to say so.
        #
        # Checked against the cache steps' own key fields rather than the file
        # text, so the comment above a corrected key can still name the
        # mistake it corrects.
        for name in ALL_WORKFLOWS:
            for job, step in steps_of(load(name)):
                if not str(step.get('uses', '')).startswith('actions/cache'):
                    continue
                with self.subTest(workflow=name, job=job):
                    parameters = step.get('with', {})
                    keys = ' '.join(str(parameters.get(field, ''))
                                    for field in ('key', 'restore-keys'))
                    self.assertNotIn('.git', keys)

    def test_uploads_are_named_and_fail_when_empty(self):
        for name in ALL_WORKFLOWS:
            for job, step in steps_of(load(name)):
                if not str(step.get('uses', '')).startswith(
                        'actions/upload-artifact'):
                    continue
                with self.subTest(workflow=name, job=job):
                    parameters = step.get('with', {})
                    self.assertIn('name', parameters)
                    self.assertEqual('error',
                                     parameters.get('if-no-files-found'))

    def test_pytest_always_runs_from_outside_the_checkout(self):
        # The repository root holds a slideio/ package directory, so pytest run
        # from inside the checkout imports the source tree rather than the
        # installed wheel (CLAUDE.md).
        found = 0
        for name in ALL_WORKFLOWS:
            for job, step in steps_of(load(name)):
                run = str(step.get('run', ''))
                if 'pytest' not in run:
                    continue
                found += 1
                with self.subTest(workflow=name, job=job):
                    self.assertTrue(
                        'cd "$RUNNER_TEMP"' in run
                        or 'Set-Location $env:RUNNER_TEMP' in run,
                        'this pytest step never leaves the checkout')
        self.assertGreater(found, 0, 'no pytest step found at all')


class TestSetsVariable(unittest.TestCase):
    """Unit tests for the helper the two hygiene tests depend on.

    Those tests can only fail; without these, a sets_variable() that never
    returned True would make both of them pass vacuously.
    """

    def test_detects_a_workflow_level_env_entry(self):
        self.assertTrue(sets_variable({'env': {'VAR': '1'}}, 'VAR'))

    def test_detects_a_job_level_env_entry(self):
        self.assertTrue(sets_variable(
            {'jobs': {'build': {'env': {'VAR': '1'}}}}, 'VAR'))

    def test_detects_a_step_level_env_entry(self):
        self.assertTrue(sets_variable(
            {'jobs': {'build': {'steps': [{'env': {'VAR': '1'}}]}}}, 'VAR'))

    def test_detects_a_shell_assignment(self):
        self.assertTrue(sets_variable(
            {'jobs': {'build': {'steps': [{'run': 'export VAR=1\n'}]}}},
            'VAR'))

    def test_detects_the_github_env_idiom(self):
        self.assertTrue(sets_variable(
            {'jobs': {'build': {'steps': [
                {'run': 'echo "VAR=1" >> "$GITHUB_ENV"\n'}]}}},
            'VAR'))

    def test_detects_a_heredoc_into_github_env(self):
        self.assertTrue(sets_variable(
            {'jobs': {'build': {'steps': [
                {'run': 'cat >> "$GITHUB_ENV" <<EOF\nVAR=1\nEOF\n'}]}}},
            'VAR'))

    def test_a_comment_naming_the_variable_does_not_count(self):
        # The reason these checks are structural at all: the workflows name
        # SLIDEIO_SKIP_MISSING_IMAGES in a comment to explain why it is unset.
        self.assertFalse(sets_variable(
            {'jobs': {'build': {'steps': [
                {'run': 'echo building  # VAR stays unset on purpose\n'}]}}},
            'VAR'))

    def test_a_similarly_named_variable_does_not_count(self):
        self.assertFalse(sets_variable({'env': {'VAR_SUFFIX': '1'}}, 'VAR'))


class TestWheelWorkflows(unittest.TestCase):
    def test_callable_and_dispatchable(self):
        for name in WHEEL_WORKFLOWS:
            with self.subTest(workflow=name):
                on = triggers(load(name))
                self.assertIn('workflow_call', on)
                self.assertIn('workflow_dispatch', on)

    def test_orchestration_inputs_are_declared(self):
        for name in WHEEL_WORKFLOWS:
            with self.subTest(workflow=name):
                inputs = triggers(load(name))['workflow_call']['inputs']
                self.assertEqual('string', inputs['ci_pipeline_iid']['type'])
                self.assertEqual('string', inputs['artifact_name']['type'])

    def test_patch_defaults_to_zero_not_empty(self):
        # A manual dispatch passes no patch. setup.py:40 treats '' as absent and
        # falls back to '0', so '' would work -- but '0' says what the version
        # will be instead of depending on that fallback.
        for name in WHEEL_WORKFLOWS:
            with self.subTest(workflow=name):
                inputs = triggers(load(name))['workflow_call']['inputs']
                self.assertEqual('0', inputs['ci_pipeline_iid']['default'])

    def test_patch_reaches_the_build_environment(self):
        for name in WHEEL_WORKFLOWS:
            with self.subTest(workflow=name):
                self.assertIn('CI_PIPELINE_IID: ${{ inputs.ci_pipeline_iid }}',
                              read(name))

    def test_default_artifact_names_are_distinct(self):
        defaults = [
            triggers(load(name))['workflow_call']['inputs']
            ['artifact_name']['default'] for name in WHEEL_WORKFLOWS]
        self.assertEqual(len(defaults), len(set(defaults)))
        for default in defaults:
            # release.yml's publish job downloads with pattern wheels-*.
            self.assertTrue(default.startswith('wheels-'), default)

    def test_uploads_use_the_artifact_name_input(self):
        for name in WHEEL_WORKFLOWS:
            with self.subTest(workflow=name):
                self.assertIn('name: ${{ inputs.artifact_name }}', read(name))

    def test_macos_runner_comes_from_the_inputs_context(self):
        # github.event.inputs is empty under workflow_call, so a job whose
        # runs-on reads it would fail to start.
        #
        # Read from the parsed job rather than the file text, so a comment may
        # name github.event.inputs to explain why it is not used.
        jobs = load('macos-wheels.yml')['jobs']
        self.assertEqual(1, len(jobs))
        self.assertEqual('${{ inputs.os }}',
                         next(iter(jobs.values()))['runs-on'])

    def test_macos_offers_both_architectures_to_both_triggers(self):
        on = triggers(load('macos-wheels.yml'))
        self.assertEqual('macos-14',
                         on['workflow_call']['inputs']['os']['default'])
        self.assertEqual(
            ['macos-14', 'macos-15-intel'],
            on['workflow_dispatch']['inputs']['os']['options'])

    def test_each_caches_conan_under_the_submodule_commit(self):
        # Guards test_cache_keys_do_not_hash_the_git_directory against passing
        # vacuously, and pins what the key is actually derived from.
        for name in WHEEL_WORKFLOWS:
            with self.subTest(workflow=name):
                caches = [step for _job, step in steps_of(load(name))
                          if str(step.get('uses', '')).startswith(
                              'actions/cache')]
                self.assertEqual(1, len(caches))
                self.assertIn('steps.slideio.outputs.sha',
                              caches[0]['with']['key'])


class TestBuildValidation(unittest.TestCase):
    def setUp(self):
        self.workflow = load('build-validation.yml')

    def test_runs_on_push_and_pull_request_to_main(self):
        on = triggers(self.workflow)
        self.assertEqual(['main'], on['push']['branches'])
        self.assertEqual(['main'], on['pull_request']['branches'])
        self.assertIn('workflow_dispatch', on)

    def test_supersedes_its_own_earlier_runs(self):
        self.assertTrue(self.workflow['concurrency']['cancel-in-progress'])

    def test_builds_the_three_shipped_platforms(self):
        self.assertEqual({'manylinux', 'macos', 'windows'},
                         set(self.workflow['jobs']))

    def test_one_platform_failing_does_not_hide_the_others(self):
        for name, job in self.workflow['jobs'].items():
            with self.subTest(job=name):
                self.assertNotIn('needs', job)

    def test_no_job_runs_a_full_wheel_script(self):
        # The gate builds one wheel per platform; the 3.9-3.14 loop the wheel
        # scripts run is roughly six times the cost.
        #
        # Checked against the steps' own `run:` text rather than the whole
        # file. The macOS job's comment names build-wheels-macos.sh to explain
        # why it does not use conda, and a substring check over the file would
        # forbid that explanation -- YAML comments are not in the parsed data,
        # so this surface cannot confuse the two.
        invocation = re.compile(r'build-wheels-\S*\.(?:sh|ps1)')
        for job, step in steps_of(self.workflow):
            with self.subTest(job=job):
                self.assertIsNone(
                    invocation.search(str(step.get('run', ''))))

    def test_every_job_tests_the_wheel_behind_the_corpus_variable(self):
        for name, job in self.workflow['jobs'].items():
            with self.subTest(job=name):
                tested = [step for step in job['steps']
                          if 'pytest' in str(step.get('run', ''))]
                self.assertEqual(1, len(tested))
                self.assertIn('vars.SLIDEIO_IMAGES_PATH', tested[0]['if'])

    def test_every_job_checks_out_submodules_recursively(self):
        for name, job in self.workflow['jobs'].items():
            with self.subTest(job=name):
                checkouts = [step for step in job['steps']
                             if str(step.get('uses', '')).startswith(
                                 'actions/checkout')]
                self.assertEqual(1, len(checkouts))
                self.assertEqual('recursive',
                                 checkouts[0]['with']['submodules'])

    def test_windows_repairs_the_pyd_name_inside_the_wheel(self):
        # lib.ps1:47 renames slideiopybind*.pyd to the name the package
        # imports; an unrepaired Windows wheel does not import at all, so a
        # gate that skipped this would be testing something that never ships.
        steps = self.workflow['jobs']['windows']['steps']
        self.assertTrue(any('Repair-Naming' in str(step.get('run', ''))
                            for step in steps))

    def test_manylinux_repairs_the_wheel_before_testing_it(self):
        steps = self.workflow['jobs']['manylinux']['steps']
        self.assertTrue(any('auditwheel repair' in str(step.get('run', ''))
                            for step in steps))


class TestRelease(unittest.TestCase):
    WHEEL_JOBS = ('wheels-manylinux', 'wheels-macos-arm64',
                  'wheels-macos-x86_64', 'wheels-windows')

    def setUp(self):
        self.workflow = load('release.yml')
        self.jobs = self.workflow['jobs']

    def test_triggers_on_version_tags_and_dispatch(self):
        on = triggers(self.workflow)
        self.assertEqual(['v*'], on['push']['tags'])
        self.assertIn('workflow_dispatch', on)

    def test_does_not_cancel_a_running_release(self):
        # A half-cancelled release is worse than two of them.
        self.assertFalse(self.workflow['concurrency']['cancel-in-progress'])

    def test_the_version_is_checked_before_anything_builds(self):
        self.assertIn('ci_version.py', str(self.jobs['check-version']))
        for job in self.WHEEL_JOBS:
            with self.subTest(job=job):
                self.assertIn('check-version', self.jobs[job]['needs'])

    def test_each_leg_calls_a_wheel_workflow_with_the_derived_patch(self):
        expected = {
            'wheels-manylinux': './.github/workflows/linux-wheels.yml',
            'wheels-macos-arm64': './.github/workflows/macos-wheels.yml',
            'wheels-macos-x86_64': './.github/workflows/macos-wheels.yml',
            'wheels-windows': './.github/workflows/windows-wheels.yml',
        }
        for job, uses in expected.items():
            with self.subTest(job=job):
                self.assertEqual(uses, self.jobs[job]['uses'])
                self.assertEqual('${{ needs.check-version.outputs.patch }}',
                                 self.jobs[job]['with']['ci_pipeline_iid'])

    def test_every_leg_uploads_under_a_distinct_name(self):
        names = [self.jobs[job]['with']['artifact_name']
                 for job in self.WHEEL_JOBS]
        self.assertEqual(len(names), len(set(names)))
        for name in names:
            self.assertTrue(name.startswith('wheels-'), name)

    def test_both_macos_architectures_are_built(self):
        self.assertEqual('macos-14',
                         self.jobs['wheels-macos-arm64']['with']['os'])
        self.assertEqual('macos-15-intel',
                         self.jobs['wheels-macos-x86_64']['with']['os'])

    def test_a_tag_push_builds_every_platform(self):
        # A tag push carries no inputs, so `inputs.platforms || 'all'` has to
        # fall back to 'all' in every leg's condition.
        for job in self.WHEEL_JOBS:
            with self.subTest(job=job):
                self.assertIn("inputs.platforms || 'all'", self.jobs[job]['if'])

    def test_a_manual_run_cannot_publish(self):
        # Both halves are load-bearing: the dispatch API accepts a tag ref as
        # readily as a branch, so github.ref_type alone would let a manual
        # one-platform run publish a release.
        condition = self.jobs['publish']['if']
        self.assertIn("github.event_name == 'push'", condition)
        self.assertIn("github.ref_type == 'tag'", condition)

    def test_publish_waits_for_every_platform(self):
        self.assertEqual({'check-version'} | set(self.WHEEL_JOBS),
                         set(self.jobs['publish']['needs']))

    def test_publish_can_write_releases(self):
        self.assertEqual('write',
                         self.jobs['publish']['permissions']['contents'])

    def test_publish_downloads_every_wheel_artifact(self):
        downloads = [step for step in self.jobs['publish']['steps']
                     if str(step.get('uses', '')).startswith(
                         'actions/download-artifact')]
        self.assertEqual(1, len(downloads))
        self.assertEqual('wheels-*', downloads[0]['with']['pattern'])
        self.assertTrue(downloads[0]['with']['merge-multiple'])

    def test_publish_creates_a_reviewable_draft(self):
        releases = [step for step in self.jobs['publish']['steps']
                    if str(step.get('uses', '')).startswith(
                        'softprops/action-gh-release')]
        self.assertEqual(1, len(releases))
        parameters = releases[0]['with']
        self.assertTrue(parameters['draft'])
        self.assertTrue(parameters['fail_on_unmatched_files'])


if __name__ == '__main__':
    unittest.main()
