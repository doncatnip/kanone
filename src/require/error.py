class Invalid(BaseException):
    context = None

    def __init__(self, value, _validator=None, _key='fail', **kwargs):
        if _validator is not None:
            self.validator = _validator
        self.value = value
        self.data = {'key': _key, 'extra': kwargs}

    @property
    def key(self):
        return self.data['key']

    @key.setter
    def key(self, value):
        self.data['key'] = value

    @property
    def message(self):
        return self.data.get('message',None)

    @property
    def extra(self):
        return self.data['extra']

    def __repr__(self):
        return 'Invalid(%s, %s)' % (self.value, self.key)

    def __str__(self):
        return self.__unicode__().encode('utf8')

    def __unicode__(self):
        if self.context is not None and self.message is not None:
            return self.context.root.errorFormatter( self.context, self )
        else:
            return self.__repr__()

