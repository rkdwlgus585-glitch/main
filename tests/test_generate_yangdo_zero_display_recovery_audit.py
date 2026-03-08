import json
import tempfile
import unittest
from pathlib import Path

from scripts.generate_yangdo_zero_display_recovery_audit import build_yangdo_zero_display_recovery_audit


class GenerateYangdoZeroDisplayRecoveryAuditTests(unittest.TestCase):
    def _write_common_inputs(self, base: Path, lane_id: str) -> tuple[Path, Path, Path, Path, Path, Path, Path]:
        comparable = base / "comparable.json"
        bridge = base / "bridge.json"
        service_copy = base / "service_copy.json"
        ux = base / "ux.json"
        contract = base / "contract.json"
        brainstorm = base / "brainstorm.json"
        attorney = base / "attorney.json"

        comparable.write_text(json.dumps({"records_zero_display": 4}, ensure_ascii=False), encoding="utf-8")
        bridge.write_text(
            json.dumps(
                {
                    "public_summary_contract": {
                        "primary_cta": {"target": "/mna-market"},
                    },
                    "market_bridge_policy": {
                        "service_flow_policy": "public_summary_then_market_or_consult",
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        service_copy.write_text(
            json.dumps(
                {
                    "summary": {
                        "low_precision_consult_first_ready": True,
                    },
                    "cta_ladder": {
                        "primary_market_bridge": {"target": "/mna-market"},
                        "secondary_consult": {"target": "/consult?intent=yangdo"},
                    },
                    "zero_display_recovery_policy": {
                        "policy_ready": True,
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        ux.write_text(
            json.dumps(
                {
                    "consult_detail_experience": {
                        "allowed_offerings": ["yangdo_pro"],
                        "detail_axes": ["matched_axes", "mismatch_flags"],
                    }
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        contract.write_text(json.dumps({"summary": {"contract_ok": True}}, ensure_ascii=False), encoding="utf-8")
        brainstorm.write_text(
            json.dumps(
                {
                    "summary": {"zero_recovery_ready": True},
                    "current_execution_lane": {"id": lane_id},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        attorney.write_text(
            json.dumps(
                {
                    "tracks": [
                        {
                            "track_id": "A",
                            "attorney_position": {
                                "claim_focus": ["fallback 공개 등급 제어", "시장 브리지와 상담 상세 제어"],
                                "commercial_positioning": ["추천 요약 카드와 시장 브리지 fallback 계약"],
                            },
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return comparable, bridge, service_copy, ux, contract, brainstorm, attorney

    def test_build_audit_requires_market_bridge_consult_and_patent_hook(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            comparable, bridge, service_copy, ux, contract, brainstorm, attorney = self._write_common_inputs(
                base, "zero_display_recovery_guard"
            )

            payload = build_yangdo_zero_display_recovery_audit(
                comparable_path=comparable,
                bridge_path=bridge,
                service_copy_path=service_copy,
                ux_path=ux,
                contract_path=contract,
                brainstorm_path=brainstorm,
                attorney_path=attorney,
            )

            self.assertTrue(payload["summary"]["packet_ready"])
            self.assertEqual(payload["summary"]["zero_display_total"], 4)
            self.assertTrue(payload["summary"]["selected_lane_ok"])
            self.assertTrue(payload["summary"]["selected_lane_guard_ok"])
            self.assertTrue(payload["summary"]["runtime_ready"])
            self.assertTrue(payload["summary"]["market_bridge_route_ok"])
            self.assertTrue(payload["summary"]["consult_first_ready"])
            self.assertTrue(payload["summary"]["patent_hook_ready"])
            self.assertTrue(payload["summary"]["zero_display_guard_ok"])

    def test_build_audit_keeps_guard_ready_true_after_lane_advances(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            comparable, bridge, service_copy, ux, contract, brainstorm, attorney = self._write_common_inputs(
                base, "public_language_normalization"
            )

            payload = build_yangdo_zero_display_recovery_audit(
                comparable_path=comparable,
                bridge_path=bridge,
                service_copy_path=service_copy,
                ux_path=ux,
                contract_path=contract,
                brainstorm_path=brainstorm,
                attorney_path=attorney,
            )

            self.assertFalse(payload["summary"]["selected_lane_ok"])
            self.assertFalse(payload["summary"]["selected_lane_guard_ok"])
            self.assertTrue(payload["summary"]["zero_display_guard_ok"])


if __name__ == "__main__":
    unittest.main()
