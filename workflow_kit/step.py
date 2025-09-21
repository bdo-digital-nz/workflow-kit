__all__ = ['Step']

from dataclasses import dataclass
from typing import Callable, List, Dict, Any

from workflow_kit.types import Decorator


@dataclass
class Step:
    func: Callable
    name: str
    decorators: List[Decorator]
    kwargs: Dict[str, Any]

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> 'Step':
        """
        Generate a new Step from a dictionary.

        :arg d: Step config.
        :return: Step instance.
        """
        return Step(
            func=d['func'],
            name=d['name'],
            decorators=d['decorators'],
            kwargs=d['kwargs'],
        )
