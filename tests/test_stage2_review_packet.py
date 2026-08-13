"""Review-packet coverage checks that do not perform human review."""

from __future__ import annotations

import unittest
from pathlib import Path

from safety_stl.stage2_review import render_review_packet


class Stage2ReviewPacketTests(unittest.TestCase):
    def test_packet_contains_every_pending_record_and_no_approval_claim(self) -> None:
        root = Path(__file__).resolve().parents[1] / "benchmarks/stage2_v0"
        packet = render_review_packet(root)
        self.assertIn("35 pending / 40 total", packet)
        self.assertEqual(packet.count("Reviewer name: ____________________"), 35)
        self.assertIn("`or-v0-008`", packet)
        self.assertNotIn("independently reviewed by Codex", packet)


if __name__ == "__main__":
    unittest.main()
