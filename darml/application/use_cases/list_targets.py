from dataclasses import dataclass

from darml.domain.models import Target
from darml.domain.targets import list_targets


@dataclass
class ListTargets:
    def execute(self) -> list[Target]:
        return list_targets()
