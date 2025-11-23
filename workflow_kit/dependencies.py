__all__ = ['DependencyInjector']

import inspect
from typing import Callable, Dict, Any, get_type_hints, List, Tuple, get_origin, Annotated, get_args

import workflow_kit


class DependencyInjector:
    def __init__(self, types: Dict[Any, Any] | None = None, names: Dict[str, Any] | None = None) -> None:
        """
        Dependency container for injecting dependencies into callables.

        :param types: Optional types dict to initialise with.
        :param names: Optional names dict to initialise with.
        """
        self.types = types if types else {}
        self.names = names if names else {}
        self.callbacks = {}

    def __call__(
            self,
            func: Callable,
            decorators: List[Callable | Tuple[Callable, Dict[str, Any]]] | None = None,
            **kwargs
    ) -> Any:
        """
        Invokes a callable with dependencies.

        :arg func: Callable.
        :param kwargs: Keyword args to provide.
        :param decorators: List of decorators to apply.
        :return: Return value.
        """
        params = self.resolve(func, **kwargs)

        if not decorators:
            decorators = []

        for decorator in decorators:
            if isinstance(decorator, tuple):
                deco_callable, deco_kwargs = decorator
                func = deco_callable(func, **deco_kwargs)
            else:
                func = decorator(func)

        return func(**params)

    def add(self, *args, **kwargs) -> None:
        """
        Adds dependencies to the injector.

        :arg args: Typed dependencies.
        :param kwargs: Named dependencies.
        """
        # Add typed dependencies
        for arg in args:
            self.types[type(arg)] = arg

        # Add named dependencies
        for key, value in kwargs.items():
            self.names[key] = value

    def add_callback(self, value: Any, resolver: Callable[[Any], Any]) -> None:
        """
        Adds a callback to the injector.

        :arg value: Type to trigger callback.
        :arg resolver: Resolver function for the callback.
        """
        self.callbacks[value] = resolver

    def resolve(self, func: Callable, **kwargs) -> Dict[str, Any]:
        """
        Resolves dependencies for a callable.

        :arg func: Callable.
        :param kwargs: Function args.
        :return: Dict of resolved dependencies.
        """
        params = {}
        annotations = get_type_hints(func)

        for name, param in inspect.signature(func).parameters.items():
            annotated_type = annotations.get(name)
            value = kwargs.get(name)
            is_positional = param.default == getattr(inspect, '_empty')

            # Handle callbacks
            if get_origin(param.annotation) is Annotated:
                callback = get_args(param.annotation)[1]
                if type(callback) not in self.callbacks:
                    raise workflow_kit.WorkflowKitError(
                        code='DependencyError',
                        message=f'Annotation in param name \'{name}\' for function \'{func.__name__}\' '
                                'did not resolve to a callback',
                    )
                params[name] = self.callbacks[type(callback)](callback)

            # Match on type
            elif annotated_type in self.types:
                params[name] = self.types[annotated_type]

            # Match on name
            elif name in self.names:
                params[name] = self.names[name]

            # Assign from kwargs
            elif name in kwargs:
                params[name] = value

            # Throw if param is required
            elif is_positional:
                raise workflow_kit.WorkflowKitError(
                    code='DependencyError',
                    message='Dependency for positional argument '
                            f'"{name}" in "{func.__name__}" cannot be inferred.'
                )

        return params
