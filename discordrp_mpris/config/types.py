from __future__ import annotations

import typing

if typing.TYPE_CHECKING:
    from typing import TypeAlias
else:
    TypeAlias = None

TomlScalar: TypeAlias = "str | float | int"  # omits datetimes
TomlValue: TypeAlias = "TomlScalar | dict[str, TomlValue] | list[TomlValue]"
TomlTable: TypeAlias = "dict[str, TomlValue]"
TomlList: TypeAlias = "list[TomlValue]"
