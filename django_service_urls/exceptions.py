# Copyright (C) Raffaele Salmaso <raffaele@salmaso.org>
# Copyright (C) Tom Forbes
# Copyright (C) Kenneth Reitz
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

from __future__ import annotations

from collections.abc import Mapping
from typing import Generator, TypeAlias, Union

__all__ = ["ValidationError"]

# Type alias for ValidationError message parameter
ErrorMessageMapping: TypeAlias = Mapping[str, Union[str, "ValidationError", object]]
ErrorMessage: TypeAlias = Union[str, ErrorMessageMapping, "ValidationError"]


class ValidationError(ValueError):
    def __init__(self, message: ErrorMessage) -> None:
        """
        Initialize a ValidationError with error message or error dictionary.

        The `message` argument can be:
        - A single error string: Creates a simple error with .message attribute
        - A dictionary mapping keys to errors: Creates .error_dict attribute
        - Another ValidationError instance: Extracts its error or error_dict

        Args:
            message: Error message as string, key->error dict, or ValidationError instance

        Examples:
            >>> ValidationError("Simple error")
            ValidationError('Simple error')

            >>> nested = ValidationError("Nested error")
            >>> ValidationError(nested)
            ValidationError('Nested error')

            >>> ValidationError({"field1": "Error 1", "field2": "Error 2"})
            ValidationError({'field1': 'Error 1', 'field2': 'Error 2'})

            >>> ValidationError({"field1": ValidationError("Error 1"), "field2": ValidationError("Error 2")})
            ValidationError({'field1': 'Error 1', 'field2': 'Error 2'})
        """
        self.error_dict: dict[str, Union[str, "ValidationError"]]
        self.message: str

        if isinstance(message, ValidationError):
            if hasattr(message, "error_dict"):
                self.error_dict = message.error_dict.copy()
            else:
                self.message = message.message
        elif isinstance(message, dict):
            self.error_dict = {}
            for key, value in message.items():
                if isinstance(value, ValidationError):
                    self.error_dict[key] = value.message
                else:
                    # value is a string
                    self.error_dict[key] = value
        elif isinstance(message, str):
            self.message = message

    def __str__(self) -> str:
        if hasattr(self, "error_dict"):
            return repr(self.error_dict)
        return repr(self.message)

    def __repr__(self) -> str:
        return f"ValidationError({self})"

    def __iter__(self) -> Generator[Union[tuple[str, str], str], None, None]:
        if hasattr(self, "error_dict"):
            for key, message in self.error_dict.items():
                yield key, str(message)
        else:
            yield self.message
