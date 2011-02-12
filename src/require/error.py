class Invalid(Exception):

    def __init__(self, type, msg, **kwargs):
        self.msg = msg
        self.type = type
        self.extra = dict(kwargs)
        Exception.__init__(self,"%s:%s" (type,msg),self.extra)

    def __str__(self):
        if self.context is not None:
            return self.context.root.errorFormatter( context, self )
        else:
            return self.__repr__()

class DepencyError( Invalid ):

    def __init__(self, context ):
        self.context = context
        self.msg = "Depency Error"
        self.type = 'depency'
        self.extra = {}
        Exception.__init__(self,msg)

