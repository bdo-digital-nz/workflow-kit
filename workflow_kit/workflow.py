from typing import Type, Callable, List, Tuple, Dict, Any

from pydantic import BaseModel

import workflow_kit


class Workflow:
    def __init__(self, model: Type[BaseModel]) -> None:
        """
        Constructor for a Workflow recipe/template.

        :arg model: Pydantic model defining the workflow event.
        """
        self.model = model

        self.init_func = None
        self.init_decorators = None

        self.steps = []
        self.exception_handlers = {}

    @property
    def name(self):
        return self.model.__name__

    def on_init(
            self,
            func: Callable | None = None,
            *,
            decorators: List[Callable | Tuple[Callable, Dict[str, Any]]] | None = None
    ):
        """
        Method to be run at the very beginning of a workflow.

        :arg func: Init function to run.
        :param decorators: Optional decorators to apply to the init function.
        """
        if self.init_func is not None:
            raise workflow_kit.WorkflowKitError(
                code='WorkflowError',
                message=f'Workflow "{self.name}" already has an init handler defined.'
            )

        def decorator(inner_func: Callable):
            self.init_func = inner_func
            self.init_decorators = decorators
            return inner_func

        if func is not None:
            self.init_func = func
            self.init_decorators = decorators
            return func

        return decorator

    def _step(
            self,
            func: Callable,
            decorators: List[Callable | Tuple[Callable, Dict[str, Any]]] | None = None,
            **kwargs
    ):
        """
        Inner step creation function.

        :arg func: Callable step.
        :param decorators: Optional decorators to apply to the step.
        :param kwargs: Optional kwargs to pass into the callable step.
        """
        self.steps.append({
            'func': func,
            'name': func.__name__,
            'kwargs': kwargs,
            'decorators': decorators,
        })

    def step(
            self,
            func: Callable | None = None,
            *,
            decorators: List[Callable | Tuple[Callable, Dict[str, Any]]] | None = None,
            **kwargs
    ):
        """
        Create a new step in the workflow to be run in sequence.

        :param func: Callable function.
        :param decorators: Optional decorators to apply to the step.
        :param kwargs: Optional kwargs to provide to the callable step.
        """
        def decorator(inner_func: Callable, **inner_kwargs):
            self._step(func=inner_func, decorators=decorators, **inner_kwargs)
            return inner_func

        if func is not None:
            self._step(func=func, decorators=decorators, **kwargs)
            return func

        return decorator

    def _catch(self, func: Callable, exception: Type[Exception]):
        """
        Inner exception handler.

        :arg func: Callable function to run when the provided exception is thrown.
        :arg exception: Exception type to catch.
        """
        if exception in self.exception_handlers:
            raise workflow_kit.WorkflowKitError(
                code='WorkflowError',
                message=f'Exception handler for "{exception.__name__}" '
                        f'already exists in workflow "{self.name}".'
            )
        self.exception_handlers[exception] = func
        return func

    def catch(self, func: Callable | None = None, *, exception: Type[Exception]):
        """
        Implement an exception handler to the workflow.

        :param func: Callable to invoke when the provided exception is thrown.
        :param exception: Exception type to catch.
        """
        def decorator(inner_func: Callable):
            self._catch(inner_func, exception)
            return inner_func

        if func is None:
            # Usage: @catch(exception=...)
            return decorator
        else:
            # Usage: @catch without params
            return decorator(func)
