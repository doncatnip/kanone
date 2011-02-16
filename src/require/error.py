class Invalid(Exception):

    context = None
    msg = 'Invalid'

    def __init__(self, _key='fail', **kwargs):
        self.key = _key
        self.extra = dict(kwargs)
        Exception.__init__( self )

    def __str__(self):
        if self.context is not None:
            return self.context.root.errorFormatter( self.context, self )
        else:
            return self.__repr__()

