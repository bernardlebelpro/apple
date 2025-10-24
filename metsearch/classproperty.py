class classproperty(property):
    """Turn a class variable into a property-like attribute.

    Just like the @property decorator,
    decorate your class method with @classproperty.

    Ex:
        class A(object):
            _yeah = 'yeah'

            @classproperty
            def myprop(cls):

                return cls._yeah
    """

    def __get__(self, instance, owner):
        return self.fget(owner)
