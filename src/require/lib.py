from zope.interface.advice import addClassAdvisor
from UserDict import UserDict
import sys

from pulp import Pulp

from .error import  Invalid

import copy, logging
log = logging.getLogger(__name__)


# TODO
# * Validators:
#   * new: core.Limit( min=None, max=None )   ( Dict/List/Integer/Float )
#   * new: core.Len( min=None, max=None )     ( String/Integer/Float )
#   * new: schema.Merge( klass, other )

class PASS:
    pass

class __MISSING__:
    def __str__(self):
        return ''

MISSING = __MISSING__()


def _append_list(klass, key, data):
    setattr\
        ( klass
        , "__%s__" % key
        , list(getattr(klass,key,[])) + list(data)
        )

def _merge_dict(klass, key, data):
    fields = dict(getattr\
        ( klass
        , '__%s__' % key
        , {}
        ))

    fields.update( data )

    setattr\
        ( klass
        , "__%s__" % key
        , fields
        )
   
def _merge_fields(klass, key, fields):
    if (len(fields)%2 != 0) or (len(fields)<2):
        raise SyntaxError("Invalid number of fields supplied (%s). Use: %s(key, value, key, value, …)" % (len(fields),key))

    prev_fields = getattr\
        ( klass
        , '__%s__' % key
        , []
        )

    newfields = list(prev_fields)

    field_index = {}
    pos = 0
    for (name, value) in prev_fields:
        field_index[name] = pos
        pos+=1

    pos = 0
    for value in fields:
        if pos%2 != 0:
            if name in field_index:
                newfields[field_index[name]] = (name,value)
            else:
                newfields.append((name,value))
        else:
            name = value
        pos += 1

    setattr\
        ( klass
        , '__%s__' % key
        , newfields
        )

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
        raise SyntaxError("%s can be used only from a class definition." % name)

    if not '__advice_data__' in locals:
        locals['__advice_data__'] = {}

    if name in locals['__advice_data__']:
        raise SyntaxError("%s can be used only once in a class definition." % name)


    if not locals['__advice_data__']:
        addClassAdvisor(_callback, depth=depth)

    locals['__advice_data__'][name] = (data, callback)


def pre_validate(*validators):
    _advice('pre_validate', _append_list,  validators)

def post_validate(*validators):
    _advice('post_validate', _append_list,  validators)

def fieldset(*fields):
    _advice('fieldset', _merge_fields, fields )

def messages(**fields):
    _advice('messages', _merge_dict, fields )


def defaultErrorFormatter( context, error ):
    return error.msg % (error.extra)


class DataHolder( object ):
    def __init__(self):
        __data__ = {}

    def __call__(self, validator):
        if not validator in self.__data__:
            self.__data__[ validator ] = Pulp()
        return self.__data__[ validator ]

class Context( dict ):

    __value__ = MISSING
    __error__ = MISSING
    __result__ = MISSING

    parent = None
    root = None

    key = ''

    isValidated = False
    isPopulated = False

    def __init__(self, key='', parent=None):
        if parent is not None:
            self.parent = parent
            self.root = parent.root
            self['path'] = '%s.%s' % (parent.path,key)
        else:
            self.root = self
            self.errorFormatter = defaultErrorFormatter

    @apply
    def path():
        def fget(self):
            if 'path' in self:
                return ''
            return self['path']

    @apply
    def childs():
        def fget(self):
            if not 'childs' in self:
                self[ 'childs' ] = {}
            return self['childs']

    @apply
    def value():
        def fget(self):
            return self.populate()

        def fset(self,value):
            self.__value__ = value
            self.isValidated = False
            self.isPopulated = False
            self.clear()

    @apply
    def result():
        def fget(self):
            return self.validate()

    @apply
    def error():
        def fget(self):
            if not 'error' in self:
                return MISSING
            return self['error']

    @apply
    def validator():
        def fget(self):
            if not hasattr(self, '__validator__'):
                return None
            return self.__validator__

        def fset(self,value):
            self.__validator__ = value
            self.clear()

    def clear( self ):
        dict.clear( self )

        self.isValidated = False
        self.isPopulated = False

        self.__resulf__ = MISSING
        self.__error__ = MISSING
        self['value'] = self.__value__

    def populate(self ):
        if self.isPopulated:
            return self['value']

        if self.parent is not None:
            self.parent.populate()

        self.data = DataHolder()
        result = PASS

        if (self.validator is None):
            raise AttributeError("No validator set for context '%s'" % self.path )

        try:
            result = self.validator.validate( self, self['value'] )
        except Invalid,e:
            e.context = self
            __error__ = e
        else:
            if result is not PASS:
                self.__result__ = result

        return self['value']

    def validate(self ):

        if not self.isPopulated:
            self.populate()

        if not self.isValidated:

            if self.__result__ is not MISSING:
                self['result'] = self.__result__
            elif self.__error__ is not MISSIG:
                self['error'] = self.__error__

            self.isValidated = True

        if self.__error__ is MISSING:
            return self.__result__

        raise self.error

    def __call__( self, path ):
        path = path.split('.',1)

        try:
            child = self.childs[path[0]]
        except KeyError,e:
            child = self.childs[path[0]] = Context( key=path[0], parent=self )

        if(len(path)==1):
            return child
        else:
            path=path[1]

        return child.field(path)


class ValidatorBase(object):

    messages\
        ( fail='Validation failed'
        )

    __update__ = False

    def __call__( self, value=MISSING ):
        context = Context( value )
        context.validator = self
        context.value = value
        return context

    def validate( self, context, value ):
        if (value is MISSING):
            return self.on_missing( context )
        elif (value is None):
            return self.on_blank( context )
        else:
            return self.on_value( context, vale )

    def invalid( self, type='fail', **kwargs ):
        if 'catchall' in self.__messages__:
            msg = self.__messages__['catchall']
        else:
            msg = self.__messages__[type]
        type = "%s.%s" % (self.__class__.name,type)
        return Invalid( msg, type=type, **kwargs )

    def error( self, **messages ):
        # copy class attribute to object
        self.__messages__ = dict(self.__messages__)
        self.__messages__.update(messages)
        return self
