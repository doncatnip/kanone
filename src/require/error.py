class Invalid(Exception):

    context = None
    validator = None

    def __init__(self, _key='fail', **kwargs):
        self.data = {}
        self.data['key'] = _key
        self.data['extra'] = dict(kwargs)
        Exception.__init__( self, _key )

    @property
    def message(self):
        return self.data['message']

    @property
    def key(self):
        return self.data['key']

    @property
    def extra(self):
        return self.data['extra']

    def __str__(self):
        if self.context is not None:
            return self.context.root.errorFormatter( self.context, self )
        else:
            return self.__repr__()

