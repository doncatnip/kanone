from ..validator.schema import Schema, ForEach
from ..error import Invalid
from ..util import varargs2kwargs, getArgSpec, getParameterNames

def validate( validator, onInvalid=None ):

    def __validateDecorator( f ):
        spec = getArgSpec( f )

        hasVarargs = spec.varargs is not None
        varargs =  spec.varargs or '*varargs'
        keywords = spec.keywords or None
        parameterNames = tuple(getParameterNames( f ))


        def __validateArgs(*args, **kwargs):
            (args, kwargs, shifted ) = varargs2kwargs( f, args, kwargs )

            if keywords is not None:
                restKwargs = dict(\
                    ( key, kwargs.pop(key))\
                        for key in kwargs.keys() if key not in parameterNames
                    )
                kwargs[ keywords ] = restKwargs

            if args or hasVarargs:
                kwargs[ varargs ] = args
            try:
                resultKwargs = validator.context( kwargs ).result
            except Invalid as e:
                if onInvalid is not None:
                    return onInvalid( e )
                else:
                    raise

            if args or hasVarargs:
                resultArgs = resultKwargs.pop( varargs )
                resultArgs = [ resultKwargs.pop(key) for key in shifted  ] + resultArgs
            else:
                resultArgs = []

            if keywords is not None:
                resultKwargs.update( resultKwargs.pop( keywords ) )
            return f( *resultArgs, **resultKwargs )

        return __validateArgs

    return __validateDecorator

