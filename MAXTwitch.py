import asyncio, datetime, traceback, dateutil.parser, tinydb, tinydb.operations, copy, enum
import twitchio, twitchio.ext.commands
import MAXShared, MAXDiscord, MAXServer
from MAXShared import auth, discordConfig, twitchConfig, query, devFlag, dayNames

# overloads print for this module so that all prints (hopefully all the sub functions that get called too) are appended with which service the prints came from
print = MAXShared.printName(print, "TWITCH:")



# ---------- SETUP ------------------------------------------------------------------------------------------------------------
#        #######                                               
#      /       ###                                             
#     /         ##              #                              
#     ##        #              ##                              
#      ###                     ##                              
#     ## ###           /##   ######## ##   ####        /###    
#      ### ###        / ### ########   ##    ###  /   / ###  / 
#        ### ###     /   ###   ##      ##     ###/   /   ###/  
#          ### /##  ##    ###  ##      ##      ##   ##    ##   
#            #/ /## ########   ##      ##      ##   ##    ##   
#             #/ ## #######    ##      ##      ##   ##    ##   
#              # /  ##         ##      ##      ##   ##    ##   
#    /##        /   ####    /  ##      ##      /#   ##    ##   
#   /  ########/     ######/   ##       ######/ ##  #######    
#  /     #####        #####     ##       #####   ## ######     
#  |                                                ##         
#   \)                                              ##         
#                                                   ##         
#                                                    ##        
# ---------- SETUP ------------------------------------------------------------------------------------------------------------



# gets the table/subsection of config for this service
config = twitchConfig

twitchToken = auth.get(query.name == 'twitch')['devToken'] if devFlag else auth.get(query.name == 'twitch')['token']
twitchClientID = auth.get(query.name == 'twitch')['devClientID'] if devFlag else auth.get(query.name == 'twitch')['clientID']
twitchNick = auth.get(query.name == 'twitch')['devNick'] if devFlag else auth.get(query.name == 'twitch')['nick']
twitchClientSecret = auth.get(query.name == 'twitch')['devClientSecret'] if devFlag else auth.get(query.name == 'twitch')['clientSecret']

initialChannels = []
for entry in discordConfig.all():
    for name in entry['ownerNames']:
        if name not in initialChannels:
            initialChannels.append(name)

# localHost = '192.168.50.62'
# externalHost = '172.103.254.14'
# port = '81'
# callback = 'twitchcallback'

# bot = twitchio.ext.commands.Bot(irc_token=twitchToken, client_id=twitchClientID, prefix="!", nick=twitchNick, initial_channels=initialChannels, webhook_server=True, local_host=localHost, external_host=externalHost, port=port, callback=callback)

bot = twitchio.ext.commands.Bot(irc_token=twitchToken, client_id=twitchClientID, prefix="!", nick=twitchNick, initial_channels=initialChannels, client_secret=twitchClientSecret)



# ---------- FUNCTIONS --------------------------------------------------------------------------------------------------------
#       ##### ##                                                                                    
#    ######  /### /                                           #                                     
#   /#   /  /  ##/                                    #      ###                                    
#  /    /  /    #                                    ##       #                                     
#      /  /                                          ##                                             
#     ## ##    ##   ####    ###  /###     /###     ######## ###       /###   ###  /###      /###    
#     ## ##     ##    ###  / ###/ #### / / ###  / ########   ###     / ###  / ###/ #### /  / #### / 
#     ## ###### ##     ###/   ##   ###/ /   ###/     ##       ##    /   ###/   ##   ###/  ##  ###/  
#     ## #####  ##      ##    ##    ## ##            ##       ##   ##    ##    ##    ##  ####       
#     ## ##     ##      ##    ##    ## ##            ##       ##   ##    ##    ##    ##    ###      
#     #  ##     ##      ##    ##    ## ##            ##       ##   ##    ##    ##    ##      ###    
#        #      ##      ##    ##    ## ##            ##       ##   ##    ##    ##    ##        ###  
#    /####      ##      /#    ##    ## ###     /     ##       ##   ##    ##    ##    ##   /###  ##  
#   /  #####     ######/ ##   ###   ### ######/      ##       ### / ######     ###   ### / #### /   
#  /    ###       #####   ##   ###   ### #####        ##       ##/   ####       ###   ###   ###/    
#  #                                                                                                
#   ##                                                                                              
# ---------- FUNCTIONS --------------------------------------------------------------------------------------------------------



# monkey patching :D
async def new_global_before_hook(self, ctx):
    print('Command', '"'+ ctx.command.name +'"','invoked by', str(ctx.author.name), '('+ str(ctx.author.id) +')', 'on channel "' + str(ctx.channel.name) + '".' if not ctx.channel == None else 'in private message.')
twitchio.ext.commands.Bot.global_before_hook = new_global_before_hook

# starts the bot when called
async def engage():
    print("Starting...")
    loop = asyncio.get_event_loop()
    loop.create_task(checkChannels())
    # loop.create_task(MAXServer.twitchWS())
    await bot.start()

# called when told to join a new channel, sets up defaults (creates an entry for that channel)
async def configNewChannel(channel):
    pass

async def checkChannels():
    while True:
        try:
            if devFlag:
                await asyncio.sleep(7)
            else:
                await asyncio.sleep(30)
            await bot._ws.wait_until_ready()
            await MAXDiscord.bot.wait_until_ready()

            channelsToCheck = await getChannelsToCheck()
            if not channelsToCheck:
                continue    # restarts the loop from the top (so waits, then checks again)
            try:
                response = await bot.get_streams(channels=channelsToCheck)
            except twitchio.errors.HTTPException as error:
                print('HTTPException getting stream information: ' + str(error))
                continue
            else:
                await notifyChannels(response)
        except Exception as error:
            traceback.print_exc()
            continue

async def getChannelsToCheck():
    channels = []
    entriesToRemove = []
    # find every channel
    for entry in config.all():
        newAnnounceSchedule = copy.copy(entry['announceSchedule'])
        # remove the schedule dates that have passed
        for day in entry['announceSchedule']:
            if (day != 'once') and (day != 'always') and (day not in dayNames) and (dateutil.parser.parse(day).date() < datetime.date.today()):
                try:
                    newAnnounceSchedule.remove(day)
                except ValueError:
                    continue
        if newAnnounceSchedule == [] and entry['announcement'] == 'none':
            # mark for removal
            entriesToRemove.append({'twitchChannel': entry['twitchChannel'].lower(), 'discordGuild': entry['discordGuild']})
            continue
        elif newAnnounceSchedule != entry['announceSchedule']:
            # update schedule
            config.update({'announceSchedule': newAnnounceSchedule}, (query.twitchChannel == entry['twitchChannel']) & (query.discordGuild == entry['discordGuild']))
        if entry['twitchChannel'] in channels:
            continue    # starts loop again with the next iteration, so skips all the date checking since already added
        if entry['announcement'] != 'none':
            channels.append(entry['twitchChannel'])
            continue    # starts loop again with the next iteration, so skips all the date checking since already added
        for date in entry['announceSchedule']:
            if date == 'always' or date == 'once':
                channels.append(entry['twitchChannel'])
                break
            else:
                today = datetime.date.today()
                if date in dayNames and dayNames.index(date) == today.weekday():
                    channels.append(entry['twitchChannel'])
                    break
                if today == dateutil.parser.parse(date).date():
                    channels.append(entry['twitchChannel'])
                    break
    for entry in entriesToRemove:
        config.remove((query.twitchChannel == entry['twitchChannel']) & (query.discordGuild == entry['discordGuild']))
    return channels

async def notifyChannels(response):
    streamNames = []
    streamsToAnnounce = []
    games = []
    users = []
    for stream in response:
        streamNames.append(stream['user_name'].lower())

    for entry in config.all():
        announcement = entry['announcement']
        twitchChannel = entry['twitchChannel'].lower()
        discordGuild = entry['discordGuild']
        if announcement == 'none' and twitchChannel in streamNames:
            # stream has no announcement but is in the list of live streams, so announce
            # get the index of the twitchChannel in the streamNames list and pass the response element (dict) thats at the same position in the response list as the name in streamNames list (cause its made from the response list)
            responseEntry = response[streamNames.index(twitchChannel)]
            games.append(int(responseEntry['game_id']))
            users.append(twitchChannel)
            streamsToAnnounce.append({'discordGuild': discordGuild, 'info': responseEntry})
        elif announcement != 'none' and twitchChannel not in streamNames:
            # stream had an announcement but is not in the list of live streams, so remove its announcement
            if not entry.get('ended'):
                print(twitchChannel + ' went offline...')
            await MAXDiscord.removeAnnouncement(discordGuild, announcement, twitchChannel)
        elif announcement != 'none' and twitchChannel in streamNames and entry.get('ended'):
            # if going live but there's an "ended" entry for the stream (so, its been less than an hour since they went live)
            # delete the "ended" element
            print(response[streamNames.index(twitchChannel)]['user_name'] + ' went live again within grace period.')
            config.update(tinydb.operations.delete('ended'), (query.twitchChannel == twitchChannel) & (query.discordGuild == discordGuild))
    
    # get information about the games that are being played, including game name and game image
    if games:
        games = await bot.get_games(*games)

    # get information about the users being announced, including profile image and the user offline image
    if users:
        response = await bot.get_users(*users)
        for user in response:
            config.update({'profileURL': user.profile_image, 'offlineURL': user.offline_image}, query.twitchChannel == user.login.lower())

    for stream in streamsToAnnounce: 
        game = {'name': 'No Game Selected'}
        for gameResult in games:
            if stream['info']['game_id'] == gameResult['id']:
                game = gameResult
                break
        print(stream['info']['user_name'] + ' is live unannounced...')
        await MAXDiscord.makeAnnouncement(stream['discordGuild'], stream['info'], game)

# join a twitch channel (only going to be called by a discord server owner)
async def join(ctx):
    # configNewChannel(channel)
    # bot.join_channels(channelList)
    pass

# leave a twitch channel (only going to be called by a discord server owner)
async def leave(ctx):
    # configRemoveChannel(channel)
    # bot.part_channels(channelList)
    pass



# ---------- EVENTS -----------------------------------------------------------------------------------------------------------
#       ##### ##                                                      
#    ######  /### /                                                   
#   /#   /  / ###/                                      #             
#  /    /  /   ## ##                                   ##             
#      /  /       ##                                   ##             
#     ## ##        ##    ###      /##  ###  /###     ######## /###    
#     ## ##         ##    ###    / ###  ###/ #### / ######## / #### / 
#     ## ######     ##     ###  /   ###  ##   ###/     ##   ##  ###/  
#     ## #####      ##      ## ##    ### ##    ##      ##  ####       
#     ## ##         ##      ## ########  ##    ##      ##    ###      
#     #  ##         ##      ## #######   ##    ##      ##      ###    
#        /          ##      ## ##        ##    ##      ##        ###  
#    /##/         / ##      /  ####    / ##    ##      ##   /###  ##  
#   /  ##########/   ######/    ######/  ###   ###     ##  / #### /   
#  /     ######       #####      #####    ###   ###     ##    ###/    
#  #                                                                  
#   ##                                                                
# ---------- EVENTS -----------------------------------------------------------------------------------------------------------



@bot.event
async def event_command_error(ctx, error):
    # ignore command not found errors
    if type(error) == twitchio.ext.commands.errors.CommandNotFound:
        return

@bot.event
async def event_ready():
    print(f'Connected as {bot.nick} to "' + '", "'.join(bot.initial_channels) + '"')

#@bot.event
#async def event_webhook(data):
#    print(data)



# ---------- COMMANDS ---------------------------------------------------------------------------------------------------------
#        # ###                                                                       ##             
#      /  /###  /                                                                     ##            
#     /  /  ###/                                                                      ##            
#    /  ##   ##                                                                       ##            
#   /  ###                                                                            ##            
#  ##   ##          /###   ### /### /###   ### /### /###     /###   ###  /###     ### ##    /###    
#  ##   ##         / ###  / ##/ ###/ /##  / ##/ ###/ /##  / / ###  / ###/ #### / ######### / #### / 
#  ##   ##        /   ###/   ##  ###/ ###/   ##  ###/ ###/ /   ###/   ##   ###/ ##   #### ##  ###/  
#  ##   ##       ##    ##    ##   ##   ##    ##   ##   ## ##    ##    ##    ##  ##    ## ####       
#  ##   ##       ##    ##    ##   ##   ##    ##   ##   ## ##    ##    ##    ##  ##    ##   ###      
#   ##  ##       ##    ##    ##   ##   ##    ##   ##   ## ##    ##    ##    ##  ##    ##     ###    
#    ## #      / ##    ##    ##   ##   ##    ##   ##   ## ##    ##    ##    ##  ##    ##       ###  
#     ###     /  ##    ##    ##   ##   ##    ##   ##   ## ##    /#    ##    ##  ##    /#  /###  ##  
#      ######/    ######     ###  ###  ###   ###  ###  ### ####/ ##   ###   ###  ####/   / #### /   
#        ###       ####       ###  ###  ###   ###  ###  ### ###   ##   ###   ###  ###       ###/    
# ---------- COMMANDS ---------------------------------------------------------------------------------------------------------



@bot.command(name='test')
async def test(ctx):
    print('test')
    await ctx.send(f'Hello {ctx.author.name}!')
    print('test2')
    await MAXServer.subscribeTwitchTopic()