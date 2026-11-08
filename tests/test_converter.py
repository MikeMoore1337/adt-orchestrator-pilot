"""Baseline tests. Codex adds more tests while resolving Issues."""

import unittest

from converter import ensure_temperature


class BaseConverterTests(unittest.TestCase):
    def test_accepts_finite_number(self):
        self.assertEqual(20.0, ensure_temperature(20))

    def test_rejects_bool(self):
        with self.assertRaises(TypeError):
            ensure_temperature(True)

    def test_rejects_nan(self):
        with self.assertRaises(ValueError):
            ensure_temperature(float("nan"))


if __name__ == "__main__":
    unittest.main()
