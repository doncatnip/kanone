from require import Invalid

class validate():

    def __init__( self, validator, errorFormatter=None ):
        self.validator = validator
        self.errorFormatter = errorFormatter

    def __call__( self, origFunction ):
 
        def __formFunction__( nself, action, environ, start_response, controller, pylons, *args, **kwargs ):
            request = nself._py_object.request
 
            context = self.validator.context( dict(request.params) )
            if request.params:
                if self.errorFormatter is not None:
                    context.errorFormatter = self.errorFormatter
                try:
                    result = context.result
                except Invalid:
                    pass
                else:
                    return self.__successFunc__( nself,  result, *args, **kwargs )
            else:
                self.__initFunc__( nself, context, *args, **kwargs )

            return origFunction( nself, context, *args, **kwargs )

        def initFormFunction(  initFunc ):
            self.__initFunc__ = initFunc

            return __formFunction__

        def successFormFunction(  successFunc ):
            self.__successFunc__ = successFunc

            return __formFunction__

        __formFunction__.init = initFormFunction
        __formFunction__.success = successFormFunction

        return __formFunction__


