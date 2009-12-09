from zope.interface.advice import addClassAdvisor
from UserDict import UserDict
import sys

from pyped.util.utypes import Pulp

from .error import DepencyError, IsMissing, Invalid
from . import settings

import copy, logging
log = logging.getLogger(__name__)



class missing:
    pass

class IGNORE:
    pass

def _append_list(klass, key, data):
    setattr\
        ( klass
        , "__%s__" % key
        , list(getattr(klass,key,[])) + list(data)
        )


def _append_fields(klass, key, fields):
    prev_fields = getattr\
        ( klass
        , '__fields__'
        , []
        )

    newfields = list(prev_fields)

    field_index = {}
    pos = 0
    for (name, validator) in prev_fields:
        field_index[name] = pos
        pos+=0

    for (name, validator) in fields:
        if name in field_index:
            newfields[field_index[name]] = (name,validator)
        else:
            newfields.append((name,validator))


    setattr\
        ( klass
        , '__fields__'
        , newfields
        )


def _create_method_test(klass, key, method_decorator):
    for validator in method_decorator.validators:
        setattr(klass, "test_%s" % validator.name, validator.method_test)


def _callback(klass):
    advice_data = klass.__dict__['__advice_data__']

    for key,(data, callback)  in advice_data.iteritems():
        callback( klass, key, data)

    del klass.__advice_data__

    return klass

def _advice(name, callback,  data, depth=3 ):
    frame = sys._getframe(depth-1)
    locals = frame.f_locals

    if (locals is frame.f_globals) or (
        ('__module__' not in locals) and sys.version_info[:3] > (2, 2, 0)):
        raise TypeError("%s can be used only from a class definition." % name)

    if not '__advice_data__' in locals:
        locals['__advice_data__'] = {}

    if name in locals['__advice_data__']:
        raise TypeError("%s can be used only once in a class definition." % name)


    if not locals['__advice_data__']:
        addClassAdvisor(_callback, depth=depth)

    locals['__advice_data__'][name] = (data, callback)


def pre_validate(*validators):
    _advice('pre_validate', _append_list,  validators)

def post_validate(*validators):
    _advice('post_validate', _append_list,  validators)

def fieldset(*fields):
    _advice('fieldset', _append_fields, fields )

def method_test(method_decorator):
    _advice('method_test', _create_method_test, method_decorator)


class ValidationState(object):

    def __init__(self, validator, context, values ):
        self.__context__ = context
        self.__validator__ = validator
        self.__values__ = values

    def __cascade__(self, errback=None):
        result = Pulp()

        failed = False
        field_index = self.__validator__.field_index_get( self.__context__ )

        for key in field_index:
            try:
                next = getattr(self, key)
            except IsMissing,e:
                pass
            except DepencyError,e:
                failed = True
            else:
                if isinstance(next, ValidationState):
                    result[key], cascade_failed = next.__cascade__(  )
                    if cascade_failed:
                        failed = True
                else:
                    result[key] = next

        if errback and failed:
            errback( self.__context__ )

        return (result, failed)

    def __do_validate__(self):
        if not self.__context__.validated:
            self.__validator__.do_validate(self.__context__)
            self.__context__.validated = True

        if self.__context__.error:
            raise DepencyError\
                ( "Got an error for requested field '%(field)s'"
                , field=self.__context__.key
                , error=self.__context__.error[0]
                )

        if hasattr(self.__context__, 'result'):
            return self.__context__.result

        raise IsMissing("Field '%(field)s' is missing", field=self.__context__.key)

    def __getattr__(self, attr):
        if attr.endswith('_context'):
            attr = attr[:-8]
            context_only = True
        else:
            context_only = False

        if not attr in self.__context__:

            if isinstance(self.__validator__,SchemaBase):

                validator = self.__validator__.validator_get( self.__context__, attr )

                self.__do_validate__()

                if attr in self.__values__:
                    value = self.__values__[attr]
                else:
                    value = missing

                context = self.__context__.new(attr, value)
                if context_only:
                    return context

                validator.do_validate( context )
                context.validated = True
            else:
                return TypeError("%s is not a Schema" % self.__validator__)

        if context_only:
            return self.__context__[attr]

        if self.__context__[attr].error:
            raise DepencyError( "Got an error for requested field '%(field)s" )
        elif hasattr(self.__context__[attr], 'result'):
            return self.__context__[attr].result
        else:
            raise IsMissing("Field '%(field)s' is missing", field = attr)


    def __call__(self, attr, context_only=False):
        path = attr.split('.')
        valid = self
        while path:
            part = path.pop(0)
            if not path and context_only:
                part = "%s_context" % part
            valid = getattr(valid, part)

        return valid

class Context(UserDict):

    validated = False

    def __init__(self, value, key="result", state=None, root_state=None):
        if value == '':
            value = None

        self.value = value
        self.state = state or Pulp()
        self.key = str(key)
        self.error = None
        self.__objstate__ = Pulp()

        if root_state is not None:
            self.require = root_state

        UserDict.__init__(self)

    def new(self, key, value):
        key = str(key)
        self[key] = Context( value, key, root_state=getattr(self,'require',None))
        return self[key]

    def pack(self):
        field = {}

        child=None
        for (key, child) in self.iteritems():

            field[key.upper()] = child.pack()

        if self.error:
            field["error"] = self.error[0]

        if child is None:
            if self.value is not missing:
                field["value"] = self.value

            if hasattr(self, "result"):
                if isinstance(self.result, ValidationState ):
                    result,failed = self.result.__cascade__()
                else:
                    result = self.result
                field["result"] = result

        return field

    def objstate(self, obj):
        return self.__objstate__(obj.__hash__())

class ValidatorBase(object):

    __staticinfo__      = settings.text.Validator.info
    __pre_validate__    = []

    def __call__( self, context, errback=None, value=missing, cascade=True):

        result = self.do_validate( context, value )
        context.validated = True

        if context.error:
            if errback:
                errback(context)

        elif isinstance( result, ValidationState ) and cascade:
            result, failed = result.__cascade__( errback=errback )

        return result

    def __info__(self, context):
        return getattr(self,'info', self.__staticinfo__)

    def __extra__(self, context):
        return {}

    def info_get(self, context):
        info,extra = self.__info__( context ), self.__extra__( context )
        retval = { 'info': info, 'type': self.__class__.__name__ }
        retval.update( extra )
        return retval

    def text( self, msg=None, info=None):
        if msg:
            self.msg    = msg
        if info:
            self.info   = info
        return self

    def do_validate(self, context, value=missing):
        if value is IGNORE:
            return value

        if value is missing:
            value = context.value

        try:
            nextvalue = IGNORE

            if isinstance( value, dict ) or isinstance( value, list ):
                if len(value) == 0:
                    value = None

                if isinstance( value, dict):
                    n = None
                    for (key, val) in value.iteritems():
                        if val is not None and val is not '':
                            n = value
                            break
                    value = n

                elif isinstance( value, list):
                    n = None
                    for val in value:
                        if val is not None and val is not '':
                            n = value
                            break
                    value = n

            if value is missing:
                nextvalue = self.on_missing(context)

            elif value is None:
                nextvalue = self.on_blank(context)

            if nextvalue is not IGNORE:
                value = nextvalue

            if value not in [ missing, None ]:
                value = self.on_validate(context, value)

        except DepencyError:
            pass
        except Invalid,e:
            if not 'info' in e[0]:
                e[0].update( self.info_get( context ) )
            context.error = e
            if hasattr(context,'result'):
                del context.result
            if context.state.abort:
                raise e
        else:
            if value is not missing:
                context.result = value
            elif hasattr( context, 'result' ):
                del context.result

        return value


    def on_validate(self, context, value):
        return value



class SchemaBase( object ):

    def vstate_get(self, context, values):

        objstate = context.objstate( self )
        if not 'vstate' in objstate:
            objstate.vstate = ValidationState(self, context, values)

            if not hasattr(context,'require'):
                context.require = objstate.vstate

        return objstate.vstate

    def validator_get( self, context, key ):
        raise NotImplementedError( "SchemaBase can only be used as base class")

    def field_index_get( self, context ):
        raise NotImplementedError( "SchemaBase can only be used as base class")


def _do_validate( state, schema, errback, *args):
    context = Context(args, state=state)
    result = schema(context, errback=errback)
    return result

class MethodValidatorBase():

    def __init__(self, schema, errback):
        self.schema = schema
        self.errback = errback

    def __call__(self, f ):
        self.name = f.__name__
        def decorate( nself, state, *args):
            return f( nself, state, self.method_test(state, *args))
        return decorate

    def method_test(self, state, *args):
        return _do_validate( state, self.schema, self.errback, *args)

class MethodDecorator():

    def __init__(self, errback=None):
        self.errback = errback or settings.errback
        self.validators = []

        from .validator import Schema

    def __call__(self, *validator):
        if len(validator)==1 and hasattr(validator[0], 'on_validate'):
            validator = validator[0]
        else:
            validator = Schema(*validator)

        validator = MethodValidatorBase(validator, self.errback)
        self.validators.append(validator)

        return validator
