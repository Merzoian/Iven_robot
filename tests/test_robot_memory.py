import os
import tempfile
import threading
import unittest

from robot_memory import (
    apply_memory_from_text,
    clean_phrase,
    load_session_memory,
    save_session_memory,
)


class RobotMemoryTests(unittest.TestCase):
    def setUp(self):
        self.session_memory = {"name": None, "likes": [], "facts": []}
        self.memory_lock = threading.Lock()
        self.save_calls = 0

    def save_callback(self):
        self.save_calls += 1

    def test_clean_phrase_normalizes_spacing_and_punctuation(self):
        cleaned = clean_phrase("  Hello,   Ivan!!!  ")

        self.assertEqual(cleaned, "Hello Ivan")

    def test_apply_memory_extracts_name_like_fact_and_favorite(self):
        text = (
            "My name is Alice. "
            "I like pizza. "
            "Please remember that I have a blue bike. "
            "My favorite color is green."
        )

        apply_memory_from_text(text, self.session_memory, self.save_callback)

        self.assertEqual(self.session_memory["name"], "Alice")
        self.assertIn("pizza", self.session_memory["likes"])
        self.assertIn("that I have a blue bike", self.session_memory["facts"])
        self.assertIn("favorite color is green", self.session_memory["facts"])
        self.assertEqual(self.save_calls, 1)

    def test_apply_memory_does_not_duplicate_existing_entries(self):
        self.session_memory["likes"] = ["pizza"]
        self.session_memory["facts"] = ["favorite color is green"]

        apply_memory_from_text(
            "I like pizza. My favorite color is green.",
            self.session_memory,
            self.save_callback,
        )

        self.assertEqual(self.session_memory["likes"], ["pizza"])
        self.assertEqual(self.session_memory["facts"], ["favorite color is green"])
        self.assertEqual(self.save_calls, 0)

    def test_apply_memory_handles_im_name_variant(self):
        apply_memory_from_text("I'm Carlos", self.session_memory, self.save_callback)

        self.assertEqual(self.session_memory["name"], "Carlos")
        self.assertEqual(self.save_calls, 1)

    def test_save_and_load_round_trip(self):
        self.session_memory["name"] = "Valentina"
        self.session_memory["likes"] = ["robots", "coffee"]
        self.session_memory["facts"] = ["favorite color is green", "has a blue bike"]

        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = os.path.join(tmpdir, "memory.json")
            save_session_memory(self.session_memory, self.memory_lock, memory_path)

            loaded = {"name": None, "likes": [], "facts": []}
            load_session_memory(loaded, self.memory_lock, memory_path)

        self.assertEqual(loaded, self.session_memory)

    def test_load_session_memory_ignores_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = os.path.join(tmpdir, "missing.json")
            load_session_memory(self.session_memory, self.memory_lock, missing_path)

        self.assertEqual(self.session_memory, {"name": None, "likes": [], "facts": []})


if __name__ == "__main__":
    unittest.main()
