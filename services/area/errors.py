class AreaNotFoundError(Exception):
    def __init__(self, message: str = "Area not found"):
        self.message = message
        super().__init__(self.message)

class ParentAreaNotFoundError(Exception):
    def __init__(self, message: str = "Parent area not found"):
        self.message = message
        super().__init__(self.message)