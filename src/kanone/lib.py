# -*- coding: utf-8 -*-

from zope.interface.advice import addClassAdvisor
import sys

from .error import  Invalid

import logging, inspect
log = logging.getLogger(__name__)


class PASS:
    pass

class __MISSING__( str ):
    def __str__(self):
        return ''

    __unicode__ = __str__

MISSING = __MISSING__()

def _append_list(klass, key, data):
    key = "__%s__" % key
    setattr\
        ( klass
        , key
        , list(getattr(klass,key,[])) + list(data)
        )

def _merge_dict(klass, key, data):
    log.debug('merge dict %s in %s' % ( key, klass ))

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
   
    log.debug('%s.__%s__ = %s' % (  klass, key, getattr( klass, key ) ))

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

    for key,(data, callback)  in advice_data.items():
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

"""
def messages(**fields):
    _advice('messages', _merge_dict, fields )
"""

"""
def inherit(*keys):
    _advice('inherit', _append_list, keys)
"""



def defaultErrorFormatter( context, error ):
    return error.message % (error.extra)

class Context( dict ):

    __value__ = MISSING
    __error__ = MISSING
    __result__ = MISSING

    parent = None
    root = None
    key = '/'

    isValidated = False
    isValidating = False

    taggedValidators = {}
    indexKeyRelation = {}
    numValues = 0

    def __init__(self, validator=None, value=MISSING, key='/', parent=None):
        if parent is not None:
            self.parent = parent
            self.root = parent.root
            self.key = key

            sep = self.root is not parent and '.' or ''

            self['path'] = '%s%s%s' % (parent.path,sep,key)
        else:
            self.root = self
            self.errorFormatter = defaultErrorFormatter
            self['path'] = key

        self.validator = validator
        self.value = value

    @property
    def path(self):
        return self['path']

    @property
    def childs(self):
        childs = self.get('childs',None)
        if childs is None:
            childs = self[ 'childs' ] = {}
        return childs

    @property
    def errorlist(self):
        errorlist = self.get('errorlist',None)
        if errorlist is None:
            errorlist = self[ 'errorlist' ] = []
        return errorlist

    @property
    def updates(self):
        updates = self.get('updates',None)
        if updates is None:
            updates = self[ 'updates' ] = []
        return updates

    @property
    def value(self):
        return self.get('value',self.__value__)

    @value.setter
    def value( self, value):
        if value is self.value:
            return

        if self.root.isValidating:
            self['value'] = value
            self.root.updates.append( self.path )
            return

        if (value == '') or value is [] or value is {}:
            value = None

        self.__value__ = value
        self.clear()

    @property
    def result(self):
        return self.validate()

    @property
    def error(self):
        return self.__error__.__unicode__()

    @error.setter
    def error( self, error ):
        self.__error__ = error
        error.context = self

        message = error.validator.__messages__[error.key]

        if message is not None:
            extra = error.data['extra']
            value = error.value
            data = error.data

            data['message'] = message
            if hasattr(error,'realkey'):
                data['key'] = error.realkey

            extra['value.type'] = getattr(value, '__class__', None) is not None \
                and getattr(value.__class__,'__name__', False) or 'unknown'

            if isinstance(value,str):
                extra['value'] = value
            else:
                extra['value'] = str(value)

            cache = getattr( self, 'cache', None)
            if cache is not None:
                extra.update( cache )

            self['error'] = self.__error__.data

            if self.__error__.context.path not in self.root.errorlist:
                self.root.errorlist.append( self.__error__.context.path )

    @property
    def validator(self):
        if not hasattr(self, '__validator__'):
            return None
        return self.__validator__

    @validator.setter
    def validator(self,value):
        self.__validator__ = value
        self.clear()

    def setIndexFunc( self, func ):
        self.__result__ = MISSING
        self.__error__ = MISSING
        self.indexKeyRelation = {}

        if func is not None:
            self.indexFunc = func
        elif hasattr( self, 'indexFunc'):
            del self.indexFunc

    def getKeyByIndex( self, index ):
        key = self.indexKeyRelation.get( index, None )
        if key is not None:
            return key

        indexFunc = getattr(self,'indexFunc',None)
        if indexFunc:
            if not self.indexKeyRelation:
                self.numValues = len(self.childs)

            self.indexKeyRelation[ index ] = indexFunc( index )
            return self.indexKeyRelation[ index ]
        else:
            raise SyntaxError('Context %s has no childs supporting indexing' % (self.path))

    def clear( self, force=False ):
        if not self.isValidated and not force:
            return

        dict.clear( self )

        if self.parent is not None and self.parent.path:
            self['path'] = '%s.%s' % (self.parent.path,self.key)
        else:
            self['path'] = self.key

        self.isValidated = False

        self.__result__ = MISSING
        self.__error__ = MISSING

    def validate( self ):
        if self.isValidated:
            if self.__error__ is not MISSING:
                raise self.__error__
            return self.__result__

        self.isValidating = True

        if self.parent is not None:

            if not self.parent.isValidated and not self.parent.isValidating:
                self.parent.validate()

        if self.validator is None:
            raise AttributeError("No validator set for context '%s'" % self.path )

        result = PASS
        try:
            result = self.validator.validate( self, self.__value__)

        except Invalid as e:
            self.error = e
            raise e
        else:
            if result is not PASS:
                self.__result__ = result
            else:
                self.__result__ = self.__value__

            return self.__result__
        finally:
            self.isValidated = True
            self.isValidating = False




    """
    def populate(self ):
        if self.isPopulated:
            if 'value' in self:
                return self['value']
            return self.__value__

        if self.parent is not None:
            self.parent.populate()

        schemaData = None
        if self.parent:
            schemaData = getattr(self.parent,'currentSchemaData',None)

        if self.validator is None:
            raise AttributeError("No validator set for context '%s'" % self.path )

        result = PASS
        try:
            if schemaData:
                result = schemaData.validationFunc( self, schemaData )
            else:
                result = self.validator.validate( self, self.__value__)
        except Invalid as e:
            self.__error__ = e

        if not self.__error__:
            if result is not PASS:
                self.__result__ = result
            else:
                self.__result__ = self.__value__

        self.isPopulated = True
        if not 'value' in self:
            self['value'] = self.__value__

        return self['value']

    def validate(self ):

        if not self.isPopulated:
            self.populate()

        if not self.isValidated:

            if self.__result__ is not MISSING:
                self['result'] = self.__result__
            elif self.__error__ is not MISSING:
                self.errorlist.append( self.path )
                self['error'] = self.__error__

            self.isValidated = True

        if self.__error__ is MISSING:
            return self.__result__

        raise self.__error__
    """

    def __call__( self, path ):
        if path.__class__ is int:
            if path < 0:
                path = self.numValues+path

            return self( self.getKeyByIndex( path ) )
        elif not path:
            raise SyntaxError('Path cannot be empty')

        path = path.split('.',1)

        try:
            child = self.childs[path[0]]
        except KeyError:
            child = self.childs[path[0]] = Context( key=path[0], parent=self )

        if(len(path)==1):
            return child
        else:
            path=path[1]

        return child(path)


from .util import varargs2kwargs
# Some kind of 'clonable' object -
# we reinitialize child objects with inherited kwargs merged with new ones.
# This allows us to alter just a few specific parameters in child objects.
# without the need for implementors of validators to provide setters or too
# much specification for their attributes or how they are provided.
# * the setParameters function will be inspected, so that it will use
#   named parameters as kwargs, regardless if they are provided as *args
#   ( you cannot use *varargs in setParameters )
# * you can also define a setArguments function, which will be called before
#   setParameters, using the provided *varargs. keywords defined in
#   setParameters will not be moved from *args to **kwargs when setArguments
#   is defined. You can use it for attributes you only want to initialize
#   once. It also allows you to 'name' *varargs in the function definition.
# * __inherit__ specifies what attributes should be copied to child instances.
class Parameterized:
    __kwargs__ = {}
    __inherit__ = [ ]
    __isRoot__ = True

    __ignoreClassParameters__ = []

    def __init__( self, *args, **kwargs ):
        parent = kwargs.pop( '_parent', None )

        if not hasattr( self, 'setArguments') and args:
            func = getattr( self, 'setParameters', None)
            if func is not None:
                ( args, kwargs, shifted ) = varargs2kwargs( func, args, kwargs )

        if parent is not None:
            self.__isRoot__ = False
            newkwargs = dict(parent.__kwargs__ )
            newkwargs.update(kwargs)
            kwargs = newkwargs

            for key in self.__inherit__:
                setattr(self, key, getattr(parent, key))
        else:
            for key in self.__getParameterNames__():
                if hasattr(self.__class__,key)\
                and not key in self.__ignoreClassParameters__\
                and not key in kwargs:
                    kwargs[key] = getattr(self.__class__, key)

        if args or (parent is None):
            if hasattr( self, 'setArguments' ):
                self.setArguments( *args )
            elif args:
                raise SyntaxError('%s takes no further arguments' % self.__class__.__name__)

        if hasattr( self, 'setParameters' ):
            try:
                self.setParameters( **kwargs )
            except TypeError as e:
                raise TypeError(self.__class__.__name__+': '+e[0])

        elif kwargs:
            raise SyntaxError('%s takes no parameters' % self.__class__.__name__)

        self.__kwargs__ = kwargs

    def __call__( self, *args, **kwargs):
        kwargs['_parent'] = self
        return self.__class__( *args, **kwargs )


    @classmethod
    def __getParameterNames__( klass ):
        if not hasattr( klass, '__parameterNames__'):
            if not hasattr( klass, 'setParameters'):
                names = ()
            else:
                spec = inspect.getargspec( klass.setParameters )
                if spec.varargs:
                    raise SyntaxError('Cannot use *varargs in setParameters, please use %s.setArguments' % klass.__name__)
                names = spec.args[1:]
            setattr\
                ( klass,'__parameterNames__'
                , names
                )
        return klass.__parameterNames__

def inherit( *members ):
    def decorate( klass ):
        klassInherits = list(getattr(klass,'__inherit__', [] ))
        klassInherits += members

        setattr( klass, '__inherit__', klassInherits )
        return klass

    return decorate

