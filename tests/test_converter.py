"""Baseline tests. Codex adds more tests while resolving Issues."""

import unittest

from converter import ensure_temperature, to_celsius, to_fahrenheit


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


class CelsiusTests(unittest.TestCase):
    def test_converts_fahrenheit(self):
        for fahrenheit, celsius in ((32, 0), (212, 100), (-40, -40)):
            with self.subTest(fahrenheit=fahrenheit):
                self.assertEqual(celsius, to_celsius(fahrenheit))

    def test_roundtrips_both_directions(self):
        for value in (-40, 0, 37.5, 100):
            with self.subTest(value=value):
                self.assertAlmostEqual(value, to_celsius(to_fahrenheit(value)))
                self.assertAlmostEqual(value, to_fahrenheit(to_celsius(value)))

    def test_rejects_invalid_input(self):
        for value, error in ((True, TypeError), (float("nan"), ValueError),
                             (float("inf"), ValueError), (float("-inf"), ValueError)):
            with self.subTest(value=value), self.assertRaises(error):
                to_celsius(value)


if __name__ == "__main__":
    unittest.main()
