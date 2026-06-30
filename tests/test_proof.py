"""Lane D - Proof Runner tests.

Config presence/shape checks, required vs optional command outcomes, evidence
JSONL append-only semantics, and no-secret/no-source-name leakage in evidence.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from nexskill import proof
from nexskill.contracts import (
    CONFIG_SCHEMA_VERSION,
    EVIDENCE_SCHEMA_VERSION,
    NexSkillError,
    ProjectConfig,
    SkillSource,
    default_config,
)


class _Repo:
    def __init__(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def write_config(self, config: ProjectConfig):
        proof.write_config(self.root, config)

    def add_config(self, *, checks=None, project_name="demo"):
        cfg = default_config(project_name)
        if checks is not None:
            cfg = ProjectConfig(
                schema_version=CONFIG_SCHEMA_VERSION,
                project_name=project_name,
                skill_sources=[SkillSource(type="local", path=".nexskill/skills")],
                checks=checks,
                policies={"product_name": "NexSkill", "forbid_source_names_in_reports": True},
            )
        self.write_config(cfg)
        return cfg

    def cleanup(self):
        self.tmp.cleanup()


class CheckExecutionTests(unittest.TestCase):
    def setUp(self):
        self.repo = _Repo()

    def tearDown(self):
        self.repo.cleanup()

    def test_clean_repo_passes(self):
        self.repo.add_config()
        result = proof.run_checks(self.repo.root)
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.blockers, [])
        # always-on config check present
        ids = [c.id for c in result.checks]
        self.assertIn("config", ids)

    def test_missing_config_fails(self):
        # no config written
        with self.assertRaises(NexSkillError) as ctx:
            proof.run_checks(self.repo.root)
        self.assertEqual(ctx.exception.code, "CONFIG_MISSING")

    def test_failed_required_check_is_blocker(self):
        from nexskill.contracts import CheckConfig

        cfg = self.repo.add_config(
            checks=[CheckConfig(id="tests", command="exit 1", required=True)]
        )
        result = proof.run_checks(self.repo.root, config=cfg)
        self.assertEqual(result.status, "failed")
        self.assertTrue(any("tests" in b for b in result.blockers))
        # config check itself still passes
        tests_outcome = next(c for c in result.checks if c.id == "tests")
        self.assertEqual(tests_outcome.status, "failed")

    def test_optional_check_failure_is_warning_not_blocker(self):
        from nexskill.contracts import CheckConfig

        cfg = self.repo.add_config(
            checks=[CheckConfig(id="lint", command="exit 1", required=False)]
        )
        result = proof.run_checks(self.repo.root, config=cfg)
        self.assertEqual(result.status, "warning")
        self.assertEqual(result.blockers, [])
        self.assertTrue(any("lint" in w for w in result.warnings))

    def test_passing_command_records_passed(self):
        from nexskill.contracts import CheckConfig

        cfg = self.repo.add_config(
            checks=[CheckConfig(id="ok", command="true", required=True)]
        )
        result = proof.run_checks(self.repo.root, config=cfg)
        ok = next(c for c in result.checks if c.id == "ok")
        self.assertEqual(ok.status, "passed")


class CloseoutEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.repo = _Repo()

    def tearDown(self):
        self.repo.cleanup()

    def test_closeout_writes_append_only_evidence(self):
        self.repo.add_config()
        proof.closeout(self.repo.root)
        proof.closeout(self.repo.root)
        events = proof.read_evidence(self.repo.root)
        # two closeout events, both valid
        self.assertEqual(len(events), 2)
        for ev in events:
            self.assertEqual(ev.op, "closeout")
            self.assertEqual(ev.schema_version, EVIDENCE_SCHEMA_VERSION)
        # append-only: first line is still the first event
        lines = [
            ln for ln in proof.evidence_path(self.repo.root).read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["op"], "closeout")

    def test_closeout_records_failure_evidence_not_hidden(self):
        from nexskill.contracts import CheckConfig

        self.repo.add_config(
            checks=[CheckConfig(id="tests", command="exit 1", required=True)]
        )
        proof.closeout(self.repo.root)
        events = proof.read_evidence(self.repo.root)
        self.assertEqual(events[-1].status, "failed")
        self.assertIn("tests", json.dumps(events[-1].to_dict()))

    def test_evidence_jsonl_is_parseable_line_by_line(self):
        self.repo.add_config()
        proof.closeout(self.repo.root)
        path = proof.evidence_path(self.repo.root)
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                # each non-blank line is a standalone JSON object
                self.assertTrue(line.startswith("{"))
                self.assertTrue(line.endswith("}"))
                json.loads(line)

    def test_evidence_excludes_secrets_and_source_names(self):
        from nexskill.contracts import CheckConfig

        # A command that prints something secret-like to stderr; the summary
        # must not embed raw command output verbatim in a way that leaks.
        self.repo.add_config(
            checks=[CheckConfig(id="leak", command="echo API_KEY=abc123 1>&2; exit 1", required=False)]
        )
        proof.closeout(self.repo.root)
        events = proof.read_evidence(self.repo.root)
        blob = json.dumps([e.to_dict() for e in events])
        # Raw secret must not appear in the recorded evidence summary/data.
        self.assertNotIn("abc123", blob)


class DefaultBuiltinCheckTests(unittest.TestCase):
    """Portable built-in checks: advisory, dependency-light, skip when their
    precondition is absent, never block."""

    def setUp(self):
        self.repo = _Repo()

    def tearDown(self):
        self.repo.cleanup()

    def test_default_config_enables_builtin_checks(self):
        from nexskill.contracts import DEFAULT_BUILTIN_CHECKS

        cfg = default_config("demo")
        self.assertEqual(tuple(cfg.default_checks), DEFAULT_BUILTIN_CHECKS)

    def test_builtins_run_and_do_not_block_on_clean_repo(self):
        cfg = self.repo.add_config()  # default_config -> default_checks enabled
        result = proof.run_checks(self.repo.root, config=cfg)
        ids = [c.id for c in result.checks]
        for cid in ("skills-valid", "report-hygiene", "git-clean"):
            self.assertIn(cid, ids)
        # advisory only: no blockers, status not failed
        self.assertEqual(result.blockers, [])
        self.assertNotEqual(result.status, "failed")

    def test_git_clean_skips_when_not_a_repo(self):
        cfg = self.repo.add_config()
        result = proof.run_checks(self.repo.root, config=cfg)
        git = next(c for c in result.checks if c.id == "git-clean")
        self.assertEqual(git.status, "skipped")
        self.assertFalse(git.required)

    def test_skills_valid_warns_on_broken_manifest(self):
        # Drop an invalid skill package so the registry skips it.
        cfg = self.repo.add_config()
        bad = self.repo.root / ".nexskill" / "skills" / "broken"
        bad.mkdir(parents=True, exist_ok=True)
        (bad / "manifest.json").write_text("{not valid", encoding="utf-8")
        result = proof.run_checks(self.repo.root, config=cfg)
        sv = next(c for c in result.checks if c.id == "skills-valid")
        self.assertEqual(sv.status, "warning")
        self.assertFalse(sv.required)
        # warning, never a blocker
        self.assertNotIn("skills-valid", " ".join(result.blockers))

    def test_unknown_builtin_is_skipped_not_fatal(self):
        from nexskill.contracts import (
            CONFIG_SCHEMA_VERSION,
            ProjectConfig,
            SkillSource,
        )

        cfg = ProjectConfig(
            schema_version=CONFIG_SCHEMA_VERSION,
            project_name="demo",
            skill_sources=[SkillSource(type="local", path=".nexskill/skills")],
            checks=[],
            default_checks=["does-not-exist"],
            policies={"product_name": "NexSkill", "forbid_source_names_in_reports": True},
        )
        self.repo.write_config(cfg)
        result = proof.run_checks(self.repo.root, config=cfg)
        unknown = next(c for c in result.checks if c.id == "does-not-exist")
        self.assertEqual(unknown.status, "skipped")
        self.assertEqual(result.blockers, [])


class LatencyEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.repo = _Repo()

    def tearDown(self):
        self.repo.cleanup()

    def test_closeout_records_duration_when_supplied(self):
        self.repo.add_config()
        proof.closeout(self.repo.root, duration_ms=7)
        ev = proof.read_evidence(self.repo.root)[-1]
        self.assertEqual(ev.data.get("duration_ms"), 7)

    def test_plan_records_duration_when_supplied(self):
        proof.record_plan(self.repo.root, {"steps": [{}], "stages": ["planning"]}, duration_ms=3)
        ev = proof.read_evidence(self.repo.root)[-1]
        self.assertEqual(ev.data.get("duration_ms"), 3)

    def test_duration_omitted_when_absent(self):
        self.repo.add_config()
        proof.closeout(self.repo.root)
        ev = proof.read_evidence(self.repo.root)[-1]
        self.assertNotIn("duration_ms", ev.data)


class InitPlanEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.repo = _Repo()

    def tearDown(self):
        self.repo.cleanup()

    def test_record_init_and_plan_events(self):
        proof.record_init(self.repo.root, "demo")
        proof.record_plan(self.repo.root, {"steps": [{}, {}], "stages": ["planning"]})
        events = proof.read_evidence(self.repo.root)
        ops = [e.op for e in events]
        self.assertEqual(ops, ["init", "plan"])


if __name__ == "__main__":
    unittest.main()
