from app.modules.converter.base import ConversionModule

_registry: dict[str, ConversionModule] = {}


def register_converter(module: ConversionModule) -> None:
    """Register a conversion module instance by its slug."""
    _registry[module.slug] = module


def get_converter(slug: str) -> ConversionModule | None:
    return _registry.get(slug)


def list_converters() -> list[ConversionModule]:
    return list(_registry.values())
