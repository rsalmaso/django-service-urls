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

from collections.abc import Callable, Mapping, MutableMapping
from typing import Any, TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from .base import Service

__all__ = [
    "CastValue",
    "CastValues",
    "ConfigDict",
    "ConfigInput",
    "ConfigRegistry",
    "OptionValue",
    "Options",
    "ServiceCallback",
]


CastValue: TypeAlias = int | bool | str | None
CastValues: TypeAlias = list[CastValue] | CastValue
OptionValue: TypeAlias = "CastValues | Options"
Options: TypeAlias = dict[str, "OptionValue"]

ConfigDict: TypeAlias = MutableMapping[str, Any]  # pyrefly: ignore[explicit-any]
ConfigInput: TypeAlias = Mapping[str, str | ConfigDict]
ConfigRegistry: TypeAlias = MutableMapping[str, ConfigDict]
ServiceCallback: TypeAlias = Callable[["Service", str, str, str], ConfigDict]
