#!/usr/bin/env python3

import unittest

from apply_audit_notes import detected_notes


class AuditNoteTests(unittest.TestCase):
  def test_possible_note_accepts_source_wording(self) -> None:
    notes = detected_notes([
      "某件事“可能”发生，代表说书人决定该事情是否发生。",
    ])

    self.assertEqual(len(notes), 1)
    self.assertEqual(
      notes[0]["text"],
      "可能：某件事“可能”发生，代表说书人决定该事情是否发生。",
    )

  def test_possible_note_accepts_longer_noun(self) -> None:
    notes = detected_notes([
      "某件事情“可能”发生，代表由说书人来决定该事情是否发生。",
    ])

    self.assertEqual(len(notes), 1)


if __name__ == "__main__":
  unittest.main()
