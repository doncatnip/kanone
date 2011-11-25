from .core import ValidatorBase

class Print( ValidatorBase ):

    def __init__( self, formatter):
        self.formatter=formatter

    def validate( self, context, value):
        print(( self.formatter % {'value':value} ))
        return value
