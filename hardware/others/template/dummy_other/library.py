"""
AURA Other Library: Dummy Template Other Device
===============================================
"""

class TemplateOtherLibrary:
    LABEL = "Template Other Device"
    
    def __init__(self, **kwargs):
        self.params = kwargs

    def initialize(self) -> bool:
        return True

    def run_action(self) -> None:
        pass
