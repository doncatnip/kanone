import inspect

def __setHook__(hook=None):
    def setHook(func):
        func.__parameterize__ = True
        func.__parameterizeHook__ = hook
        return func
    return setHook

def parameterize(func):
    func.__parameterize__ = True
    return func

parameterize.hook = __setHook__


class Parameterized( dict ):
    __obj__ = None
    __kwargs__ = None
    __isroot__ = False

    def __init__( self, objOrParent, args=(), kwargs=None ):
        if kwargs is None:
            kwargs = {}

        if isinstance( objOrParent, Parameterized ):
            newkwargs = dict(objOrParent.__kwargs__ )
            newkwargs.update(kwargs)
            kwargs = newkwargs
            obj = objOrParent.__obj__
        else:
            self.__isroot__ = True
            obj = objOrParent

        self.__obj__ = obj

        for (m,hook) in obj.__parameterizedMethods__:
            setattr( self, m.__name__, Parameterized.__parameterize__( self, m, hook ) )

        if hasattr( obj, 'setParameters' ):

            if not hasattr( obj.setParameters.im_func, '__spec__'):
                spec = inspect.getargspec( obj.setParameters )
                setattr( obj.setParameters.im_func,'__spec__',spec )
            else:
                spec = obj.setParameters.__spec__

            realargs = list(args)
            numSpecArgs = len(spec.args )

            for argpos in range( len( args ) ):
                if argpos < numSpecArgs-2:
                    kwargs[ spec.args[ argpos-3 ] ] = args[ argpos ]
                    del realargs[0]

            obj.setParameters( self, *realargs, **kwargs )

        elif args or kwargs:
            raise SyntaxError( "%s takes no arguments" % self.__obj__.__name__ )

        self.__kwargs__ = kwargs

    @classmethod
    def __parameterize__( klass, params, m, hook=None ):
        def parameterizedMethod(  *args, **kwargs ):
            theParams = params
            if hook:
                theParams = hook( params, *args, **kwargs )
            return m( theParams, *args, **kwargs )

        return parameterizedMethod

    def __call__( self, *args, **kwargs):
        if args or kwargs:
            return self.clone( *args, **kwargs )
        return self

    def __setattr__(self,key, value):
        if not hasattr(self,key) and not hasattr(value,'__call__'):
            self[key] = value
        else:
            dict.__setattr__( self, key, value )

    def __getattr__(self,key):
        try:
            return self[key]
        except KeyError,e:
            raise AttributeError('Parameter %s not found' % key )

    def __and__(self,other):
        return self.__dict__['__and__'](other)

    def clone( self, *args, **kwargs):
        return Parameterized( self, args=args, kwargs=kwargs )

    def new( self, *args, **kwargs):
        return Parameterized( self.__obj__, args=args, kwargs=kwargs )


class Parameterizable( object ):

    def __new__(klass, *args, **kwargs):
        klass.__prepare__()

        members = inspect.getmembers( klass )
        methods = []

        for (name,m) in members:
            if hasattr(m,'im_func')\
            and m.im_func.func_dict.get('__parameterize__',False):
                hook = m.im_func.func_dict.get\
                    ( '__parameterizeHook__'
                    , None
                    )
                if hook is not None:
                    hook = hook.__get__(self)

                methods.append\
                    (   ( m
                        , hook
                        )
                    )

        klass.__parameterizedMethods__ = methods

        return Parameterized( klass, args=args, kwargs=kwargs )


class Factory:

    _singletons = {}

    def __init__( self, klass ):
        self.klass = klass

    def __call__( self, *args, **kwargs):
        if not self.klass in Factory._singletons:
            obj = self.klass( *args, **kwargs )
            Factory._singletons[ self.klass ] = obj
            return obj
        else:
            obj = Factory._singletons[ self.klass ]

            if isinstance(obj, Parameterized):
                obj = obj.new( *args, **kwargs)

            return obj




class Validator( Parameterizable ):

    @classmethod
    def __prepare__( klass ):
        klass.validate = Validator.__wrapValidate__( klass.validate )

    @classmethod
    def __wrapValidate__( klass,  func ):
        @classmethod
        @parameterize.hook(Validator.prepareParams)
        def validate( *args, **kwargs ):
            try:
                return func( *args, **kwargs)
            except Exception, e:
                print "invalid"

        return validate

    def prepareParams( klass, params, *args, **kwargs ):
        print "prepare"
        return params



@Factory
class SomeValidator( Validator ):

    @classmethod
    def setParameters( klass, params, param1, param2, param3=False ):
        params.param1 = param1
        params.param2 = param2
        params.param3 = param3

    @classmethod
    def validate( klass, params, context, value ):
        return "42!"

    @classmethod
    @parameterize
    def __and__( klass, params, other ):
 
