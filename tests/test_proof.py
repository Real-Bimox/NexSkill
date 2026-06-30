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
