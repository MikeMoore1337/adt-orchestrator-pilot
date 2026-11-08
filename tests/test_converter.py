"""Baseline tests. Codex adds more tests while resolving Issues."""

import unittest

from converter import ensure_temperature, to_fahrenheit


class BaseConverterTests(unittest.TestCase):
    def test_accepts_finite_number(self):
        self.assertEqual(20.0, ensure_temperature(20))

    def test_rejects_bool(self):
        with self.assertRaises(TypeError):
            ensure_temperature(True)

    def test_rejects_nan(self):
        with self.assertRaises(ValueError):
            ensure_temperature(float("nan"))


class FahrenheitTests(unittest.TestCase):
    def test_converts_celsius(self):
        for celsius, fahrenheit in ((0, 32), (100, 212), (-40, -40)):
            with self.subTest(celsius=celsius):
                self.assertEqual(fahrenheit, to_fahrenheit(celsius))

    def test_rejects_invalid_input(self):
        for value, error in ((True, TypeError), (float("nan"), ValueError),
                             (float("inf"), ValueError), (float("-inf"), ValueError)):
            with self.subTest(value=value), self.assertRaises(error):
                to_fahrenheit(value)


if __name__ == "__main__":
    unittest.main()
