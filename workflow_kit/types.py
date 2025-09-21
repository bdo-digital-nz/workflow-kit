from typing import TypeAlias, Callable, Tuple, Dict, Any

Decorator: TypeAlias = 'Callable | Tuple[Callable, Dict[str, Any]]'
