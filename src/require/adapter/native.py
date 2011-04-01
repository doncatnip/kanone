from ..validator.schema import Schema, ForEach
from ..error import Invalid
from ..util import varargs2kwargs, getArgSpec

def validate( validator, onInvalid=None ):
    resultArgs = []

    def __validateDecorator( f ):
        varargs = getArgSpec( f ).varargs

        def __validateArgs(*args, **kwargs):
            if varargs is not None:
                (args, kwargs, shifted ) = varargs2kwargs( f, args, kwargs )
                kwargs[ varargs ] = args
            try:
                resultKwargs = validator.context( kwargs ).result
            except Invalid as e:
                if onInvalid is not None:
                    return onInvalid( e )
                else:
                    raise
            if varargs is not None:
                resultArgs = resultKwargs.pop( varargs )
                resultArgs = [ resultKwargs.pop(key) for key in shifted  ] + resultArgs
            return f( *resultArgs, **resultKwargs )

        return __validateArgs

    return __validateDecorator

