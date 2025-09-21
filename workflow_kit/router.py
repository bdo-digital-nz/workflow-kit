from typing import List, Any, Tuple, Optional, Callable, Dict

from pydantic import BaseModel, ValidationError

import workflow_kit


class Router:
    def __init__(self, workflows: List['workflow_kit.Workflow']) -> None:
        """
        Router of Lambda events to a specified workflow based on the
        event provided in.

        :arg workflows: List of `Workflow` instances.
        """
        if not isinstance(workflows, list):
            workflows = []

        self._routes = {flow.model: flow for flow in workflows}

        # Event serialisation
        self._model_types = tuple(flow.model for flow in workflows)

        self._root_exception_handler = None

    def _validate(self, event: Any) -> BaseModel:
        """
        Internal validation of an event to best match it to
        a Pydantic schema.

        :arg event: Raw event received to validate.
        :return: Best matching Pydantic model for the event.
        """
        # Directly return the event if it is already serialised
        if isinstance(event, self._model_types):
            return event

        match: Tuple[int, Any] | None = None

        # Attempt to match the event to a serialised model
        for model in self._model_types:
            try:
                return model.model_validate(event)
            except ValidationError as e:
                score = len(e.errors())
                if match is None or score < match[0]:
                    match = (score, e)

        raise match[1]

    def invoke(self, event: Any, context: Any = None, deps: Optional['workflow_kit.DependencyInjector'] = None):
        """
        Invokes an event by best matching it to a Pydantic schema
        and routing it to a workflow accordingly.

        :arg event: Event payload received.
        :param context: Lambda context.
        :param deps: DependencyInjector instance (when invoking a sub-event).
        :return: Response value from the workflow.
        """
        try:
            event = self._validate(event)
            workflow = self._routes[type(event)]

            orchestration = workflow_kit.Orchestration(
                router=self,
                workflow=workflow,
                event=event,
                context=context,
                deps=deps,
            )

            return orchestration.run()

        except (Exception, ) as e:
            if not self._root_exception_handler:
                raise e

            return self._root_exception_handler()

    def root_exception_handler(self, func: Callable):
        """
        Add a root exception handler to catch any exception and
        override the response from the action.
        :arg func: Callable function.
        """
        if self._root_exception_handler is not None:
            raise workflow_kit.WorkflowKitError(
                code='RouterError',
                message='A root exception handler has already been defined.'
            )
        self._root_exception_handler = func
        return func

    def create_lambda_handler(self, decorators: List[Callable | Tuple[Callable, Dict[str, Any]]] | None = None):
        """
        Creates a Lambda handler function to be used as the
        entry-point of the microservice.

        :arg decorators: Apply extra decorators to the Lambda handler.
        :return: Lambda function handler.
        """
        def lambda_handler(event, context):
            return self.invoke(event, context)

        for decorator in decorators:
            if isinstance(decorator, tuple):
                decorator_callable, kwargs = decorator
                lambda_handler = decorator_callable(lambda_handler, **kwargs)
            else:
                lambda_handler = decorator(lambda_handler)

        return lambda_handler
