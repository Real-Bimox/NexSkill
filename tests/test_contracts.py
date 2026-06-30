"""Lane A - Core Contracts tests.

Boundary validation for the JSON envelope, skill manifests, project config, and
evidence events. A malformed contract must fail with a stable error code and
never reach the registry / planner / reporter.
"""

from __future__ import annotations

import unittest

from nexskill.contracts import (
    CONFIG_SCHEMA_VERSION,
    EVIDENCE_SCHEMA_VERSION,
    ENVELOPE_SCHEMA_VERSION,
    PRODUCT_NAME,
    SKILL_SCHEMA_VERSION,
    CheckConfig,
    CheckOutcome,
    CheckResult,
    EvidenceEvent,
    NexSkillError,
    PlanResult,
    PlanStep,
    ProjectConfig,
    SkillManifest,
    SkillSource,
    default_config,
    error_envelope,
    success_envelope,
)


def _manifest(**overrides):
    base = {
        "schema_version": SKILL_SCHEMA_VERSION,
        "id": "planning.task-breakdown",
        "name": "Task Breakdown",
        "summary": "Breaks a development request into verifiable tasks.",
        "stages": ["planning"],
        "inputs": ["task_request"],
        "outputs": ["implementation_plan"],
        "depends_on": [],
        "conflicts_with": [],
        "tags": ["development", "planning"],
        "entrypoint": "SKILL.md",
    }
    base.update(overrides)
    return base


class EnvelopeTests(unittest.TestCase):
    def test_success_envelope_shape(self):
        env = success_envelope("plan", {"task": "x"})
        self.assertEqual(env["ok"], True)
        self.assertEqual(env["schema_version"], ENVELOPE_SCHEMA_VERSION)
        self.assertEqual(env["op"], "plan")
        self.assertEqual(env["result"], {"task": "x"})

    def test_error_envelope_shape(self):
        err = NexSkillError("CONFIG_MISSING", "Run nexskill init first.", {"hint": "see docs"})
        env = error_envelope("plan", err)
        self.assertEqual(env["ok"], False)
        self.assertEqual(env["schema_version"], ENVELOPE_SCHEMA_VERSION)
        self.assertEqual(env["op"], "plan")
        self.assertEqual(env["error"]["code"], "CONFIG_MISSING")
        self.assertEqual(env["error"]["message"], "Run nexskill init first.")
        self.assertEqual(env["error"]["details"], {"hint": "see docs"})

    def test_error_envelope_omits_empty_details(self):
        err = NexSkillError("PLAN_FAILED", "no skills")
        env = error_envelope("plan", err)
        self.assertNotIn("details", env["error"])

    def test_error_code_must_be_upper_snake(self):
        err = NexSkillError("bad code", "msg")
        with self.assertRaises(ValueError):
            error_envelope("plan", err)


class ManifestValidationTests(unittest.TestCase):
    def test_valid_manifest_parses(self):
        m = SkillManifest.from_dict(_manifest())
        self.assertEqual(m.id, "planning.task-breakdown")
        self.assertEqual(m.stages, ["planning"])
        self.assertEqual(m.tags, ["development", "planning"])

    def test_minimal_manifest_with_only_required_fields(self):
        raw = {
            "schema_version": SKILL_SCHEMA_VERSION,
            "id": "a-b",
            "name": "A B",
            "summary": "summary text",
            "stages": ["planning"],
            "entrypoint": "SKILL.md",
        }
        m = SkillManifest.from_dict(raw)
        self.assertEqual(m.inputs, [])
        self.assertEqual(m.depends_on, [])
        self.assertEqual(m.unknown, {})

    def test_wrong_schema_version_rejected(self):
        with self.assertRaises(NexSkillError) as ctx:
            SkillManifest.from_dict(_manifest(schema_version="nope"))
        self.assertEqual(ctx.exception.code, "SKILL_INVALID")

    def test_missing_required_field_rejected(self):
        raw = _manifest()
        raw.pop("summary")
        with self.assertRaises(NexSkillError) as ctx:
            SkillManifest.from_dict(raw)
        self.assertIn("summary", ctx.exception.message)
        self.assertEqual(ctx.exception.code, "SKILL_INVALID")

    def test_empty_required_field_rejected(self):
        with self.assertRaises(NexSkillError) as ctx:
            SkillManifest.from_dict(_manifest(name="   "))
        self.assertEqual(ctx.exception.code, "SKILL_INVALID")

    def test_invalid_id_rejected(self):
        for bad in ("UPPER", "1 odd", "has space", "with/slash", "äß"):
            with self.assertRaises(NexSkillError) as ctx:
                SkillManifest.from_dict(_manifest(id=bad))
            self.assertEqual(ctx.exception.code, "SKILL_INVALID", msg=bad)

    def test_stages_must_be_non_empty_list(self):
        with self.assertRaises(NexSkillError):
            SkillManifest.from_dict(_manifest(stages=[]))
        with self.assertRaises(NexSkillError):
            SkillManifest.from_dict(_manifest(stages="planning"))

    def test_unknown_fields_preserved_not_interpreted(self):
        raw = _manifest(extra_future_field={"x": 1})
        m = SkillManifest.from_dict(raw)
        self.assertEqual(m.unknown, {"extra_future_field": {"x": 1}})

    def test_to_index_dict_is_deterministic_and_body_free(self):
        m = SkillManifest.from_dict(_manifest())
        d = m.to_index_dict()
        self.assertEqual(list(d.keys()), list(m.to_index_dict().keys()))
        self.assertNotIn("body", d)
        self.assertNotIn("unknown", d)


class ConfigValidationTests(unittest.TestCase):
    def _config(self, **overrides):
        base = {
            "schema_version": CONFIG_SCHEMA_VERSION,
            "project_name": "example",
            "skill_sources": [{"type": "local", "path": ".nexskill/skills"}],
            "checks": [
                {"id": "tests", "command": "configured-test-command", "required": True}
            ],
            "policies": {"product_name": PRODUCT_NAME, "forbid_source_names_in_reports": True},
        }
        base.update(overrides)
        return base

    def test_valid_config_parses(self):
        cfg = ProjectConfig.from_dict(self._config())
        self.assertEqual(cfg.project_name, "example")
        self.assertEqual(len(cfg.skill_sources), 1)
        self.assertEqual(cfg.checks[0].id, "tests")
        self.assertTrue(cfg.checks[0].required)

    def test_optional_check_defaults_required_true(self):
        raw = self._config()
        raw["checks"] = [{"id": "lint", "command": "lint"}]
        cfg = ProjectConfig.from_dict(raw)
        self.assertTrue(cfg.checks[0].required)

    def test_wrong_schema_rejected(self):
        with self.assertRaises(NexSkillError) as ctx:
            ProjectConfig.from_dict(self._config(schema_version="old"))
        self.assertEqual(ctx.exception.code, "CONFIG_INVALID")

    def test_missing_project_name_rejected(self):
        with self.assertRaises(NexSkillError):
            ProjectConfig.from_dict(self._config(project_name=""))

    def test_non_local_source_rejected(self):
        with self.assertRaises(NexSkillError) as ctx:
            ProjectConfig.from_dict(
                self._config(skill_sources=[{"type": "remote", "path": "x"}])
            )
        self.assertEqual(ctx.exception.code, "CONFIG_INVALID")

    def test_round_trip_to_dict(self):
        cfg = ProjectConfig.from_dict(self._config())
        again = ProjectConfig.from_dict(cfg.to_dict())
        self.assertEqual(again.project_name, cfg.project_name)
        self.assertEqual(again.checks[0].command, cfg.checks[0].command)

    def test_default_config_is_safe_and_valid(self):
        cfg = default_config("demo")
        # Round-trips through validation.
        again = ProjectConfig.from_dict(cfg.to_dict())
        self.assertEqual(again.project_name, "demo")
        self.assertEqual(again.policies["product_name"], PRODUCT_NAME)
        self.assertEqual(again.checks, [])


class EvidenceTests(unittest.TestCase):
    def _event(self, **overrides):
        base = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "event_id": "evt-1",
            "op": "check",
            "status": "passed",
            "timestamp": "2026-06-30T00:00:00Z",
            "summary": "Configured checks passed.",
            "data": {"n": 1},
        }
        base.update(overrides)
        return base

    def test_valid_event_parses_and_round_trips(self):
        ev = EvidenceEvent.from_dict(self._event())
        self.assertEqual(ev.op, "check")
        again = EvidenceEvent.from_dict(ev.to_dict())
        self.assertEqual(again.event_id, ev.event_id)

    def test_wrong_schema_rejected(self):
        with self.assertRaises(NexSkillError) as ctx:
            EvidenceEvent.from_dict(self._event(schema_version="x"))
        self.assertEqual(ctx.exception.code, "EVIDENCE_INVALID")

    def test_invalid_op_rejected(self):
        with self.assertRaises(NexSkillError):
            EvidenceEvent.from_dict(self._event(op="deploy"))

    def test_invalid_status_rejected(self):
        with self.assertRaises(NexSkillError):
            EvidenceEvent.from_dict(self._event(status="green"))


class ResultShapeTests(unittest.TestCase):
    def test_plan_result_to_dict(self):
        pr = PlanResult(
            task="t",
            stages=["planning"],
            steps=[PlanStep("a", "A", "sum", "planning", "r")],
            conflicts=[{"a": "b"}],
            warnings=["w"],
        )
        d = pr.to_dict()
        self.assertEqual(d["task"], "t")
        self.assertEqual(d["steps"][0]["skill_id"], "a")

    def test_check_result_to_dict(self):
        cr = CheckResult(
            op="check",
            status="passed",
            checks=[CheckOutcome("tests", "cmd", True, "passed", "ok")],
            blockers=[],
            warnings=[],
        )
        d = cr.to_dict()
        self.assertEqual(d["status"], "passed")
        self.assertEqual(d["checks"][0]["status"], "passed")


class NoCliDependencyTests(unittest.TestCase):
    def test_contracts_module_imports_without_cli(self):
        # contracts.py must not import the CLI or any rendering module.
        import nexskill.contracts as mod
        with open(mod.__file__, encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("import nexskill.cli", src)
        self.assertNotIn("argparse", src)


if __name__ == "__main__":
    unittest.main()
