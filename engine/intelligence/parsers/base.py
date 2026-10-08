"""
Abstract Base Requirement Parser Interface.
"""

from abc import ABC, abstractmethod
from typing import List
from engine.intelligence.models import RequirementSpec


class BaseRequirementParser(ABC):
    @abstractmethod
    def parse(self, content: str, project_id: str, document_id: str) -> List[RequirementSpec]:
        """Parses document content deterministically into a list of RequirementSpec objects."""
        pass
