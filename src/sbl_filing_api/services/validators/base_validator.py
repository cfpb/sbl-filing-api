import pkgutil
import importlib

from abc import ABC, abstractmethod


class ActionValidator(ABC):
    """
    Abstract Callable class for action validations, __subclasses__ method leveraged to construct a registry
    """

    name: str

    def __init__(self, name: str):
        super().__init__()
        self.name = name

    @abstractmethod
    def __call__(self, *args, **kwargs): ...


_validation_registry = None


def get_validation_registry():
    # use package reflection to import all subclasses of the base ActionValidator under the current
    # package so that __subclasses__ can find loaded subs.  Do this once to keep subsequent requests
    # from being impacted in performance.
    global _validation_registry
    if not _validation_registry:
        package = __package__
        p = importlib.import_module(package)
        for _, module_name, is_pkg in pkgutil.iter_modules(p.__path__):
            if module_name not in __name__:
                importlib.import_module(f"{package}.{module_name}")
        _validation_registry = {
            validator.name: validator for validator in {Validator() for Validator in ActionValidator.__subclasses__()}
        }

    return _validation_registry
