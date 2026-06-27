"""
AURA Generic Other Library: Template Category
============================================
"""
from hardware.utils import get_active_driver, load_specific_driver

class TemplateOther:
    LABEL = "Template"
    
    def __init__(self, **kwargs):
        driver, params = get_active_driver("template")
        if driver == "template":
            driver = "dummy_other"
        merged_params = {**params, **kwargs}
        driver_cls = load_specific_driver("others", "template", driver)
        try:
            self._delegate = driver_cls(**merged_params)
        except TypeError:
            self._delegate = driver_cls()

    def initialize(self) -> bool:
        if hasattr(self._delegate, "initialize"):
            return self._delegate.initialize()
        return True

    def run_action(self) -> None:
        if hasattr(self._delegate, "run_action"):
            self._delegate.run_action()
        else:
            raise AttributeError("Template other driver has no run_action method")

# Module-level convenience functions using a default global instance
_default_other = None

def _get_default_other():
    global _default_other
    if _default_other is None:
        _default_other = TemplateOther()
        _default_other.initialize()
    return _default_other

def initialize() -> bool:
    return _get_default_other().initialize()

def run_action() -> None:
    _get_default_other().run_action()
