from kanone import Invalid
from decorator import decorator

def validate( validator, errorFormatter=None ):

    def __wrapper__( origFunction  ):

        def __formFunction__( f, self, *args, **kwargs ):
            request = self._py_object.request
            self.form_context = context = validator.context( dict(request.params) )

            if request.params:
                if errorFormatter is not None:
                    context.errorFormatter = errorFormatter
                try:
                    result = context.result
                except Invalid:
                    pass
                else:
                    return __formFunction__.__successFunc__( self,  result, *args, **kwargs )
            else:
                __formFunction__.__initFunc__( self, context, *args, **kwargs )
        
            return f( self, *args, **kwargs )
       
        resultFunc = decorator( __formFunction__, origFunction )

        def initFormFunction(  initFunc ):
            __formFunction__.__initFunc__ = initFunc
        
            return resultFunc
        
        def successFormFunction(  successFunc ):
            __formFunction__.__successFunc__ = successFunc
        
            return resultFunc

        resultFunc.init = initFormFunction
        resultFunc.success = successFormFunction
        return resultFunc

    return __wrapper__
