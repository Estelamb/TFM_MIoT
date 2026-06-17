"""
AURA Other Library: Dummy Template Other Device
===============================================
"""
LABEL = "Template Other Device"

class TemplateOtherLibrary:
    def __init__(self, **kwargs):
        self.params = kwargs

    def initialize(self) -> bool:
        return True

    def run_action(self) -> None:
        pass
