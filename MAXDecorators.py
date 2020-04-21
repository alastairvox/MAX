import functools

# adds the name of the module into the print command so I can tell where print statements originated from
def printName(function, name):
    @functools.wraps(function)
    def wrappedFunction(*args,**kwargs):
        return function(name,*args,**kwargs)
    return wrappedFunction