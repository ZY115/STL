"""Review-packet coverage checks that do not perform human review."""

from __future__ import annotations

import unittest
import json
from pathlib import Path

from safety_stl.stage2_review import render_review_packet


class Stage2ReviewPacketTests(unittest.TestCase):
    def test_packet_contains_every_pending_record_and_no_approval_claim(self) -> None:
        root = Path(__file__).resolve().parents[1] / "benchmarks/stage2_v0"
        packet = render_review_packet(root)
        reviews = json.loads((root / "reviews.json").read_text(encoding="utf-8"))
        pending = [row["spec_id"] for row in reviews if row["status"] != "approved"]
        self.assertIn(f"{len(pending)} pending / 40 total", packet)
        self.assertEqual(packet.count("Reviewer name: ____________________"), len(pending))
        for spec_id in pending:
            self.assertIn(f"`{spec_id}`", packet)
        self.assertNotIn("independently reviewed by Codex", packet)


if __name__ == "__main__":
    unittest.main()
