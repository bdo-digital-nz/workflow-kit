from typing import Any

from workflow_kit import WorkflowKitError


class ResultOf:
    def __init__(self, name: str, n: int = 1) -> None:
        """
        Helper class for defining a required return value from a prior step.

        Example usage:
        `def step_2(result: Annotated[str, ResultOf('step_1')): ...`

        :arg name: Name of function (prior step to retrieve).
        :param n: Reverse index (default 0).
        """
        self.name = name
        self.n = n

    def __call__(self, results: 'Results') -> Any:
        """
        Internal call method to get the result.

        :arg results: `Results` instance.
        :return: Return value of the step.
        """
        return results.get(name=self.name, n=self.n)


class Results:
    def __init__(self):
        """Store for setting and accessing function results."""
        self._by_name = {}

    def add(self, result: Any, name: str) -> None:
        """
        Adds a result to the store.

        :arg result: Invocation result.
        :arg name: Function name.
        """
        if name not in self._by_name:
            self._by_name[name] = []

        self._by_name[name].append(result)

    def get(self, name: str, n: int = 1) -> Any:
        """
        Get a past result by name.

        :arg name: Name of the function.
        :param n: Reverse index of results.
        :return: Return value of function invocation.
        """
        if name not in self._by_name:
            raise WorkflowKitError(
                code='OrchestrationError',
                message=f'No result was found under the name \'{name}\''
            )
        return self._by_name[name][-n]
