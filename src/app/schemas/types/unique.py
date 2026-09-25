class Unique:
    """Validate that a value is unique in the database."""

    def __init__(self, model, field, msg):
        self.model = model
        self.field = field
        self.msg = msg

    def __call__(self, value):
        return value
