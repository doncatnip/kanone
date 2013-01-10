""" Twisted adapter for Kanone """

from twisted.python.failure import Failure
from twisted.internet import defer
from ..lib import Invalid
from ..util import varargs2kwargs

import logging, sys
log = logging.getLogger( __name__ )

# hacky and redundant, but it'll do for now ..
# TODO: move to proper twisted specific classes under .tx.*
#       and get rid of the monkey

_python3 = sys.version_info[0]>=3

def monkeyPatch():
    """
    Patches Kanone so that any validation returns a Deferred, thus
    one can write asynchronous validators using Twisted's non-blocking API.
    Schema and ForEach fields are validated concurrently.
    """
    if getattr( monkeyPatch,'_isMonkeyPatched',False):
        return

    from ..lib import Context, PASS, MISSING

    from ..validator.core import Tag, Compose, Tmp, Item, Not, And, Or, Call, If
    from ..validator.check import Match
    from ..validator.schema import Schema, ForEach, Field
    from ..validator.web import MXLookup

    @defer.inlineCallbacks
    def context_validate( self ):
        if self.isValidated:
            if self.__error__ is not MISSING:
                raise self.__error__

            defer.returnValue( self.__result__ )

        self.isValidating = True

        if self.parent is not None:

            if not self.parent.isValidated and not self.parent.isValidating:
                yield defer.maybeDeferred\
                    ( self.parent.validate
                    )

        if not self.validator:
            raise AttributeError("No validator set for context '%s'" % self.path )

        result = defer.maybeDeferred\
            ( self.validator.validate
            , self
            , self.__value__
            )

        result.addErrback( context_gotError, self )
        result = yield result

        self.isValidated = True
        self.isValidating = False

        if self.__error__ is not MISSING:
            raise self.__error__
        else:
            if result is not PASS:
                self.__result__ = result
            else:
                self.__result__ = self.__value__

            self.__result__ = result

        defer.returnValue( result )


    def context_gotError( error, self ):

        e = error.value 

        if not isinstance( e, Invalid ):
            self.__error__ = error
            return

        self.__error__ = e
        e.context = self
        message = e.validator.__messages__[e.key]

        if message is not None:
            extra = e.data['extra']
            value = e.value
            data = e.data

            data['message'] = message
            if hasattr(e,'realkey'):
                data['key'] = e.realkey

            extra['value.type'] = getattr(value, '__class__', None) is not None \
                and getattr(value.__class__,'__name__', False) or 'unknown'

            if isinstance(value,str) or not _python3 and isinstance(value,basestring):
                extra['value'] = value
            else:
                extra['value'] = str(value)

            cache = getattr( self, 'cache', None)
            if cache is not None:
                extra.update( cache )

            self['error'] = self.__error__.data

            self.root.errorlist.append( self.__error__.context.path )


    def tag_gotResult( result, d, validator, tagName ):
        if isinstance( result, Failure ):
            if not isinstance(result.value, Invalid):
                d.errback( result )
                return

            e = result.value
            if e.validator is validator or getattr(e,'composer',None) is validator:
                e.tagName = tagName
            d.errback( e )
        else:
            d.callback( result )


    def tag_validate( self, context, value ):
        validator = context.root.taggedValidators.get(self.tagID, None)
        if validator is None:
            validator = self.enabled and self.validator

        if not validator:
            return value

        d = defer.Deferred()
        result = defer.maybeDeferred\
                ( validator.validate
                , context
                , value
                )
        result.addBoth( tag_gotResult, d, validator, self.tagName )
        return d

    def compose_gotResult( result, d, context, tmpTags, composer ):
        context.root.taggedValidators = tmpTags

        if isinstance( result, Failure ):
            if not isinstance( result.value, Invalid ):
                d.errback( result )
                return

            e = result.value

            if hasattr(e,'tagName'):
                e.realkey = "%s_%s" % (e.tagName, getattr(e,'realkey',e.key))
                e.composer = composer
                del e.tagName
            d.errback( e )
        else:
            d.callback( result )



    def compose_validate( self, context, value ):
        tmpTags = context.root.taggedValidators
        context.root.taggedValidators = self.currentTaggedValidators

        d = defer.Deferred()
        result = defer.maybeDeferred\
            ( self.validator.validate
            , context
            , value
            )
        result.addBoth( compose_gotResult, d, context, tmpTags, self )
        return d

    def tmp_gotReslt( result, d, raiseError, value ):
        if isinstance( result, Failure ):
            if not isinstance(result.value, Invalid):
                d.errback( result )
                return

            if raiseError:
                d.errback( result.value )
                return

        d.callback( value )

    def tmp_validate( self, context, value ):
        d = defer.Deferred()
        result = defer.maybeDeferred\
                ( self.validator.validate
                , context
                , value
                )
        result.addBoth( tmp_gotReslt, d, self.raiseError, value )
        return d

    def item_gotResult( result, d, value, key, alter ):
        if isinstance( result, Failure ):
            if not isinstance(result.value, Invalid):
                d.errback( result )
                return
            d.errback( result.value )
        else:
            if alter:
                value[key] = result

            d.callback( value )

    def item_validate( self, context, value ):
        try:
            val = value[ self.key ]

        except TypeError:
            raise Invalid( value, self, 'type' )
        except (KeyError, IndexError):
            raise Invalid( value, self, 'notFound', key=self.key )
        else:
            if self.validator is not None:
                d = defer.Deferred()
                result = defer.maybeDeferred\
                    ( self.validator.validate
                    , context
                    , val
                    )
                result.addBoth( item_gotResult, d , value, self.key, self.alter )
                return d
            else:
                return val

    def not_gotResult( result, d, value, validator ):
        if isinstance( result, Failure ):
            if not isinstance( result.value, Invalid ):
                d.errback( result )
                return
            d.callback( value )
        else:
            d.errback( Invalid( value, validator ) )

    def not_validate(self, context, value ):
        d = defer.Deferred()
        result = defer.maybeDeferred\
            ( self.validator.validate
            , context
            , value
            )
        result.addBoth( not_gotResult, d, value, self )
        return d

    def and_doTryNext( result, validators, context, value, d ):
        if isinstance( result, Failure ):
            if not isinstance(result.value, Invalid):
                d.errback( result )
            else:
                e = result.value
                d.errback( e )
        else:
            if validators:
                and_tryNext( validators, context, result, d )
            else:
                d.callback( result )

    def and_tryNext( validators, context, value, d ):
        result = defer.maybeDeferred\
            ( validators.pop(0).validate
            , context
            , value
            )

        result.addBoth( and_doTryNext, validators, context, value, d )

    def and_validate( self, context, value ):
        d = defer.Deferred()
        and_tryNext( list( self.validators ), context, value, d )
        return d

    def or_doTryNext( result, validators, context, value, d ):
        if isinstance( result, Failure ):
            err = result
        
            if not isinstance(err.value, Invalid):
                d.errback( err )
                return

            e = err.value
            if not validators:
                d.errback( e )
            else:
                or_tryNext( validators, context, value, d )
        else:
            d.callback( result )

    def or_tryNext( validators, context, value, d ):
        result = defer.maybeDeferred\
            ( validators.pop(0).validate
            , context
            , value
            )

        result.addBoth( or_doTryNext, validators, context, value, d )

    def or_validate( self, context, value ):
        d = defer.Deferred()
        or_tryNext( list(self.validators), context, value, d )
        return d



    @defer.inlineCallbacks
    def call_validate( self, context, value ):
        try:
            result = yield defer.maybeDeferred\
                ( self.__func__
                , context
                , value
                )
        except Failure as e:
            if not isinstance(e.value, Invalid):
                raise
            e = e.value
            e.validator = self
            raise e
        else:
            defer.returnValue( result )

    def match_gotResult( result, self, value, d ):
        if isinstance( result, Failure ):
            if not isinstance(result.value, Invalid):
                raise

            d.errback( Invalid( value, self, matchType=self.type, criterion=result.value ) )
        else:
            val = value
            if self.ignoreCase:
                result = str(result).lower()
                val = str(value).lower()

            if val != result:
                d.errback( Invalid( value, self, matchType=self.type, criterion=result ) )
            else:
                d.callback( value )
           

    def match_on_value(self, context, value ):
        if self.type is Match.REGEX:
            if not self.criterion.match(value):
                raise Invalid( value, self, matchType=self.type, criterion=self.criterion.pattern)
            return value
        elif self.type is Match.VALIDATOR:
            compare = defer.maybeDeferred\
                ( self.criterion.validate
                , context
                , value
                )

            d = defer.Deferred()
            compare.addBoth( match_gotResult, self, value, d )
            return d
        else:
            compare = self.criterion

        val = value
        if self.ignoreCase:
            compare = str(compare).lower()
            val = str(value).lower()

        if val != compare:
            raise Invalid( value, self, matchType=self.type, criterion=compare )

        return value


    def if_gotResult( result, d, context, value ):
        if isinstance( result, Failure ):
            if not isinstance(result.value, Invalid):
                d.errback( result )
            else:
                d.errback( result.value )
        else:
            d.callback( result )

    def if_gotResultExpression( result, validator, d, context, value ):
        if isinstance( result, Failure ):
            if not isinstance( result.value, Invalid):
                raise
            value = defer.maybeDeferred\
                ( validator._else.validate, context, value
                )
        else:
            value = defer.maybeDeferred\
                ( validator._then.validate, context, result
                )

        value.addBoth( if_gotResult, d, context, value )

    def if_validate( self, context, value ):
        d = defer.Deferred()
        result = defer.maybeDeferred( self.criterion.validate, context, value )
        result.addBoth( if_gotResultExpression, self, d, context, value )
        return d

    def schema_gotResult( result, resultset, key, isList, returnList ):
        if returnList:
            resultset.append( result )
        else:
            resultset[ key ] = result

        return result

    def schema_gotError( error, errorset, key ):
        if isinstance( error, Failure ):
            if not isinstance(error.value, Invalid):
                raise error

            error = error.value

        errorset.append( error )

    def schema__on_value_done( waste, d, schema, value, result, errors ):
        if not errors:
            d.callback( result )
        else:
            d.errback( errors.pop(0) )

    def schema__createContextChildren_on_value_done( waste, d, schema, value, result, errors ):
        if not errors:
            d.callback( result )
        else:
            d.errback( Invalid( value, schema ) )

    def schema__on_value( self, context, value ):
        isList = isinstance(value, list) or isinstance(value,tuple) or isinstance(value,set)
        if not isList and not isinstance( value, dict ):
            raise Invalid( value, self, 'type')

        extraFields = None
        if not self.allowExtraFields:
            if isList:
                extraFields = max( len(value), len(self.index) )
            else:
                extraFields = list(value.keys())

        if self.returnList:
            result = []
        else:
            result = {}

        numValues = len(value)
        jobs = []

        errorset = []
        for pos in range(len(self.index)):
            key = self.index[pos]
            if isList:
                if numValues>pos:
                    val = value[ pos ]
                    if not self.allowExtraFields:
                        extraFields-=1
                else:
                    val = MISSING
            else:
                val = value.get( key, MISSING)
                if not self.allowExtraFields and val is not MISSING:
                    try: extraFields.remove(key)
                    except: pass

            job = defer.maybeDeferred\
                ( self.validators[ key ].validate
                , context
                , val
                )

            jobs.append\
                ( job.addCallback( schema_gotResult, result, key, isList, self.returnList )\
                    .addErrback( schema_gotError, errorset, key )
                )

        if extraFields:
            raise Invalid( value, self, 'extraFields',extraFields=extraFields)

        d = defer.Deferred()
        jobs =defer.DeferredList( jobs )
        jobs.addCallback\
            ( schema__on_value_done
            , d
            , self
            , value
            , result
            , errorset
            )

        return d

    def schema__createContextChildren_on_value( self, context, value ):
        isList = isinstance(value, list) or isinstance(value,tuple) or isinstance(value,set)

        if not isList and not isinstance( value, dict ):
            raise Invalid( value, self, 'type')

        extraFields = None
        if not self.allowExtraFields:
            if isList:
                extraFields = max( len(value), len(self.index) )
            else:
                extraFields = list(value.keys())

        errors = []

        if self.returnList:
            result = []
        else:
            result = {}

        len_value = len(value)
        len_index = len(self.index)

        # populate
        for pos in range(len_index):
            key = self.index[pos]
            childContext = context( key )
            try:
                childContext.validator = self.validators[ key ]
            except KeyError:
                raise SyntaxError("No validator set for %s" % childContext.path)

            if isList:
                if len_value<=pos:
                    childContext.__value__ = MISSING
                else:
                    childContext.__value__ = value[ pos ]
            else:
                childContext.__value__ = value.get( key, MISSING )

            if not self.allowExtraFields:
                if isList:
                    extraFields-=1
                else:
                    try: extraFields.remove(key)
                    except: pass

        if extraFields:
            raise Invalid( value, self, 'extraFields',extraFields=extraFields)

        context.setIndexFunc( lambda index: self.index[index] )

        jobs = []

        # validate
        for key in self.index:

            jobs.append\
                ( context( key ).result\
                    .addCallback( schema_gotResult, result, key, isList, self.returnList )\
                    .addErrback( schema_gotError, errors, key )
                )

        d = defer.Deferred()
        jobs = defer.DeferredList( jobs )
        jobs.addCallback\
            ( schema__createContextChildren_on_value_done
            , d
            , self
            , value
            , result
            , errors
            )

        return d

    def forEach__on_value( self, context, value ):
        if self.returnList:
            result = []
        else:
            result = {}

        isList = isinstance( value, list) or isinstance(value, tuple) or isinstance(value, set)
        errorset = []
        jobs = []
        if isList or self.numericKeys:
            for pos in range( len( value ) ):
                if not isList:
                    val = value.get(str(pos),MISSING)
                    if val is MISSING:
                        raise Invalid( value, self, 'numericKeys', keys=list(value.keys()) )
                else:
                    val = value[pos]
                key = str(pos)
                jobs.append\
                    ( defer.maybeDeferred\
                        ( self.validator.validate
                        , context, val
                        ).addCallback\
                            ( schema_gotResult
                            , result
                            , key
                            , isList
                            , self.returnList
                            )\
                        .addErrback\
                            ( schema_gotError
                            , errorset
                            , key
                            )
                    )
        else:
            for (key, val) in value.items():

                jobs.append\
                    ( defer.maybeDeferred\
                        ( self.validator.validate
                        , context, val
                        ).addCallback\
                            ( schema_gotResult
                            , result
                            , key
                            , isList
                            , self.returnList
                            )\
                        .addErrback\
                            ( schema_gotError
                            , errorset
                            , key
                            )
                    )

        d = defer.Deferred()
        jobs = defer.DeferredList( jobs )
        jobs.addCallback\
            ( schema__on_value_done
            , d
            , self
            , value
            , result
            , errorset
            )

        return d


    def forEach__createContextChildren_on_value( self, context, value ):
        isList = isinstance( value, list) or isinstance(value, tuple) or isinstance(value, set)

        if not isList:
            if not isinstance(value, dict ):
                raise Invalid( value, self,'type' )

        if self.returnList:
            result = []
        else:
            result = {}
        errors = []

        # populate
        children = []
        if isList or self.numericKeys:
            context.setIndexFunc( lambda index: str(index) )

            for pos in range( len( value ) ):
                if not isList:
                    val = value.get(str(pos),MISSING)
                    if value.get(str(pos),MISSING) is MISSING:
                        context.setIndexFunc( None )
                        raise Invalid( value, self, 'numericKeys',keys=list(value.keys()))

                else:
                    val = value[ pos ]

                contextChild = context( str( pos ) )
                contextChild.validator = self.validator
                contextChild.__value__ = val
                children.append( contextChild )

        else:
            context.setIndexFunc( None )

            if self.returnList:
                raise Invalid( value, self, 'listType' )
            for (key,val) in value.items():
                contextChild = context( key )
                contextChild.validator = self.validator
                contextChild.__value__ = val
                children.append( contextChild )

        jobs = []
        #validate
        for childContext in children:
            jobs.append\
                ( childContext.validate()\
                    .addCallback\
                        ( schema_gotResult
                        , result
                        , childContext.key
                        , isList
                        , self.returnList
                        )\
                    .addErrback\
                        ( schema_gotError
                        , errors
                        , childContext.key
                        )
                )

        d = defer.Deferred()
        jobs = defer.DeferredList( jobs )
        jobs.addCallback\
            ( schema__createContextChildren_on_value_done
            , d
            , self
            , value
            , result
            , errors
            )

        return d



    @defer.inlineCallbacks
    def field_validate(self, context, value):
        fieldcontext = self.getField( context, self.path )

        if not self.useResult:
            result = fieldcontext.value

        else:
            try:
                result = yield fieldcontext.result
            except Invalid:
                result = PASS

        if self.validator is not None:
            if result is not PASS:
                result = yield defer.maybeDeferred\
                    ( self.validator.validate
                    , fieldcontext, result
                    )

        if self.writeToContext:
            fieldcontext.__result__ = result

        if self.copy:
            if result is PASS:
                defer.returnValue( value )

            defer.returnValue( result )

        defer.returnValue( value )

    from twisted.names import client
    from twisted.names.dns import Record_MX
    from twisted.names.error import DNSNameError
    from twisted.internet.defer import TimeoutError

    def mxLookup_gotResult(result, d, value, validator, context ):
        if isinstance( result, Failure ):
            if isinstance(result.value, TimeoutError):
                d.errback( Invalid( value, validator ) )
            elif not isinstance(result.value, DNSNameError):
                d.errback( result )
            else:
                d.errback( Invalid( value, validator ) )
            return

        (answers, auth, add) = result
        if not len(answers):
            d.errback( Invalid( value, validator ) )
        else:
            for record in answers:
                if isinstance(record.payload,Record_MX):
                    d.callback( value )
                    return

            d.errback( Invalid( value, validator ) )

    mxLookup_resolver = client.Resolver('/etc/resolv.conf')
    def mxLookup_on_value( self, context, value ):
        d = defer.Deferred()
        mxLookup_resolver.lookupMailExchange( value, [2,4,6,8,10] )\
            .addBoth( mxLookup_gotResult, d, value, self, context )

        return d


    Context.validate = context_validate
    Tag.validate = tag_validate
    Compose.valdate = compose_validate
    Tmp.validate = tmp_validate
    Item.validate = item_validate
    Not.validate = not_validate
    And.validate = and_validate
    Or.validate = or_validate
    Call.validate = call_validate
    Match.on_value = match_on_value
    If.validate = if_validate
    Schema._on_value = schema__on_value
    Schema._createContextChildren_on_value = schema__createContextChildren_on_value
    ForEach._on_value = forEach__on_value
    ForEach._createContextChildren_on_value = forEach__createContextChildren_on_value
    Field.validate = field_validate
    MXLookup.on_value = mxLookup_on_value

    monkeyPatch._isMonkeyPatched = True

from ..util import getArgSpec, getParameterNames



def validateDecorator_gotValidationResult\
        ( result
        , d
        , origArgs
        , origKwargs
        , method
        , varargs
        , keywords
        , shifted
        , onInvalid
        ):

    if isinstance( result, Failure ):
        if not isinstance(result.value, Invalid):
            d.errback( result )
        elif onInvalid is not None:
            try:
                result = onInvalid( result.value )
            except Exception as e:
                d.errback( e )
            else:
                d.callback( result )
        else:
            d.errback( result )

    else:
        origKwargs.update( result )
        
        resultArgs = origKwargs.pop( varargs, origArgs )
        resultArgs = [ origKwargs.pop(key) for key in shifted  ] + resultArgs
        
        if keywords is not False:
            origKwargs.update( origKwargs.pop( keywords ) )
        
        defer.maybeDeferred( method, *resultArgs, **origKwargs )\
            .chainDeferred( d )
   

def validateDecorator( validator, method, include, exclude, onInvalid, inlineCallbacks ):

    if include and exclude:
        raise SyntaxError("'include' and 'exclude' cannot be used at the same time")

    spec = getArgSpec( method )
    hasVarargs = spec.varargs is not None
    varargs =  spec.varargs or '*varargs'
    keywords = spec.keywords or False

    methodParameterNames = getParameterNames( method, skipSelf=False )

    skip = ()
    if exclude:
        skip = exclude
    if include:
        skip = set(methodParameterNames) - set(include)

    varargs    = varargs

    hasVarargs = spec.varargs not in skip and hasVarargs

    keywords   = keywords not in skip and keywords

    if inlineCallbacks:
        method = defer.inlineCallbacks( method )

    def __wrap( *fargs, **fkwargs):

        d = defer.Deferred()

        (fargs, fkwargs, shifted ) = varargs2kwargs( method, fargs, fkwargs, skipSelf=False )
        origKwargs = dict(fkwargs)

        if keywords is not False:
            restKwargs = dict(\
                ( key, fkwargs.pop(key))\
                    for key in list(fkwargs.keys()) if key not in methodParameterNames
                )
            fkwargs[ keywords ] = restKwargs

        if fargs or hasVarargs:
            fkwargs[ varargs ] = list(fargs)

        result = validator.context\
            ( dict( ( key, fkwargs[ key] ) for key in fkwargs if key not in skip )
            ).result

        result.addBoth( validateDecorator_gotValidationResult, d, fargs, origKwargs, method, varargs, keywords, shifted, onInvalid )

        return d

    return __wrap

def validate( validator, include=None, exclude=None, onInvalid=None, inlineCallbacks=False ):
    def __createDecorator( method ):
        return validateDecorator( validator, method, include, exclude, onInvalid, inlineCallbacks)
    return __createDecorator

