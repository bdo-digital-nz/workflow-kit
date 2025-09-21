__all__ = ['Orchestration']

from typing import Any, Callable, List, Tuple, Dict

from pydantic import BaseModel

import workflow_kit
from workflow_kit.dependencies import DependencyInjector
from workflow_kit.results import Results, ResultOf
from workflow_kit.step import Step
from workflow_kit.types import Decorator


class Orchestration:
    def __init__(
            self,
            router: 'workflow_kit.Router',
            workflow: 'workflow_kit.Workflow',
            event: BaseModel,
            context: Any,
            deps: DependencyInjector | None = None
    ):
        """
        Workflow orchestrator handling dependency injection.

        :arg router: Router instance.
        :arg workflow: Workflow instance.
        :arg event: Event Pydantic model.
        :arg context: AWS Lambda context object.
        :param deps: DependencyInjector instance.
        """
        self._router = router
        self._context = context
        self._event = event
        self._workflow = workflow

        self._di = self._build_di(deps)
        self._steps: List[Step] = [Step.from_dict(step) for step in self._workflow.steps]
        self._results = Results()
        self._di.add_callback(ResultOf, self._resolve_result_callback)
        self._response = None
        self._index = 0
        self._temp_index = None
        self._finished = False

    def __enter__(self):
        self._temp_index = self._index
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._temp_index = None
        return False

    @property
    def name(self):
        return self._workflow.name

    def _maybe_call_init(self) -> None:
        """Calls init function if the workflow defines one."""
        if self._workflow.init_func:
            self._call_with_di(self._workflow.init_func, decorators=self._workflow.init_decorators)

    def _build_di(self, deps: DependencyInjector | None = None) -> DependencyInjector:
        """
        Builds a new dependency injector for the orchestration.

        :param deps: Existing DependencyInjector instance (if applicable).
        :return: DependencyInjector instance.
        """
        di_args = {}

        # Copy existing types/names when an existing DI is provided.
        if deps:
            di_args['types'] = deps.types
            di_args['names'] = deps.names

        di = DependencyInjector(**di_args)
        di.add(self, self._event, di, context=self._context)
        return di

    def _resolve_result_callback(self, result_of: ResultOf) -> Any:
        """
        Callback to resolve the result of a specific step.

        :arg result_of: ResultOf instance.
        :return: Return value if one can be resolved.
        """
        return result_of(self._results)

    def _call_with_di(self, func: Callable, decorators: List[Decorator] | None = None, **kwargs) -> Any:
        """
        Invokes a callable using the dependency injector and
        handles exceptions according to the workflow.

        :arg func: Callable.
        :param decorators: Optional decorators to wrap callable with.
        :param kwargs: Optional kwargs to pass to callable.
        :return: Return value of callable.
        """
        try:
            return self._di(func, decorators=decorators, **kwargs)
        except (Exception,) as exc:
            if not self._dispatch_exception(exc) or not self._finished:
                raise exc

    def _dispatch_exception(self, exc: Exception) -> bool:
        """
        Handles exceptions raised by the orchestration.

        :arg exc: Exception instance.
        :return: Propagate exception.
        """
        for exc_type in type(exc).mro():
            handler = self._workflow.exception_handlers.get(exc_type)
            if handler:
                self._di(handler, exception=exc, exc=exc, e=exc)
                return True
        return False

    def _execute_step(self, step: Step) -> None:
        """
        Executes a step.

        :arg step: Step instance.
        """
        self._results.add(
            result=self._call_with_di(
                func=step.func,
                decorators=step.decorators,
                **step.kwargs,
            ),
            name=step.name,
        )

    @property
    def response(self):
        return self._response

    def end(self, response: Any = None):
        """
        Ends the orchestration in place.

        :param response: Response payload to return to caller.
        """
        self._response = response
        self._finished = True

    def new(self, event: Any):
        """
        Invokes a new event.

        :arg event: Event payload.
        :return: Return value of the new event.
        """
        return self._router.invoke(event, context=self._context, deps=self._di)

    def add(
            self,
            func: Callable,
            decorators: List[Callable | Tuple[Callable, Dict[str, Any]]] | None = None,
            **kwargs
    ) -> None:
        """
        Adds a new step to the orchestration in its current place.
        Must be used within the Orchestration context manager.

        :arg func: Callable.
        :param decorators: Optional decorators to wrap callable with.
        :param kwargs: Optional kwargs to pass to callable.
        """
        if self._temp_index is None:
            raise workflow_kit.WorkflowKitError(
                code='WorkflowError',
                message='Cannot insert step into workflow outside of orchestration context.'
            )

        self._temp_index += 1
        self._steps.insert(
            self._temp_index,
            Step(
                func=func,
                decorators=decorators,
                name=func.__name__,
                kwargs=kwargs,
            )
        )

    def run(self) -> Any | None:
        """
        Runs the event orchestration.

        :return: Response value if any.
        """
        self._maybe_call_init()

        while not self._finished:
            if self._index >= len(self._steps):
                self._finished = True
            else:
                self._execute_step(self._steps[self._index])
                self._index += 1

        return self._response
