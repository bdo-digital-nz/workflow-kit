class WorkflowKitError(Exception):
    def __init__(self, code: str, message: str, **extra) -> None:
        """
        Base class for all mesh-kit errors.

        :arg code: Error code.
        :arg message: Error message.
        :param extra: Extra data to be included in the error response.
        """
        self.code = code
        self.message = message
        self.extra = extra
        super().__init__(f'[{code}] {message}')
