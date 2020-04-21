# I dont understand how discord.py uses asyncio so basically we are just going to use its event loop for everything else and hope that it doesn't exit when something discord related happens...
# Each guild MAX connects to should have its own JSON file (database for tinyDB) containing config for the guild, as well as for things like access/refresh tokens for youtube and spotify
# Imported discord.py api wrapper as disc so that we can just call our discord client "discord"

import tinydb
import asyncio
import MAXDiscord

def main():
    print("MAX is alive again.")

    query = tinydb.Query()
    authDB = tinydb.TinyDB('MAXAuth.json', indent=4, separators=(',', ': '))
    configDB = tinydb.TinyDB('MAXConfig.json', indent=4, separators=(',', ': '))
    dev = configDB.get(query.name == 'dev')['value']
    
    # gets the current event loop or i guess creates one (there can only ever be one running event loop)
    loop = asyncio.get_event_loop()
    # schedules a task to run on the event loop next time the event loop checks for stuff, unless the event loop got closed!! (which is why we run forever, otherwise it wont even start them)
    loop.create_task(MAXDiscord.engage(query, authDB, configDB, configDB.table('discord'), dev))
    # makes the event loop run forever (this is blocking), so any current and future scheduled tasks will run until we explicitly tell the loop to die with loop.stop()
    loop.run_forever()

if __name__ == '__main__':
    main()