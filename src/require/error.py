class Invalid(Exception):

    def __init__(self, msg, type='fail', **kwargs):
        self.msg = msg
        self.type = type
        self.extra = dict(kwargs)
        Exception.__init__(self,"%s:%s" (type,msg),self.extra)

    def __str__(self):
        if self.context is not None:
            return self.context.root.errorFormatter( context, self )
        else:
            return self.__repr__()

