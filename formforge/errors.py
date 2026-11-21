class DocumentError(Exception):
    def __init__(self, message: str, status: int = 422, code: str = "invalid_document"):
        super().__init__(message)
        self.message, self.status, self.code = message, status, code
