from typing import Any, Generic, Self, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class BaseModelMeta(type(BaseModel)):
    """
    Custom metaclass that controls model behavior.
    """

    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ):
        """
        Create a new Pydantic response model class.
        """
        config: dict = {
            "from_attributes": True,
            "exclude_none": False,
            "extra": "ignore",
            "validate_assignment": True,
            "validate_default": True,
            "populate_by_name": True,
            "str_strip_whitespace": True,
            "str_min_length": None,
            "str_max_length": None,
            "use_enum_values": True,
            "arbitrary_types_allowed": False,
            "frozen": False,
        }

        for key, value in config.items():
            config[key] = namespace.pop(f"{key:_^{len(key)+4}}", value)

        namespace.setdefault(
            "model_config",
            ConfigDict(**config),
        )

        obj = super().__new__(
            cls,
            name,
            bases,
            namespace,
            **kwargs,
        )

        return obj
