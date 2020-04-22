import tinydb
import functools

global query
query = tinydb.Query()
global authDB
authDB = tinydb.TinyDB('MAXAuth.json', indent=4, separators=(',', ': '))
global configDB
configDB = tinydb.TinyDB('MAXConfig.json', indent=4, separators=(',', ': '))
global dev
dev = configDB.get(query.name == 'dev')['value']

# adds the name of the module into the print command so I can tell where print statements originated from
def printName(function, name):
    @functools.wraps(function)
    def wrappedFunction(*args,**kwargs):
        return function(name,*args,**kwargs)
    return wrappedFunction