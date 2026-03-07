import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_kr_live_operator_checklist import build_kr_live_operator_checklist


class GenerateKrLiveOperatorChecklistTests(unittest.TestCase):
    def test_checklist_is_ready_when_apply_proxy_cutover_and_traffic_gate_are_green(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            live_apply = base / "live_apply.json"
            proxy_matrix = base / "proxy_matrix.json"
            cutover = base / "cutover.json"
            traffic_gate = base / "traffic_gate.json"

            live_apply.write_text(
                json.dumps(
                    {
                        "summary": {"apply_packet_ready": True},
                        "wordpress_steps": [{"step": 1, "area": "backup"}],
                        "server_steps": [{"stack": "nginx"}],
                        "publish_validation": ["Open / and confirm no iframe exists before click."],
                        "rollback_map": {"theme": "restore theme"},
                        "operator_inputs": ["confirm_live_yes"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            proxy_matrix.write_text(json.dumps({"summary": {"cutover_ready": True, "public_mount_path": "/_calc"}}, ensure_ascii=False), encoding="utf-8")
            cutover.write_text(json.dumps({"summary": {"cutover_ready": True}}, ensure_ascii=False), encoding="utf-8")
            traffic_gate.write_text(json.dumps({"decision": {"traffic_leak_blocked": True}}, ensure_ascii=False), encoding="utf-8")

            payload = build_kr_live_operator_checklist(
                live_apply_path=live_apply,
                proxy_matrix_path=proxy_matrix,
                cutover_path=cutover,
                traffic_gate_path=traffic_gate,
            )

            self.assertTrue(payload["summary"]["checklist_ready"])
            self.assertEqual(payload["summary"]["public_mount_path"], "/_calc")
            self.assertEqual(payload["summary"]["operator_input_count"], 1)
            self.assertEqual(payload["summary"]["validation_step_count"], 1)


if __name__ == "__main__":
    unittest.main()
