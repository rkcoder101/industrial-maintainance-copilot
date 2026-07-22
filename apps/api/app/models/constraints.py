from enum import StrEnum


def enum_values(enum_type: type[StrEnum]) -> tuple[str, ...]:
    return tuple(item.value for item in enum_type)


def enum_check(column_name: str, enum_type: type[StrEnum]) -> str:
    values = ", ".join(f"'{value}'" for value in enum_values(enum_type))
    return f"{column_name} in ({values})"
