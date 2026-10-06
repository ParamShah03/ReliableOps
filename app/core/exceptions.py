class ReliableOpsError(Exception):
    """Base application exception."""


class UnknownToolError(ReliableOpsError):
    pass


class ToolExecutionError(ReliableOpsError):
    pass


class ToolTimeoutError(ToolExecutionError):
    pass


class ApprovalRequired(ReliableOpsError):
    def __init__(self, tool_name: str, payload: dict):
        super().__init__(f"Approval required for {tool_name}")
        self.tool_name = tool_name
        self.payload = payload


class StructuredOutputError(ReliableOpsError):
    pass
