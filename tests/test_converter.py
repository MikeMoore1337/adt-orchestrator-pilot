"""Baseline tests. Codex adds more tests while resolving Issues."""

import math
import unittest

from converter import ensure_temperature, from_kelvin, to_celsius, to_fahrenheit, to_kelvin


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


class KelvinTests(unittest.TestCase):
    def test_converts_celsius(self):
        for celsius, kelvin in ((0, 273.15), (-273.15, 0), (100, 373.15),
                                (-40, 233.15), (37.5, 310.65)):
            with self.subTest(celsius=celsius):
                result = to_kelvin(celsius)
                self.assertIsInstance(result, float)
                self.assertAlmostEqual(kelvin, result)

    def test_rejects_below_absolute_zero(self):
        for value in (-274, math.nextafter(-273.15, -math.inf)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                to_kelvin(value)

    def test_accepts_just_above_absolute_zero(self):
        self.assertGreater(to_kelvin(math.nextafter(-273.15, math.inf)), 0)

    def test_rejects_invalid_input(self):
        for value, error in ((True, TypeError), (False, TypeError),
                             ("0", TypeError), (None, TypeError),
                             (1j, TypeError), (float("nan"), ValueError),
                             (float("inf"), ValueError), (float("-inf"), ValueError)):
            with self.subTest(value=value), self.assertRaises(error):
                to_kelvin(value)


class FromKelvinTests(unittest.TestCase):
    def test_converts_kelvin(self):
        for kelvin, celsius in ((0, -273.15), (273.15, 0), (373.15, 100),
                                (233.15, -40), (310.65, 37.5)):
            with self.subTest(kelvin=kelvin):
                result = from_kelvin(kelvin)
                self.assertIsInstance(result, float)
                self.assertAlmostEqual(celsius, result)

    def test_rejects_negative_kelvin(self):
        for value in (-1, -273.15, math.nextafter(0.0, -math.inf)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                from_kelvin(value)

    def test_roundtrips_both_directions(self):
        for celsius in (-273.15, -40, 0, 37.5, 100):
            with self.subTest(celsius=celsius):
                self.assertAlmostEqual(celsius, from_kelvin(to_kelvin(celsius)))
        for kelvin in (0, 1, 233.15, 273.15, 310.65, 373.15):
            with self.subTest(kelvin=kelvin):
                self.assertAlmostEqual(kelvin, to_kelvin(from_kelvin(kelvin)))

    def test_rejects_invalid_input(self):
        for value, error in ((True, TypeError), (False, TypeError),
                             ("0", TypeError), (None, TypeError),
                             (1j, TypeError), (float("nan"), ValueError),
                             (float("inf"), ValueError), (float("-inf"), ValueError)):
            with self.subTest(value=value), self.assertRaises(error):
                from_kelvin(value)


if __name__ == "__main__":
    unittest.main()
