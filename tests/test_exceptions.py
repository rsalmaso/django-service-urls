# Copyright (C) Raffaele Salmaso <raffaele@salmaso.org>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDERS OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
# THE POSSIBILITY OF SUCH DAMAGE.

import unittest

from django_service_urls.exceptions import ValidationError


class ValidationErrorTestCase(unittest.TestCase):
    """Test cases for ValidationError exception class."""

    def test_single_string_message(self) -> None:
        error = ValidationError("This is an error")

        self.assertEqual(error.message, "This is an error")
        self.assertFalse(hasattr(error, "error_dict"))
        self.assertEqual(str(error), "'This is an error'")
        self.assertEqual(repr(error), "ValidationError('This is an error')")

    def test_dict_of_key_errors(self) -> None:
        error_dict = {
            "key1": "Error in key 1",
            "key2": "Error in key 2",
            "key3": "Error in key 3",
        }
        error = ValidationError(error_dict)

        self.assertTrue(hasattr(error, "error_dict"))
        self.assertFalse(hasattr(error, "message"))
        self.assertEqual(len(error.error_dict), 3)

        self.assertEqual(error.error_dict, error_dict)

    def test_dict_with_parse_error_values(self) -> None:
        nested_error = ValidationError("Nested error message")
        error_dict = {
            "key1": "Simple string error",
            "key2": nested_error,
        }
        error = ValidationError(error_dict)

        self.assertTrue(hasattr(error, "error_dict"))
        self.assertEqual(len(error.error_dict), 2)
        self.assertEqual(error.error_dict, {"key1": "Simple string error", "key2": "Nested error message"})

    def test_nested_parse_error_with_message(self) -> None:
        original_error = ValidationError("Original error")
        nested_error = ValidationError(original_error)

        self.assertEqual(nested_error.message, "Original error")
        self.assertFalse(hasattr(nested_error, "error_dict"))

    def test_nested_parse_error_with_dict(self) -> None:
        original_error = ValidationError({"key1": "Error 1", "key2": "Error 2"})
        nested_error = ValidationError(original_error)

        self.assertTrue(hasattr(nested_error, "error_dict"))
        self.assertFalse(hasattr(nested_error, "message"))
        self.assertEqual(len(nested_error.error_dict), 2)
        self.assertEqual(nested_error.error_dict, {"key1": "Error 1", "key2": "Error 2"})

    def test_iteration_with_simple_message(self) -> None:
        error = ValidationError("Simple error")

        # Should yield the message directly
        items = list(error)
        self.assertEqual(items, ["Simple error"])

    def test_iteration_with_error_dict(self) -> None:
        error_dict = {"key1": "Error 1", "key2": "Error 2", "key3": "Error 3"}
        error = ValidationError(error_dict)

        items = list(error)
        expected = [("key1", "Error 1"), ("key2", "Error 2"), ("key3", "Error 3")]
        self.assertEqual(items, expected)

    def test_string_representation_simple_error(self) -> None:
        """Test string representation of simple error."""
        error = ValidationError("Simple error")

        self.assertEqual(str(error), "'Simple error'")
        self.assertEqual(repr(error), "ValidationError('Simple error')")

    def test_string_representation_error_dict(self) -> None:
        """Test string representation of error dict."""
        error_dict = {"key1": "Error 1", "key2": "Error 2"}
        error = ValidationError(error_dict)

        # Should use dict representation
        str_repr = str(error)
        self.assertIn("key1", str_repr)
        self.assertIn("key2", str_repr)
        self.assertIn("Error 1", str_repr)
        self.assertIn("Error 2", str_repr)

        repr_str = repr(error)
        self.assertIn("ValidationError", repr_str)

    def test_empty_dict(self) -> None:
        error = ValidationError({})

        self.assertTrue(hasattr(error, "error_dict"))
        self.assertEqual(len(error.error_dict), 0)

    def test_dict_with_mixed_value_types(self) -> None:
        error = ValidationError(
            {
                "string_key": "String error",
                "parse_error_key": ValidationError("Nested error"),
            }
        )

        self.assertTrue(hasattr(error, "error_dict"))
        self.assertEqual(len(error.error_dict), 2)

        # All values should be converted to message strings
        self.assertEqual(error.error_dict["string_key"], "String error")
        self.assertEqual(error.error_dict["parse_error_key"], "Nested error")

    def test_deeply_nested_parse_errors(self) -> None:
        # Create a chain: inner -> middle -> outer
        inner_error = ValidationError("Inner error message")
        middle_error = ValidationError(inner_error)
        outer_error = ValidationError(middle_error)

        # Should resolve to the innermost message
        self.assertEqual(outer_error.message, "Inner error message")
        self.assertFalse(hasattr(outer_error, "error_dict"))

    def test_nested_dict_extraction(self) -> None:
        outer_error = ValidationError(ValidationError({"inner_key1": "Inner error 1", "inner_key2": "Inner error 2"}))

        self.assertTrue(hasattr(outer_error, "error_dict"))
        self.assertEqual(len(outer_error.error_dict), 2)
        self.assertEqual(outer_error.error_dict["inner_key1"], "Inner error 1")
        self.assertEqual(outer_error.error_dict["inner_key2"], "Inner error 2")

    def test_composition_dict_with_parse_error_values(self) -> None:
        composed_error = ValidationError(
            {
                "database": ValidationError("Database connection failed"),
                "cache": ValidationError("Cache connection timeout"),
                "email": ValidationError("Email service unavailable"),
            }
        )

        self.assertTrue(hasattr(composed_error, "error_dict"))
        self.assertEqual(len(composed_error.error_dict), 3)

        self.assertEqual(
            composed_error.error_dict,
            {
                "database": "Database connection failed",
                "cache": "Cache connection timeout",
                "email": "Email service unavailable",
            },
        )

        str_repr = str(composed_error)
        self.assertIn("database", str_repr)
        self.assertIn("Database connection failed", str_repr)
        self.assertIn("cache", str_repr)
        self.assertIn("Cache connection timeout", str_repr)
        self.assertIn("email", str_repr)
        self.assertIn("Email service unavailable", str_repr)


if __name__ == "__main__":
    unittest.main()
