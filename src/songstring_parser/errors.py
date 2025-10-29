class ParseError(Exception):
    """Raised when the string is too complex/ambiguous to parse confidently."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}