"""
AURA Actuator Library: Dummy Template Actuator
==============================================
"""

class TemplateActuatorLibrary:
    LABEL = "Template Actuator"
    
    def __init__(self, **kwargs):
        self.params = kwargs

    def initialize(self) -> bool:
        return True

    def write_value(self, value) -> None:
        pass
