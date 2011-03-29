class Invalid(BaseException):

    def __init__(self, _validator=None, _key='fail', **kwargs):
        if _validator is not None:
            self.validator = _validator
        self.data = {'key': _key, 'extra': kwargs}

    @property
    def key(self):
        return self.data['key']

    @property
    def message(self):
        return self.data.get('message',None)

    @property
    def extra(self):
        return self.data['extra']

    def __str__(self):
        if self.context is not None and self.message is not None:
            return self.context.root.errorFormatter( self.context, self )
        else:
            return self.__repr__()

