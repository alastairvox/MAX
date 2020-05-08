import tinydb
import functools

global query
query = tinydb.Query()
global configPath
configPath = 'MAXConfig/'

global auth
auth = tinydb.TinyDB(configPath + 'MAXAuth.json', indent=4, separators=(',', ': '))
global generalConfig
generalConfig = tinydb.TinyDB(configPath + 'MAXGeneralConfig.json', indent=4, separators=(',', ': '))
global devFlag
devFlag = generalConfig.get(query.name == 'dev')['value']

global discordConfig
discordConfig = tinydb.TinyDB(configPath + 'MAXDiscordConfig.json', indent=4, separators=(',', ': '))
global twitchConfig
twitchConfig = tinydb.TinyDB(configPath + 'MAXTwitchConfig.json', indent=4, separators=(',', ': '))
global youtubeConfig
youtubeConfig = tinydb.TinyDB(configPath + 'MAXYoutubeConfig.json', indent=4, separators=(',', ': '))

global dayNames
dayNames = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
global fullDayNames
fullDayNames = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
global specialRoles
specialRoles = ['default', 'everyone', 'here', 'none']

# adds the name of the module into the print command so I can easily tell where print statements originated from
def printName(function, name):
    @functools.wraps(function)
    def wrappedFunction(*args,**kwargs):
        return function(name,*args,**kwargs)
    return wrappedFunction