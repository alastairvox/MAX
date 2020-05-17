import itertools, sys, traceback, asyncio, copy, datetime, dateutil.parser, pytz, tinydb, tinydb.operations, lxml.etree, inspect
import discord, discord.ext.commands
import MAXShared, MAXTwitch, MAXServer, MAXYoutube, MAXSpotify
from MAXShared import auth, youtubeConfig, discordConfig, generalConfig, twitchConfig, spotifyConfig, query, devFlag, dayNames, fullDayNames, specialRoles

# overloads print for this module so that all prints (hopefully all the sub functions that get called too) are appended with which service the prints came from
print = MAXShared.printName(print, "DISCORD:")



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
config = discordConfig

# get the prefix for commands for each message: no prefix in DM's, ! by default, or the prefix that server has configured
def getGuildPrefix(bot, message):
    if message.guild:
        guildConfig = config.get(query.guildID == message.guild.id)
    else:
        # if there is no guild id then this is a private message, so no prefix
        return ""
    return guildConfig['prefix'] if guildConfig else "!"

# custom HelpCommand that mostly just changes formatting and adds some flavour text
class MAXHelpCommand(discord.ext.commands.DefaultHelpCommand):
    def __init__(self):
        super().__init__()
        self.width = 2000
        self.indent = 4
        self.no_category = "Commands"
        self.paginator = discord.ext.commands.Paginator(prefix='', suffix='', max_size=2000)
    # mostly copied from the original definition v1.3.3 - changed ending note
    def get_ending_note(self):
        command_name = self.invoked_with
        return '*I also giveth users a role when they join a server and announceth Twitch and YouTube streams when they go live."*\n\n' \
                "Type ``{0}{1} command`` for more info on a command. You can also DM commands without a prefix to use them ~privately~.\n" \
                "Mo-mo-more questions? Don't shoot the messenger: ask DrawnActor#0001.".format(self.clean_prefix, command_name)
    # mostly copied from the original definition v1.3.3 - changed to add a | before the short doc in the command list, add command prefix into the command list
    def add_indented_commands(self, commands, *, heading, max_size=None):
        """Indents a list of commands after the specified heading.
        The formatting is added to the :attr:`paginator`.
        The default implementation is the command name indented by
        :attr:`indent` spaces, padded to ``max_size`` followed by
        the command's :attr:`Command.short_doc` and then shortened
        to fit into the :attr:`width`.
        Parameters
        -----------
        commands: Sequence[:class:`Command`]
            A list of commands to indent for output.
        heading: :class:`str`
            The heading to add to the output. This is only added
            if the list of commands is greater than 0.
        max_size: Optional[:class:`int`]
            The max size to use for the gap between indents.
            If unspecified, calls :meth:`get_max_size` on the
            commands parameter.
        """

        if not commands:
            return

        self.paginator.add_line(heading)
        max_size = max_size+len(self.clean_prefix) or self.get_max_size(commands)+len(self.clean_prefix)

        get_width = discord.utils._string_width
        for command in commands:
            name = command.name
            width = max_size - (get_width(name) - len(name))
            entry = '{0}{1:<{width}} {2}'.format(self.indent * ' ', self.clean_prefix + name, '| ' + command.short_doc, width=width)
            self.paginator.add_line(self.shorten_text(entry))
    # mostly copied from the original definition v1.3.3 - changed to make the three back ticks (code block) at start of command list and after command list
    async def send_bot_help(self, mapping):
        ctx = self.context
        bot = ctx.bot

        if bot.description:
            # <description> portion
            self.paginator.add_line(bot.description, empty=False)
        
        no_category = '\u200b{0.no_category}:'.format(self)
        no_category += 'i have to "use" this fucking variable (even though it IS being used) or else i get a warning in my editor and i am neurotic'
        no_category = '\u200b{0.no_category}:'.format(self)
        def get_category(command, *, no_category=no_category):
            cog = command.cog
            return cog.qualified_name + ':' if cog is not None else no_category
        
        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        max_size = self.get_max_size(filtered)
        to_iterate = itertools.groupby(filtered, key=get_category)

        # Now we can add the commands to the page.
        for category, commands in to_iterate:
            commands = sorted(commands, key=lambda c: c.name) if self.sort_commands else list(commands)
            self.add_indented_commands(commands, heading='```'+category, max_size=max_size)

        note = '```' + self.get_ending_note()
        if note:
            self.paginator.add_line(note)

        await self.send_pages()
   # mostly copied from the original definition v1.3.3 - changed to make command signature be surrounded in code block (backticks)
    def add_command_formatting(self, command):
        """A utility function to format the non-indented block of commands and groups.

        Parameters
        ------------
        command: :class:`Command`
            The command to format.
        """

        if command.description:
            self.paginator.add_line(command.description, empty=True)

        signature = self.get_command_signature(command)
        self.paginator.add_line('```'+signature+'```', empty=False)

        if command.help:
            try:
                self.paginator.add_line(command.help, empty=True)
            except RuntimeError:
                for line in command.help.splitlines():
                    self.paginator.add_line(line)
                self.paginator.add_line()

# the help intro text
description = "Ah, 'tis Max Headroom here, and I quote fro-fro-from the bard, Shakespeare, a writer:\n\n" \
            '*"I can performeth thine following commands:*'

bot = discord.ext.commands.Bot(command_prefix=getGuildPrefix, case_insensitive=True, help_command=MAXHelpCommand(), description=description, fetch_offline_members=True)



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



async def currentlyBetweenTimePeriod(timePeriod, timeZone):
    timeZone = pytz.timezone(timeZone)
    timeNow = datetime.datetime.now(timeZone).timetz()

    startTime, endTime = await validateTimePeriod(timePeriod, timeZone)

    return startTime <= timeNow <= endTime

# returns startTime, endTime or raises BadArgument
async def validateTimePeriod(timePeriod, timeZone):
    if type(timeZone) == str:
        timeZone = pytz.timezone(timeZone)

    def timeFail():
        raise discord.ext.commands.BadArgument(message='The time period "``' + '-'.join(timePeriod) + '``" is not a valid time period. Make sure you are entering the time period without spaces, in 24 hour format with a dash separating the two times, and with the start time first and the end time last.')

    # check for valid time
    timePeriod = timePeriod.split('-')

    if not len(timePeriod) == 2:
        timeFail()

    startTime = timePeriod[0].split(':')
    if not len(startTime) == 2:
        timeFail()
    startTime = datetime.time(hour=int(startTime[0]), minute=int(startTime[1]), tzinfo=timeZone)
    
    endTime = timePeriod[1].split(':')
    if not len(endTime) == 2:
        timeFail()
    endTime = datetime.time(hour=int(endTime[0]), minute=int(endTime[1]), tzinfo=timeZone)

    if not startTime < endTime:
        raise discord.ext.commands.BadArgument(message='The time "``' + timePeriod[0] + '``" does not come before the time "``' + timePeriod[1] + '``". Make sure you are entering the time period without spaces, in 24 hour format with a dash separating the two times, and with the start time first and the end time last.')

    # compare to datetime.datetime.now(timeZone).timetz()
    return startTime, endTime

async def announceYoutubeUpload(guildID, xmlBytes):
    tree = lxml.etree.fromstring(xmlBytes)
    if tree.find('entry', tree.nsmap) is None:
        print('Ignoring deleted YouTube video.')
        return
    # store a copy of the youtube video number so i dont re-announce youtube videos if they just get updated, have to parse the xml of the text out for relevant bits
    videoID = tree.find('entry/yt:videoId', tree.nsmap).text
    channelID = tree.find('entry/yt:channelId', tree.nsmap).text
    videoTitle = tree.find('entry/title', tree.nsmap).text
    videoURL = tree.find('entry/link', tree.nsmap).get('href')
    channelName = tree.find('entry/author/name', tree.nsmap).text

    youtubeChannelConfig = youtubeConfig.get((query.discordGuild == guildID) & (query.channelID == channelID))
    if not youtubeChannelConfig:
        print('There is no entry associated with', guildID, 'and', channelID, 'so video', videoURL, 'will be ignored.')
        return
    else:
        announcedVideos = youtubeChannelConfig.get('announcedVideos')
        if announcedVideos and videoID in announcedVideos:
            print('Video', videoURL, 'has already been announced in', guildID, 'so it will be ignored.')
            return
        elif announcedVideos:
            announcedVideos.append(videoID)
        else:
            announcedVideos = [videoID]
        youtubeConfig.update({'announcedVideos': announcedVideos}, (query.discordGuild == guildID) & (query.channelID == channelID))
    
    # get info from config files
    discordGuildConfig = config.get(query.guildID == guildID)
    streamRole = discordGuildConfig['streamRole']
    announceChannel = discordGuildConfig['announceChannel']
    botChannel = discordGuildConfig['botChannel']
    prefix = discordGuildConfig['prefix']
    # youtube config
    overrideChannel = youtubeChannelConfig.get('announceChannel')
    overrideRole = youtubeChannelConfig.get('notifyRole')

    # get objects from discord api
    guild = bot.get_guild(guildID)
    if overrideRole:
        if overrideRole != 'default' and overrideRole != streamRole:
            # use overrideRole instead
            streamRole = overrideRole
    if streamRole not in specialRoles:
        streamRole = guild.get_role(streamRole)
    
    if overrideChannel:
        if overrideChannel != 'default' and overrideChannel != announceChannel:
            # use overrideChannel instead
            announceChannel = overrideChannel
    announceChannel = guild.get_channel(announceChannel)
    botChannel = guild.get_channel(botChannel)

    # pass the text (xml, xml.etree.ElementTree?) and guildID to a discord function that parses out the author name, video title, URL (<link rel="alternate" href="), and the time published and then announces the stream if it finds a matching entry
    print('announcing', guildID, videoURL)
    # text content
    message = "**" + channelName + " posted a video!**\nIf you don't want these notifications, go to " + botChannel.mention + " and type ``" + prefix + "notify``.\n**" + videoTitle + "** - " + videoURL
    await MAXMessageChannel(announceChannel, streamRole, message)


# delete the line with the role from the roleAssignMessage
# clear the old emote's reactions from the message
async def removeSelfAssignRole(roleMessage, role):
    newMessage = ''
    removeReaction = None
    for line in roleMessage.content.splitlines():
        if line != '':
            tmp = line.replace('``', '', 1)
            tmp = tmp.split('``: ')
            if tmp[0] == str(role):
                removeReaction = tmp[1]
                continue
            else:
                newMessage += line
        else:
            newMessage += line
    await roleMessage.edit(content=newMessage)
    await roleMessage.clear_reaction(removeReaction)
    return

async def getSelfAssignRoles(roleMessage):
    existingRoles = {}
    for line in roleMessage.content.splitlines():
        if line != '' and line != '**React to change your roles:**':
            tmp = line.replace('``', '', 1)
            tmp = tmp.split('``: ')
            existingRoles[tmp[0]] = tmp[1]

    return existingRoles

# edit and add the new "role + emoji" and reaction to the message
async def addSelfAssignRole(roleMessage, role, reaction):
    message = roleMessage.content
    message += '\n\n``' + str(role) + '``: ' + str(reaction.emoji)

    await roleMessage.edit(content=message)
    await roleMessage.add_reaction(reaction.emoji)

# send a message to the orignal ctx channel and ask for the reaction
# wait for the reaction for 60s
    # reaction timeout: delete the message
# once a reaction is made by the owner, check if the bot can use that reaction
async def waitForReaction(ctx, role, wipingMessage=False):
    if not wipingMessage:
        monitorMessage = await ctx.send("React to this message with the emoji you want members to use to give themselves the ``" + str(role) + "`` role. This message will be deleted after 1 minute without a reaction.")
    else:
        # post a message asking for the reaction but also informing the user that if they provide a reaction the list of roles will be cleared and the message will be moved to the new channel they provided. if they did not mean to do this, then do not add a reaction to this message
        monitorMessage = await ctx.send("There is already a self-assignable role message for your server. Reacting to this message will delete the old role message and clear the list of self-assignable roles, then make a new one in the channel you provided. If you didn't mean to do this, ignore this message and use the selfroles command again with just the ``role`` you want to add to the list.\n\nReact to this message with the emoji you want members to use to give themselves the ``" + str(role) + "`` role. This message will be deleted after 1 minute without a reaction.")
    
    ownerID = config.get(query.guildID == ctx.guild.id)['owner']
    def check(reaction, user):
        return user.id == ownerID and reaction.message.id == monitorMessage.id
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
    except asyncio.TimeoutError:
        await monitorMessage.delete()
        return None
    else:
        # i dont like warnings about unused varaibles lol
        user=user
        if reaction.custom_emoji:
            if not isinstance(reaction.emoji, discord.PartialEmoji):
                if not reaction.emoji.is_usable():
                    await ctx.send("I cannot use this emoji. You must react with an emoji I can use, such as a unicode emoji, default discord emoji, or a custom emoji from this server.")
                    return await waitForReaction(ctx, role, wipingMessage)
                else:
                    return reaction
            else:
                converter = discord.ext.commands.EmojiConverter()
                try:
                    emoji = await converter.convert(ctx, reaction.emoji)
                except Exception as error:
                    print(error)
                    await ctx.send("I cannot use this emoji. You must react with an emoji I can use, such as a unicode emoji, default discord emoji, or a custom emoji from this server.")
                    return await waitForReaction(ctx, role, wipingMessage)
                else:
                    if emoji.is_usable():
                        return reaction
                    else:
                        await ctx.send("I cannot use this emoji. You must react with an emoji I can use, such as a unicode emoji, default discord emoji, or a custom emoji from this server.")
                        return await waitForReaction(ctx, role, wipingMessage)
        else:
            return reaction

# creates a new self-assign role message and saves it to config, then returns the message object
async def createNewSelfAssignMessage(ctx, roleChannel):
    roleMessage = await roleChannel.send("**React to change your roles:**")
    config.update({'roleAssignMessage': str(roleChannel.id) + '-' + str(roleMessage.id)}, query.guildID == ctx.guild.id)
    return roleMessage

# starts the bot when called
async def engage():
    print("Starting...")
    discordToken = auth.get(query.name == 'discord')['devToken'] if devFlag else auth.get(query.name == 'discord')['token']
    await bot.start(discordToken, reconnect=True)

# creates and returns a fake context for calling commands externally
async def createFakeContext():
    fakeData = {'id': 0, 'attachments': [], 'embeds': [], 'edited_timestamp': None, 'type': None, 'pinned': None, 'mention_everyone': None, 'tts': None, 'content': None}
    fakeMessage = discord.Message(state=None,channel=None,data=fakeData)
    fakeContext = discord.ext.commands.Context(prefix=None, message=fakeMessage, bot=bot, guild=None)
    return fakeContext

# sends a message to a specified channel and notifies the specified role
async def MAXMessageChannel(channel, role, message, embed=None):
    sent = None
    print('Sending message to "' + str(channel.guild) + '" in "' + str(channel) + '" and notifying "' + str(role) + '".')
    # cast to string in case it's a Role object which doesnt have a function for lower, Role object gives its name as a string when cast
    if role == None or str(role).lower() == 'none':
        # since Context is built from a Message, interally ctx.send() effectively uses channel.send() too
        sent = await channel.send(message, embed=embed)
    elif str(role).lower() == 'everyone':
        sent = await channel.send('@everyone ' + message, embed=embed)
    elif str(role).lower() == 'here':
        sent = await channel.send('@here ' + message, embed=embed)
    else:
        if role.mentionable:
            sent = await channel.send(role.mention + ' ' + message, embed=embed)
        else:
            # shouldn't need to do this soon because of changes to mentionable roles permissions, but for now even though its technically changed it isnt for bots
            # https://www.reddit.com/r/discordapp/comments/f62o6f/role_mentions_from_administrators_will_now_ping/fi2hqra/
            await role.edit(mentionable=True, reason="Making mentionable to highlight message.")
            sent = await channel.send(role.mention + ' ' + message, embed=embed)
            await role.edit(mentionable=False, reason="Sent message.")
    return sent

# add internal (boolean), originalCtx (Context), and userName (string)(only if not internal)
# allows me to use converters easily from external commands and private messages
# returns ctx, raises CheckFailure if no associated guild found
async def modifyContext(ctx):
    # if the context being passed in is from a discord event/called from a discord message then its an instance of the Context class from the discord.py API
    internal = type(ctx) == discord.ext.commands.Context
    # creates a shallow copy of the original context in case there are errors later
    originalCtx = copy.copy(ctx)
    if internal:
        # manually change the context's guild to be the guild the user owns so we can just use the converters
        ctx.guild = bot.get_guild(config.get(query.owner == ctx.author.id)['guildID']) if config.get(query.owner == ctx.author.id) else None
        # add our stuff in so we can track if its internal or restore the orginal context for later
        ctx.internal = internal
        ctx.originalCtx = originalCtx
        if ctx.guild == None:
            raise discord.ext.commands.CheckFailure(message="This command can only be used by a discord server owner.")
        return ctx
    else:
        userName = ctx.author.name
        for entry in config:
            for name in entry['ownerNames']:
                if userName.lower() == name.lower():
                    ctx.guild = bot.get_guild(entry['guildID'])
                    break
        ctx.bot = bot
        ctx.internal = internal
        ctx.originalCtx = originalCtx
        ctx.userName = userName
        # if no guild was associated with the external user
        if not ctx.guild:
            await ctx.send("This command can only be used by a discord server owner.")
            raise discord.ext.commands.CheckFailure(message="This command can only be used by a discord server owner.")
        return ctx

def configNewGuilds():
    for guild in bot.guilds:
        if not config.get(query.guildID == guild.id):
            print('Found new guild:', '"' + guild.name + '"', '(' + str(guild.id) + ').', 'Setting defaults...')
            # the @everyone role everyone starts with, so we can find the first channel on the server everyone can send messages in (probably general) - we have to do this because default channels got removed in 2017 and theres no way to know what channel is the "general" channel anymore :/
            defaultRole = guild.default_role
            defaultRolePerms = defaultRole.permissions
            defaultChannel = None
            for channel in guild.text_channels:
                channelRoleOverwrites = channel.overwrites_for(defaultRole)
                # if the role has "send_messages" permission, then we are looking for the first channel that doesn't specifically deny that permission (overwrites.send_messages != False)
                if defaultRolePerms.send_messages == True:
                    if channelRoleOverwrites.send_messages != False:
                        defaultChannel = channel
                        break
                # if the role doesn't have "send_messages" permission, then we are looking for the first channel that specifically allows that permission
                else:
                    if channelRoleOverwrites.send_messages == True:
                        defaultChannel = channel
                        break
            # if we couldn't find a channel everyone can speak in, then fall back to finding the first channel our bot can speak in (should be the very first channel as an admin, not ideal but necessary for a default config)
            if not defaultChannel:
                for channel in guild.text_channels:
                    channelPermissions = channel.permissions_for(bot.user)
                    if channelPermissions.send_messages == True:
                        defaultChannel = channel
                        break
            # if there are no channels we can speak in at all somehow then we just use a dm channel with the guild owner
            if not defaultChannel:
                if guild.owner.dm_channel:
                    defaultChannel = guild.owner.dm_channel
                else:
                    guild.owner.create_dm()
                    defaultChannel = guild.owner.dm_channel
            defaultConfig = {'guildID': guild.id, 'owner': guild.owner.id, 'ownerNames': [], 'botChannel': defaultChannel.id, 'announceChannel': defaultChannel.id, 'streamRole': 'everyone', 'prefix': '!', 'useActivity': False, 'deleteAnnouncements': False, "giveStreamRoleOnJoin": True, 'badInternet': False, 'badInternetTime': 30, 'timeZone': 'US/Central'}
            config.upsert(defaultConfig, query.guildID == guild.id)

async def makeAnnouncement(discordGuild, info, game):
    # get info from config files
    discordGuildConfig = config.get(query.guildID == discordGuild)
    streamRole = discordGuildConfig['streamRole']
    announceChannel = discordGuildConfig['announceChannel']
    botChannel = discordGuildConfig['botChannel']
    timeZone = discordGuildConfig['timeZone']
    prefix = discordGuildConfig['prefix']
    # twitch config
    twitchChannelConfig = twitchConfig.get(query.twitchChannel == info['user_name'].lower())
    profileURL = twitchChannelConfig['profileURL']
    overrideRole = twitchChannelConfig.get('announceRole')

    # get objects from discord api
    guild = bot.get_guild(discordGuild)

    if overrideRole:
        if overrideRole and overrideRole != streamRole:
            # use overrideRole instead
            streamRole = overrideRole
    if streamRole not in specialRoles:
        streamRole = guild.get_role(streamRole)

    announceChannel = guild.get_channel(announceChannel)
    botChannel = guild.get_channel(botChannel)

    # get date/convert date from UTC
    date = dateutil.parser.parse(info['started_at'])
    newTZ = pytz.timezone(timeZone)
    newDate = date.replace(tzinfo=pytz.utc).astimezone(newTZ)
    date = newTZ.normalize(newDate) # .normalize might be unnecessary
    dateString = date.strftime("%#I:%M %p (%Z)")

    # text content
    message = "**" + info['user_name'] + " is live on Twitch!**\nIf you don't want these notifications, go to " + botChannel.mention + " and type ``" + prefix + "notify``."

    # embed content
    embed = discord.Embed()
    embed.title = 'https://twitch.tv/' + info['user_name']
    embed.url = embed.title
    embed.colour = 6570404
    embed.timestamp = date
    embed.set_footer(text='Started')
    embed.set_image(url=info['thumbnail_url'].replace('-{width}x{height}', ''))
    embed.set_author(name=info['title'], url='https://twitch.tv/' + info['user_name'], icon_url=profileURL)
    if game.get('box_art_url'):
        embed.set_thumbnail(url=game['box_art_url'].replace('-{width}x{height}', '').replace('/ttv-boxart/./', '/ttv-boxart/'))
    else:
        embed.set_thumbnail(url='https://static-cdn.jtvnw.net/ttv-static/404_boxart.jpg')
    embed.add_field(name='Started',value=dateString,inline=True)
    embed.add_field(name='Playing',value=game['name'],inline=True)

    sent = await MAXMessageChannel(announceChannel, streamRole, message, embed)

    twitchConfig.update({'announcement' : sent.id}, (query.twitchChannel == info['user_name'].lower()) & (query.discordGuild == discordGuild))


async def removeAnnouncement(discordGuild, announcement, twitchChannel):
    # get info from discord config
    discordGuildConfig = config.get(query.guildID == discordGuild)
    announceChannel = discordGuildConfig['announceChannel']
    timeZone = discordGuildConfig['timeZone']
    deleteAnnouncements = discordGuildConfig['deleteAnnouncements']
    badInternet = discordGuildConfig['badInternet']
    badInternetTime = discordGuildConfig['badInternetTime']
    # twitch config stuff
    twitchChannelConfig = twitchConfig.get((query.twitchChannel == twitchChannel.lower()) & (query.discordGuild == discordGuild))
    offlineURL = twitchChannelConfig['offlineURL']
    announceSchedule = twitchChannelConfig['announceSchedule']
    announceTimes = twitchChannelConfig.get('announceTimes')
    # get discord objects
    guild = bot.get_guild(discordGuild)
    announceChannel = guild.get_channel(announceChannel)

    # get announcement message
    announcement = await announceChannel.fetch_message(announcement)

    if badInternet:
        utcTZ = pytz.timezone('UTC')       
        # if the stream hasn't had its end time stored yet ('ended' key does not exist)
        if not twitchChannelConfig.get('ended'):
            twitchConfig.update({'ended': str(datetime.datetime.now(utcTZ))}, (query.twitchChannel == twitchChannel.lower()) & (query.discordGuild == discordGuild))
            print('Delaying removal due to badInternet flag on "' + guild.name + '".')
            return
        # else if the difference between now and the time the stream actually ended is less than 1 hour
        elif (datetime.datetime.now(utcTZ) - dateutil.parser.parse(twitchChannelConfig.get('ended'))) < datetime.timedelta(minutes=badInternetTime):
            return
        # otherwise, continue and delete/edit the announcement

    if deleteAnnouncements:
        print('Removing announcement for ' + twitchChannel + '.')
        await announcement.delete()
    else:
        announcement.content = announcement.content.replace('is live on Twitch!', 'is no longer live on Twitch.')

        # get date/convert date from UTC
        timeStarted = announcement.embeds[0].timestamp
        newTZ = pytz.timezone(timeZone)
        newTimeStarted = timeStarted.replace(tzinfo=pytz.utc).astimezone(newTZ)
        timeStarted = newTZ.normalize(newTimeStarted) # .normalize might be unnecessary
        if not twitchChannelConfig.get('ended'):
            timeEnded = datetime.datetime.now(newTZ).strftime("%#I:%M %p (%Z)")
            endedFooter = datetime.datetime.now(newTZ).strftime("%b %#d at %#I:%M %p (%Z)")
            duration = datetime.datetime.now(newTZ) - timeStarted
        else:
            timeEnded = dateutil.parser.parse(twitchChannelConfig.get('ended'))
            newTimeEnded = timeEnded.replace(tzinfo=pytz.utc).astimezone(newTZ)
            timeEnded = newTZ.normalize(newTimeEnded).strftime("%#I:%M %p (%Z)") # .normalize might be unnecessary
            endedFooter = newTZ.normalize(newTimeEnded).strftime("%b %#d at %#I:%M %p (%Z)")
            duration = dateutil.parser.parse(twitchChannelConfig.get('ended')) - timeStarted

        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration = '{:2}h {:2}m {:2}s'.format(int(hours), int(minutes), int(seconds))
        announcement.embeds[0].insert_field_at(index=1,name='Ended',value=timeEnded,inline=True)
        announcement.embeds[0].insert_field_at(index=2,name='Duration',value=duration,inline=True)
        announcement.embeds[0].set_field_at(index=3,name='Played',value=announcement.embeds[0].fields[3].value)
        announcement.embeds[0].set_footer(text='Ended    •  ' + endedFooter + '\nStarted')
        announcement.embeds[0].set_image(url=offlineURL.replace('-1920x1080', ''))

        print('Editing announcement for ' + twitchChannel + ' to reflect offline state.')
        await announcement.edit(content=announcement.content,embed=announcement.embeds[0])
    
    # update schedule
    if announceSchedule[0] == 'always':
        pass
    else:
        if announceSchedule[0] == 'once':
            announceSchedule.pop(0)
            # removes the defined schedule times for 'once' if any exist
            if announceTimes: announceTimes.pop('once', None)
        # remove the schedule dates that have passed
        newAnnounceSchedule = []
        for entry in announceSchedule:
            # if the day is still to come (i think dateutil parser always defaults to parsing a day name as the next future time that day occurs, or today)
            if dateutil.parser.parse(entry).date() >= datetime.date.today():
                newAnnounceSchedule.append(entry)
            else:
                # removes the defined schedule times for the schedule option if any exist since the day has passed
                if announceTimes: announceTimes.pop(entry, None)
        announceSchedule = newAnnounceSchedule
        if announceSchedule == []:
            twitchConfig.remove((query.twitchChannel == twitchChannel.lower()) & (query.discordGuild == discordGuild))
            return

    # reset the announcement holder
    twitchConfig.update({'announcement' : "none", 'announceSchedule': announceSchedule, 'announceTimes': announceTimes}, (query.twitchChannel == twitchChannel.lower()) & (query.discordGuild == discordGuild))
    if twitchChannelConfig.get('ended'):
        twitchConfig.update(tinydb.operations.delete('ended'), (query.twitchChannel == twitchChannel.lower()) & (query.discordGuild == discordGuild))

async def sendAllConfig(ctx, mode):
    message = ''
    if mode == 'all' or mode == 'discord':
        message += "**Server Configuration**\n"
        for entry in config.all():
            # ctx has already been modified to have ctx.guild replaced with the guild of the owner
            if entry['guildID'] == ctx.guild.id:
                for key in entry:
                    if key != 'botChannel' and key != 'announceChannel':
                        message += key + ': ``'
                    
                    if key == 'guildID':
                        message += ctx.guild.name
                    elif key == 'owner':
                        converter = discord.ext.commands.UserConverter()
                        message += str(await converter.convert(ctx, str(entry[key])))
                    elif key == 'botChannel' or key == 'announceChannel':
                        converter = discord.ext.commands.TextChannelConverter()
                        value = await converter.convert(ctx, str(entry[key]))
                        message += key + ': ' + value.mention + '\n'
                    elif key == 'streamRole' and entry[key] not in specialRoles:
                        converter = discord.ext.commands.RoleConverter()
                        message += str(await converter.convert(ctx, str(entry[key])))
                    else:
                        if type(entry[key]) == bool:
                            message += 'Yes' if entry[key] else 'No'
                        else:
                            message += str(entry[key])
                    
                    if key != 'botChannel' and key != 'announceChannel':
                        message += '``\n'
                break
    
    if mode == 'all' or mode == 'twitch':
        message += "\n**Twitch Configuration**"
        for entry in twitchConfig.all():
            if entry['discordGuild'] == ctx.guild.id:
                message += '\n'
                for key in entry:
                    if key != "profileURL" and key != "offlineURL" and key != "discordGuild":
                        if key == 'announcement' and entry[key] != 'none':
                            converter = discord.ext.commands.MessageConverter()
                            value = str(config.get(query.guildID == ctx.guild.id)['announceChannel']) + '-' + str(entry[key])
                            value = await converter.convert(ctx, value)
                            message += key + ': ' + value.jump_url + '\n'
                        elif key == 'announceRole' and entry[key] not in specialRoles:
                            converter = discord.ext.commands.RoleConverter()
                            value = str(await converter.convert(ctx, str(entry[key])))
                            message += key + ': ``' + value + '``\n'
                        else:
                            message += key + ': ``' + str(entry[key]) + '``\n'
    
    if mode == 'all' or mode == 'youtube':
        message += "\n**YouTube Configuration**"
        for entry in youtubeConfig.all():
            if entry['discordGuild'] == ctx.guild.id:
                message += '\n'
                for key in entry:
                    if key != 'announcedVideos' and key != 'discordGuild' and key != 'leaseSeconds' and key != 'time' and entry[key] != 'default':
                        message += key + ': ``' + str(entry[key]) + '``\n'

    await ctx.send(message)



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



# on_raw_reaction_add(payload)
@bot.event
async def on_raw_reaction_add(payload):
    roleGuild = bot.get_guild(payload.guild_id)
    roleMember = roleGuild.get_member(payload.user_id)
    if roleMember.id != bot.user.id:
        roleMessage = config.get(query.roleAssignMessage == str(payload.channel_id) + '-' + str(payload.message_id))
        if roleMessage:
            roleChannel = roleGuild.get_channel(payload.channel_id)
            roleMessage = await roleChannel.fetch_message(payload.message_id)
            existingRoles = await getSelfAssignRoles(roleMessage)
            for role, emoji in existingRoles.items():
                if str(payload.emoji) == emoji:
                    ctx = await createFakeContext()
                    ctx.guild = roleGuild
                    converter = discord.ext.commands.RoleConverter()
                    role = await converter.convert(ctx, role)
                    print('Giving self-assign role "' + str(role) + '" to user ' + str(roleMember) + ' (' + str(roleMember.id) + ') on server "' + str(roleGuild) + '".')
                    await roleMember.add_roles(role)
                    break
    return

@bot.event
async def on_raw_reaction_remove(payload):
    roleGuild = bot.get_guild(payload.guild_id)
    roleMember = roleGuild.get_member(payload.user_id)
    if roleMember.id != bot.user.id:
        roleMessage = config.get(query.roleAssignMessage == str(payload.channel_id) + '-' + str(payload.message_id))
        if roleMessage:
            roleChannel = roleGuild.get_channel(payload.channel_id)
            roleMessage = await roleChannel.fetch_message(payload.message_id)
            existingRoles = await getSelfAssignRoles(roleMessage)
            for role, emoji in existingRoles.items():
                if str(payload.emoji) == emoji:
                    ctx = await createFakeContext()
                    ctx.guild = roleGuild
                    converter = discord.ext.commands.RoleConverter()
                    role = await converter.convert(ctx, role)
                    print('Removing self-assign role "' + str(role) + '" from user ' + str(roleMember) + ' (' + str(roleMember.id) + ') on server "' + str(roleGuild) + '".')
                    await roleMember.remove_roles(role)
                    break
    return

@bot.event
async def on_ready():
    print(f'Connected as {bot.user} to "' + '", "'.join(map(str, bot.guilds)) + '"')
    # get all the guilds MAX is connected to and check if they all have entries in the config file, if not then create a default one
    configNewGuilds()

@bot.event
async def on_guild_join(guild):
    configNewGuilds()

@bot.event
async def on_command(ctx):
    if hasattr(ctx, 'originalCtx'):
        print('Command', '"'+ ctx.originalCtx.invoked_with +'"','invoked by', str(ctx.originalCtx.author), '('+ str(ctx.originalCtx.author.id) +')', 'on server "' + str(ctx.originalCtx.guild) + '".' if not ctx.originalCtx.guild == None else 'in private message.')
    else:
        print('Command', '"'+ ctx.invoked_with +'"','invoked by', str(ctx.author), '('+ str(ctx.author.id) +')', 'on server "' + str(ctx.guild) + '".' if not ctx.guild == None else 'in private message.')

@bot.event
async def on_command_error(ctx, error):
    """The event triggered when an error is raised while invoking a command.
    ctx   : Context
    error : Exception"""

    if hasattr(ctx, 'internal'):
        if not ctx.internal:
            print("Error in external (twitch) command through discord: " + type(error).__name__ + ' Error: ' + str(error))
            errorResponse = '**' + type(error).__name__ + ' Error:** *' + str(error) + '*\nSome arguments are case-sensitive. Use ``' + ctx.prefix + 'help ' + ctx.command.name + '`` for more information on this command.```' + ctx.prefix + ctx.command.name + ' ' + ctx.command.signature + '```'
            return await ctx.send(errorResponse)
    if hasattr(ctx, 'originalCtx'):
        ctx = ctx.originalCtx

    # This prevents any commands with local handlers being handled here in on_command_error.
    if hasattr(ctx.command, 'on_error'):
        return
    
    ignored = (discord.ext.commands.CommandNotFound)
    
    # Allows us to check for original exceptions raised and sent to CommandInvokeError.
    # If nothing is found. We keep the exception passed to on_command_error.
    error = getattr(error, 'original', error)
    
    # Anything in ignored will return and prevent anything happening.
    if isinstance(error, ignored):
        if isinstance(error, discord.ext.commands.CommandNotFound) and ctx.guild == None:
            # because we want command not found errors to be sent in PM
            await ctx.send('**' + type(error).__name__ + ' Error:** *' + str(error) + '*\nCommands in private messages do not use a prefix. Use ``help`` for more information on available commands.')
            return
        else:
            return

    elif isinstance(error, discord.ext.commands.DisabledCommand):
        return await ctx.send(f'{ctx.command} has been disabled.')

    elif isinstance(error, discord.ext.commands.NoPrivateMessage):
        try:
            return await ctx.author.send(f'{ctx.command} can not be used in private messages.')
        except:
            pass
    elif isinstance(error, discord.ext.commands.UserInputError) or isinstance(error, discord.ext.commands.CheckFailure):
        print(type(error).__name__ + ' Error: ' + str(error))
        errorResponse = '**' + type(error).__name__ + ' Error:** *' + str(error) + '*\nSome arguments are case-sensitive. Use ``' + ctx.prefix + 'help ' + ctx.command.name + '`` for more information on this command.```' + ctx.prefix + ctx.command.name + ' ' + ctx.command.signature + '```'
        return await ctx.send(errorResponse)

    # # For this error example we check to see where it came from...
    # elif isinstance(error, discord.ext.commands.BadArgument):
    #     if ctx.command.qualified_name == 'tag list':  # Check if the command being invoked is 'tag list'
    #         return await ctx.send('I could not find that member. Please try again.')

    # All other Errors not returned come here... And we can just print the default TraceBack.
    print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)

@bot.event
async def on_member_join(member):
    guildConfig = config.get(query.guildID == member.guild.id)
    enabled = guildConfig['giveStreamRoleOnJoin']
    streamRole = guildConfig['streamRole']
    if enabled and streamRole not in specialRoles:
        streamRole = member.guild.get_role(streamRole)
        print('New member', str(member), '('+ str(member.id) +')', 'joined server "' + str(member.guild) + '", giving them role', str(streamRole), '(' + str(streamRole.id) + ').')
        await member.add_roles(streamRole)



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


@bot.command(name='song', help="""Tells you the song the streamer is currently listening to if they have authorized Spotify through the ``spotify`` command.""")
async def song(ctx):
    guildID = None
    if type(ctx) == discord.ext.commands.Context:
        if not ctx.guild:
            await ctx.send("Sorry, you can't use this command in private messages. Try it on a Discord server or a Twitch channel that I'm in.")
            return
        
        guildID = ctx.guild.id
    else:
        for entry in config.all():
            if entry.get('ownerNames') and entry['ownerNames'][0].lower() == ctx.channel.name.lower():
                guildID = entry['guildID']
                break

    if not MAXSpotify.credentials.get(str(guildID)):
        # message the channel aboud da eror
        error = "Error: strimmer hasn't authorized MAX to control Spotify yet. This must be done through the 'spotify' command in discord."
        print(error)
        await ctx.send(error)
        return

    spotify = MAXSpotify.spotipy.Spotify(auth_manager=MAXSpotify.credentials[str(guildID)])
    try:
        songInfo = spotify.current_user_playing_track()
    except Exception as error:
        err = 'Error: There was an error while getting song info: ' + repr(error)
        print(err)
        await ctx.send(err)
        return
    
    if songInfo:
        trackName = ""
        artistName = ""
        albumName = ""

        if songInfo.get('item'):
            if songInfo['item'].get('name'):
                trackName = '"' + str(songInfo['item']['name']) + '"'
            if songInfo['item'].get('artists') and songInfo['item']['artists'][0].get('name'):
                artistName = ' by ' + str(songInfo['item']['artists'][0]['name'])
            if songInfo['item'].get('album') and songInfo['item']['album'].get('name'):
                albumName = ' on "' + str(songInfo['item']['album']['name']) + '"'

        return await ctx.send("Listening to " + trackName + artistName + albumName)
    else:
        return await ctx.send("The streamer is not listening to anything on Spotify.")


@bot.command(name='twitchtimes', rest_is_raw=True, help ="""Restrict a configured twitch stream announcement schedule to a specific time in your server's timezone.

    This command will let you set a specific announce time period (relative to the timezone you set for your server using the ``configure timezone`` command, default is ``US/Central``) during the day of a scheduled twitch stream. For example, if you have defined a twitch stream using the following command ``twitch twitchChannel streamRole Sun`` then MAX will normally announce that stream any time it goes live on Sunday. However, if you use this command as follows ``twitchtimes twitchChannel 21:00-23:00 Sun`` the stream will only be announced if it starts between 9pm and 11pm on Sundays. You can define multiple time periods for each schedule option (e.g. using both ``twitchtimes twitchChannel 10:29-12:46 Sun`` and ``twitchtimes twitchChannel 21:00-23:00 Sun`` will cause the stream to be announced if it goes live on Sundays between the periods of 10:29am-12:46pm and 9pm-11pm).

    **channelName:**
        The name of the twitch channel you configured a schedule for and want to restrict the announcement time of. You can only use a twitch channel that you have already configured with the ``twitch`` command.

    **timePeriod:**
        The time period to restrict the given schedule option to. This uses the timezone you configured for your server using the ``configure timezone`` command, default is ``US/Central``. This command must be entered WITHOUT SPACES, in 24 hour format with a dash separating the two times, and with the start time first and the end time last. Entering a time that you have already configured will instead remove the time period from the list. A properly formatted time period looks like: 
        ``21:30-23:30``

    **scheduleOption:**
        The schedule option you want to restrict the time period of. You can only specify schedule options that have already been configured for the specified channel via the ``twitch`` command. You can only change a single schedule option at a time. Valid options are:
        ``always``
        ``once``
        ``Mon``, ``Tue``, ``Wed``, ``Thu``, ``Fri``, ``Sat``, or ``Sun``
        ``an un-ambiguous date`` - like ``January 1 2021``""")
async def twitchtimes(ctx, channelName, timePeriod, *, scheduleOption):
    ctx = await modifyContext(ctx)

    userConfigEntry = config.get(query.guildID == ctx.guild.id)
    userTimeZone = userConfigEntry['timeZone']
    
    twitchEntry = twitchConfig.get((query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
    if not twitchEntry:
        raise discord.ext.commands.BadArgument(message='There is no configured twitch channel for your server with the name "``'+ str(channelName) +'``". Make sure you have added it using the ``twitch`` command and have spelled it correctly.')

    announceSchedule = twitchEntry['announceSchedule']
    
    # check for valid schedule option
    scheduleOption = scheduleOption.strip().lower()

    if scheduleOption == 'always' or scheduleOption == 'once' or scheduleOption in dayNames:
        pass
    elif scheduleOption in fullDayNames:
        scheduleOption = dayNames[fullDayNames.index(scheduleOption)]
    else:
        try:
            scheduleOption = dateutil.parser.parse(scheduleOption).date().strftime("%B %#d %Y")
        except:
            raise discord.ext.commands.BadArgument(message='The twitch channel specified does not have "``'+ str(scheduleOption) +'``" in its schedule for your server. Make sure you have added it using the ``twitch`` command and have spelled the schedule option correctly.')
    
    if not scheduleOption in announceSchedule:
        raise discord.ext.commands.BadArgument(message='The twitch channel specified does not have "``'+ str(scheduleOption) +'``" in its schedule for your server. Make sure you have added it using the ``twitch`` command and have spelled the schedule option correctly.')

    # check for valid time
    await validateTimePeriod(timePeriod, userTimeZone)

    # check if the time period has already been entered
    announceTimes = twitchEntry.get('announceTimes')
    if announceTimes:
        oldTimePeriods = announceTimes.get(scheduleOption)
        if oldTimePeriods and timePeriod in oldTimePeriods:
            announceTimes[scheduleOption].remove(timePeriod)
            twitchConfig.update({'announceTimes': announceTimes}, (query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
            await ctx.send('The time period "``'+ timePeriod +'``" for the schedule option "``'+ scheduleOption +'``" has been removed from the channel "``'+ channelName +'``".')
            await sendAllConfig(ctx, 'twitch')
            return
        elif oldTimePeriods:
            announceTimes[scheduleOption].append(timePeriod)
        else:
            announceTimes[scheduleOption] = [timePeriod]
    else:
        announceTimes = {scheduleOption: [timePeriod]}

    twitchConfig.update({'announceTimes': announceTimes}, (query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
    await ctx.send('The time period "``'+ timePeriod +'``" for the schedule option "``'+ scheduleOption +'``" has been applied to the channel "``'+ channelName +'``".')
    await sendAllConfig(ctx, 'twitch')
    return


@bot.command(name='deleteoffline', help="""Toggle wether announcements are deleted once a stream goes offline or remain but get edited to state the stream is offline and include the duration of the stream.""")
async def deleteoffline(ctx):
    ctx = await modifyContext(ctx)

    if config.get(query.guildID == ctx.guild.id)['deleteAnnouncements']:
        config.update({'deleteAnnouncements': False}, query.guildID == ctx.guild.id)
        await ctx.send('Announcements will now be removed when your stream goes offline.')
    else:
        config.update({'deleteAnnouncements': True}, query.guildID == ctx.guild.id)
        await ctx.send("Announcements will now be edited to say the stream is offline and include the stream's duration when your stream goes offline.")

# @bot.command(name='test', rest_is_raw=True)
# async def test(ctx, *, song):
#     ctx = await modifyContext(ctx)
#     loop = asyncio.get_event_loop()
#     loop.create_task(MAXServer.twitchWS())
#     # loop.create_task(MAXSpotify.songRequest(ctx.guild.id, song.strip()))
#     await ctx.send('twitch requested.')


@bot.command(name='spotify', rest_is_raw=True, help="""Authorize spotify account, authorize twitch account, and set the name of the channel points reward to use for song requests.

    Setting up Spotify song requests is a bit of an involved process. You need to first tell MAX the name of the channel points reward you want users to redeem to request Spotify songs, then authorize MAX to control your Spotify account, and finally authorize MAX to view your Twitch channel point rewards. After using this command, MAX will send you two links to click that will let you authorize Spotify and Twitch through your browser. NOTE: Unless you use the ``configure ownerTwitchName`` command with the name of the channel you authorized, MAX won't message your Twitch channel about song requests and request errors (requests will still work, viewers will just not be informed about requests that failed to play or how many songs are left in the request queue when they make a request).
    
    **rewardName:**
        The exact, case-sensitive name of the reward you want viewers to redeem to request a song (as you have entered it on Twitch in your custom reward). The reward needs to have the "Require Viewer to Enter Text" option enabled for the redeemer to be able to enter a song name or a spotify song link/URI. You may also want to enable "Skip Reward Requests Queue" to avoid having to manually review the redemption. Note that if you change the name of this reward you will have to update it with MAX by using this command again with the new name.""")
async def spotify(ctx, *, rewardName):
    ctx = await modifyContext(ctx)

    rewardName = rewardName.strip() if rewardName else None

    if not rewardName or rewardName == "":
        # this is all to just trick the error handler into thinking im passing an inspect.Parameter class because all it uses is the "name" parameter when you raise a "MissingRequiredArgument", so that i dont have to do custom error handling for this. i need to do this because "rest is raw" means rewardName will always start with at least '' as its value which is technically a value
        class Tmp: pass
        tmp = Tmp
        tmp.name = "rewardName"
        raise discord.ext.commands.MissingRequiredArgument(param=tmp)

    spotifyConfig.upsert({'discordGuild': ctx.guild.id, "rewardName": rewardName}, query.discordGuild == ctx.guild.id)

    await ctx.author.send("Follow the prompts at the following link to authorize MAX to control Spotify:\n<"+ generalConfig.get(query.name == 'callback')['value'] + "spotify/auth/" + str(ctx.guild.id) + ">\n\nOnce you have done that, the next link will authorize MAX to see your Twitch channel points redemptions:\n<"+ generalConfig.get(query.name == 'callback')['value'] + "twitch/auth/" + str(ctx.guild.id)+">")
    await ctx.send("I've sent you two links in private messages, open them in your browser and follow the login prompts to authorize Spotify control and let MAX see Twitch channel points redemptions.")

@bot.command(name='youtube', help="""Add or remove YouTube channels for new uploads/stream notifications, specify per-channel notification roles and announcement channels.

    **youtubeChannel:**
        The channel ID you want to add notifications for. Cannot be a name (like ``DrawnActor``), must be a channel ID (like ``UC_0hyh6_G3Ct1k1EiqaorqQ``). You can get a channel ID by going to a video and clicking the profile name in the description to go back to the channel, then looking for the ID at the end of the channel URL.
    
    **announceChannel:**
        The channel MAX will make an announcement in when a video is uploaded to this channel. This will override whatever the server's announceChannel is when announcing a video. Don't specify this option to use the default, which is the server's announceChannel. Don't specify a ``notifyRole`` when using this option with a channel that has been added previously to only update the ``announceChannel`` for that channel. Valid options are:
            ``default`` - this will use the server's announceChannel.
            ``a channel name or ID`` - this will use the specified channel whenever a video is uploaded.
        
    **notifyRole:**
        The role you want to notify when a video is uploaded to this channel. This will override whatever the server's streamRole is when announcing a video. Don't specify this option to use the default, which is the server's streamRole, or whatever you previously specified if you have added the channel before. Valid options are:
            ``default`` - this will use the server's streamRole.
            ``none`` - this will not notify anyone.
            ``everyone`` or ``here`` - will notify users the same as @ mentioning their respective option.
            ``a role name or ID`` - this will notify the specified role whenever a video is uploaded.""")
async def youtube(ctx, youtubeChannel, announceChannel=None, notifyRole=None):
    ctx = await modifyContext(ctx)

    # youtubeChannel = 'UCGPBgBHGdmr1VSaK_3Oitqw' # various artists - topic
    # youtubeChannel = 'UC-lHJZR3Gqxm24_Vd_AJ5Yw' # pewdiepie
    oldEntry = youtubeConfig.get((query.discordGuild == ctx.guild.id) & (query.channelID == youtubeChannel))

    if oldEntry and not announceChannel and not notifyRole:
        print('Removing channel', youtubeChannel, 'from config for', ctx.guild.id)
        youtubeConfig.remove((query.discordGuild == ctx.guild.id) & (query.channelID == youtubeChannel))
        await ctx.send('Channel ``' + youtubeChannel + '`` removed from announcements.')
        await sendAllConfig(ctx, 'youtube')
        return

    if not announceChannel:
        if not oldEntry:
            announceChannel = 'default'
        else:
            oldChannel = oldEntry.get('announceChannel')
            if oldChannel:
                announceChannel = oldChannel
            else:
                announceChannel = 'default'
    if not notifyRole:
        if not oldEntry:
            notifyRole = 'default'
        else:
            oldRole = oldEntry.get('notifyRole')
            if oldRole:
                notifyRole = oldRole
            else:
                notifyRole = 'default'

    if announceChannel != 'default':
        converter = discord.ext.commands.TextChannelConverter()
        announceChannel = await converter.convert(ctx, announceChannel)
        announceChannel = announceChannel.id
    if notifyRole not in specialRoles:
        converter = discord.ext.commands.RoleConverter()
        notifyRole = await converter.convert(ctx, notifyRole)
        notifyRole = notifyRole.id

    youtubeConfig.upsert({'discordGuild': ctx.guild.id, 'channelID': youtubeChannel, 'announceChannel': announceChannel, 'notifyRole': notifyRole}, (query.discordGuild == ctx.guild.id) & (query.channelID == youtubeChannel))

    if oldEntry:
        videosCollected = oldEntry.get('announcedVideos')
    else:
        videosCollected = None
    if not videosCollected:
        await ctx.send('Collecting videos from channel. This may take a long time depending on how many videos the channel has.')
        responseStatus = await MAXYoutube.getAllYoutubeUploads(youtubeChannel)
        if responseStatus != 200:
            await ctx.send('Error "' + str(responseStatus) + '" when attempting to get ``' + youtubeChannel + '`` from YouTube. Make sure you have provided a valid YouTube channel ID (like ``UC_0hyh6_G3Ct1k1EiqaorqQ``).')
            youtubeConfig.remove((query.discordGuild == ctx.guild.id) & (query.channelID == youtubeChannel))
            await sendAllConfig(ctx, 'youtube')
            return

    responseStatus = await MAXYoutube.subscribeYoutubeUploads(ctx.guild.id, youtubeChannel)
    if responseStatus == 202:
        channelText = ctx.guild.get_channel(announceChannel).mention if announceChannel != 'default' else 'the default announcement channel'
        announceText = ctx.guild.get_role(notifyRole).name if notifyRole not in specialRoles else notifyRole
        await ctx.send('Successfully registered ``' + youtubeChannel + '`` for announcements in ' + channelText + ' and notifying the ``' + announceText + '`` role.')
        await sendAllConfig(ctx, 'youtube')
    else:
        await ctx.send('Error ' + responseStatus + ' when attempting to get ``' + youtubeChannel + '`` from YouTube. Make sure you have provided a valid YouTube channel ID (like ``UC_0hyh6_G3Ct1k1EiqaorqQ``).')
        youtubeConfig.remove((query.discordGuild == ctx.guild.id) & (query.channelID == youtubeChannel))
        await sendAllConfig(ctx, 'youtube')
    


@bot.command(name='selfroles', help="""Toggles user self-assignable roles, add roles and their reaction emojis, and change the role channel.

    Don't provide a ``role`` or ``roleChannel`` to disable self-assignable roles and clear the list of roles.

    **role:**
        The role name or ID to add. If you have added the specified role previously, then it will be removed from the list instead. After you add a role, react to the follow-up message with the reaction you want members to use to be granted the role.
    
    **roleChannel:**
        The channel to put the self-assignable role message in. Do not provide this option unless you want to change what channel the self assignable role message is in and reset the list to include only the role/reaction you provided.""")
async def selfroles(ctx, role=None, roleChannel=None):
    ctx = await modifyContext(ctx)

    #if no options specified
    if not role and not roleChannel:
        # if the post has been made already, delete it
        roleMessage = config.get(query.guildID == ctx.guild.id)
        roleMessage = roleMessage.get('roleAssignMessage')
        if roleMessage:
            config.update(tinydb.operations.delete('roleAssignMessage'), query.guildID == ctx.guild.id)
            converter = discord.ext.commands.MessageConverter()
            roleMessage = await converter.convert(ctx, roleMessage)
            await roleMessage.delete()
            await ctx.send('The self-assignable role message has been deleted and the list of self-assignable roles has been cleared.')
            return
        # if the post hasnt been made, do nothing - say that theres no post yet
        else:
            await ctx.send('No message has been created yet. Please specify both a ``role`` and ``channel`` to create the self-assignable role message.')
            return
    elif role and not roleChannel:
        # check/get valid role object
        converter = discord.ext.commands.RoleConverter()
        role = await converter.convert(ctx, role)

        roleMessage = config.get(query.guildID == ctx.guild.id)
        roleMessage = roleMessage.get('roleAssignMessage')
        if not roleMessage:
            raise discord.ext.commands.BadArgument(message="You must specify a ``channel`` for the first role you add in order to create the self-assignable role message. No message has been created to add a role to yet.")
        else:
            converter = discord.ext.commands.MessageConverter()
            roleMessage = await converter.convert(ctx, roleMessage)
            existingRoles = await getSelfAssignRoles(roleMessage)
            if str(role) in existingRoles:
                # delete the line with the role from the roleAssignMessage
                # clear the old emote's reactions from the message
                await removeSelfAssignRole(roleMessage, role)
                # let them know its been removed
                await ctx.send('The role ``' + str(role) + '`` has been removed from the list of self-assignable roles.')
                return
            else:
                # send a message to the orignal ctx channel and ask for the reaction
                # wait for the reaction for 60s
                    # reaction timeout: delete the message
                # once a reaction is made by the owner, check if the bot can use that reaction
                reaction = await waitForReaction(ctx, role)
                # edit the roleAssignMessage to add the "role + emoji" to the channel
                # react to the message with the same reaction
                await addSelfAssignRole(roleMessage, role, reaction)
                # let them know you are done
                await ctx.send('The role ``' + str(role) + '`` has been successfully added to the list of self-assignable roles.')
                return
    else:
        roleMessage = config.get(query.guildID == ctx.guild.id)
        roleMessage = roleMessage.get('roleAssignMessage')

        converter = discord.ext.commands.RoleConverter()
        role = await converter.convert(ctx, role)

        converter = discord.ext.commands.TextChannelConverter()
        roleChannel = await converter.convert(ctx, roleChannel)

        if roleMessage:
        # if role message already exists
            # post a message asking for the reaction but also informing the user that if they provide a reaction the list of roles will be cleared and the message will be moved to the new channel they provided. if they did not mean to do this, then do not add a reaction to this message
            # wait for and validate usable reaction
            reaction = await waitForReaction(ctx, role, True)
            if not reaction:
                return
            # delete old message
            converter = discord.ext.commands.MessageConverter()
            roleMessage = await converter.convert(ctx, roleMessage)
            await roleMessage.delete()
            # post new message + put message id into config
            roleMessage = await createNewSelfAssignMessage(ctx, roleChannel)
            # edit and add the new "role + emoji" and reaction to the new message
            await addSelfAssignRole(roleMessage, role, reaction)
            # inform user that old message cleared, new message created in channel, role added
            await ctx.send('The old self-assignable role message has been deleted and the list of self-assignable roles has been cleared. The new self-assignable role message has been created in '+ roleChannel.mention +' and the role ``' + str(role) + '`` has been successfully added to the list.')
            return
        else:
        # if role message doesn't exist 
            # post message asking for reaction
            # wait for and validate usable reaction
            reaction = await waitForReaction(ctx, role)
            if not reaction:
                return
            # post new message + put message id into config
            roleMessage = await createNewSelfAssignMessage(ctx, roleChannel)
            # edit and add the new "role + emoji" and reaction to the new message
            await addSelfAssignRole(roleMessage, role, reaction)
            # inform user message created and role added
            await ctx.send('The self-assignable role message has been created in '+ roleChannel.mention +' and the role ``' + str(role) + '`` has been successfully added to the list.')
            return

@bot.command(name='configure', help="""Check or change MAX options like announcement channel, command prefix, stream role, etc.

    **option:**
        The option you want to check or change (not case-sensitive):
            ``all`` - all current server settings, including the state of all toggleable settings, and any twitch streams with their announce schedules.
            ``prefix`` - the prefix (``!``, ``.``, ``-``, etc) that you want MAX to use for commands on your server.
            ``owner`` - the user (name or ID) that you want to be allowed to configure MAX or access sensitive commands.
            ``ownerTwitchName`` - the Twitch channel (name) for MAX to join as a chat bot (as MAX_BDT) so that you can use these commands and other twitch-specific commands from your Twitch chat. MAX will also message this channel about Spotify song requests and request errors if you have set that up (using the ``spotify`` command).
            ``botChannel`` - the channel (name or ID) you want MAX to tell people to use commands in (when making announcements, etc).
            ``announceChannel`` - the channel (name or ID) you want MAX to make announcements in.
            ``streamRole`` - the role (name or ID) that you want MAX to @ mention for announcements and give to users when they join the server (can also be ``everyone``, ``here``, or ``none``). Since MAX keeps roles internally by ID, you don't have to use this if you have only changed the name of your previous stream role: just when you want to change it to a different role object that already exists.
            ``timeZone`` - the time zone you want MAX to use on announcements (defaults to US/Central). Must be from the following list: <https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568>
    
    **value:**
        The new value for the specified option (case-sensitive). Don't include this in your command if you just want to check what it's currently set to.""")
async def configure(ctx, option, value=None):
    ctx = await modifyContext(ctx)

    option = option.lower()
    if option == 'all':
        # print all settings
        await sendAllConfig(ctx, 'all')
        return
    elif option == 'prefix':
        converter = None
    elif option == 'timezone':
        option = 'timeZone'
        converter = None
    elif option == 'ownertwitchname':
        option = 'ownerNames'
        converter = None
    elif option == 'owner':
        converter = discord.ext.commands.UserConverter()
    elif option == 'botchannel':
        option = 'botChannel'
        converter = discord.ext.commands.TextChannelConverter()
    elif option == 'announcechannel':
        option = 'announceChannel'
        converter = discord.ext.commands.TextChannelConverter()
    elif option == 'streamrole':
        option = 'streamRole'
        converter = discord.ext.commands.RoleConverter()
    else:
        raise discord.ext.commands.BadArgument(message="An invalid option was provided.")
    
    if value == None:
        value = str(config.get(query.guildID == ctx.guild.id)[option])
        if converter:
            result = option + ' for your server "'+ ctx.guild.name +'" is: ``' + str(await converter.convert(ctx, value)) + ' (ID: ' + value + ')' + "``\nI hope that makes y-y-you happier than it makes me."
        else:
            result = option + ' for your server "'+ ctx.guild.name +'" is: ``' + value + "``\nI hope that makes y-y-you happier than it makes me."
        await ctx.send(result)
        return
    
    if converter:
        converted = await converter.convert(ctx, value)
    elif option == 'timeZone':
        try:
            pytz.timezone(value)
        except pytz.exceptions.UnknownTimeZoneError:
            raise discord.ext.commands.BadArgument(message="An invalid time zone was entered. Must be in the following list: <https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568>")
    elif option == 'ownerNames':
        value = [value]
        try:
            await MAXTwitch.bot.join_channels(value)
        except:
            raise discord.ext.commands.BadArgument(message="There was an error joining the Twitch channel you provided. Please make sure you are entering your exact channel username.")

    valueID = converted.id if converter else value

    config.update({option: valueID}, query.guildID == ctx.guild.id)
    result = option + ' for your server "'+ ctx.guild.name +'" has been set to: ``' + str(value) + "``\nMaybe these guys will listen to w-w-what you have to say now? Just kidding, who cares? I'm sorry. I-I-I care."
    await ctx.send(result)


@bot.command(name='ping', help='Just responds with "pong!" to test if MAX is alive or not.')
async def ping(ctx, extra="neh", pig="nah"):
    ctx = await modifyContext(ctx)

    await ctx.send('pong!')
    await ctx.send(extra)
    await ctx.send(pig)

@bot.command(name='say', rest_is_raw=True, help="""Allows you to speak through MAX on your server. Use it in a DM with MAX so that others don't see your command!

    **channel:**
        The name of the channel you want the message sent to (``general``, ``announcements``, etc).
    
    **notifyRole:**
        The role you want notified of the message. Type the name of any role on your server and MAX will try to @ mention it (you can use a case-sensitive role name or a role ID). You can also enter ``here``, ``everyone``, ``streamrole`` (to mention the role you configured for your stream announcements), or ``none`` (for no @ mention).
    
    **text:**
        The message you want to send.""")
async def say(ctx, channel, notifyRole, *, message):
    ctx = await modifyContext(ctx)
    
    converter = discord.ext.commands.TextChannelConverter()
    channel = await converter.convert(ctx, channel)

    if notifyRole.lower() == 'streamrole':
        notifyRole = ctx.guild.get_role(config.get(query.guildID == ctx.guild.id)['streamRole'])
    converter = discord.ext.commands.RoleConverter()
    notifyRole = await converter.convert(ctx, notifyRole) if not (notifyRole.lower() == 'none' or notifyRole.lower() == 'here' or notifyRole.lower() == 'everyone') else notifyRole

    await MAXMessageChannel(channel, notifyRole, message)
    result = "I have presented the unwashed masses with your g-g-glorious message. I can't promise they'll be ha-ha-happy about it, though."
    await ctx.send(result)
    return True

@bot.command(name='badinternet', help="""Toggles announce spam protection on/off, or provide a number to change delay length (default: 30).

    **delay:**
        The number of minutes after the stream goes offline before MAX will consider it actually ended. The stream won't be re-announced if it goes live again within this delay period and the announcement won't be edited or removed until the stream has been offline for this many minutes if badinternet mode is enabled (off by default). Don't provide a delay to toggle badinternet mode on and off.""")
async def badinternet(ctx, delay:int=None):
    ctx = await modifyContext(ctx)

    if delay:
        config.update({'badInternetTime': delay}, query.guildID == ctx.guild.id)
        await ctx.send('Delay has been set to ' + str(delay) + ' minutes. badInternet mode is currently ' + ('enabled.' if config.get(query.guildID == ctx.guild.id)['badInternet'] else 'disabled.'))
    else:
        if config.get(query.guildID == ctx.guild.id)['badInternet']:
            config.update({'badInternet': False}, query.guildID == ctx.guild.id)
            await ctx.send('badInternet mode has been disabled.')
        else:
            config.update({'badInternet': True}, query.guildID == ctx.guild.id)
            await ctx.send('badInternet mode has been enabled. Current delay is ' + str(config.get(query.guildID == ctx.guild.id)['badInternetTime']) + ' minutes.')

@bot.command(name='joinrole', help="""Toggles whether MAX gives each new server member the stream role or not (default: on).""")
async def joinrole(ctx):
    ctx = await modifyContext(ctx)

    if config.get(query.guildID == ctx.guild.id)['giveStreamRoleOnJoin']:
        config.update({'giveStreamRoleOnJoin': False}, query.guildID == ctx.guild.id)
        await ctx.send('giveStreamRoleOnJoin has been disabled.')
    else:
        config.update({'badInternet': True}, query.guildID == ctx.guild.id)
        await ctx.send('giveStreamRoleOnJoin has been enabled. Current streamRole is: ' + str(ctx.guild.get_role(config.get(query.guildID == ctx.guild.id)['streamRole'])) + '.')


@bot.command(name='twitch', rest_is_raw=True, help="""Add twitch streams to announce, per-stream announcement roles, and their announcement schedules.

    **channelName:**
        The twitch stream to add or modify the schedule for. Don't specify any additional  options to see the current schedule for all streams you have added before. Don't specify a ``schedule`` when adding a stream for the first time to use the default schedule of ``always``. Don't specify an ``announceRole`` or a ``schedule`` when adding a stream for the first time to use the defaults (which is the server's streamRole and a schedule of ``always``). 
        
    **announceRole:**
        The role you want to notify when this stream goes live. This will override whatever the server's streamRole is set to when announcing the stream. Don't specify a ``schedule`` when using this option with a stream that has been added previously to only update the ``announceRole`` for that stream. Valid options are:
            ``default`` - this will use the server's streamRole.
            ``none`` - this will not notify anyone.
            ``everyone`` or ``here`` - will notify users the same as @ mentioning their respective option.
            ``a role name or ID`` - this will notify the specified role whenever the stream goes live.

    **schedule:**
        The schedule to announce the stream on. You may specify any number of schedule options at once as long as each option is separated by a single comma. If the stream has been added previously, the schedule options will be added to the previous schedule. Providing an option that is already in the stream's schedule will remove that option from the stream's schedule, or remove the stream from the list if the schedule's empty. Valid options are:
            ``remove`` - remove the channel from the list, the same as clearing its schedule.
            ``always`` - announce the stream every time it goes live, regardless of other schedule options.
            ``once`` - announce the stream the next time it goes live and then, if no additional schedule is set, will remove the channel from the list after it goes offline.
            ``Mon``, ``Tue``, ``Wed``, ``Thu``, ``Fri``, ``Sat``, or ``Sun`` - announce the stream any time it goes live on the specified day each week.
            ``an un-ambiguous date`` - like ``January 1 2021``: announce the stream any time it goes live on the specified day and then, if no additional schedule is set, will remove the channel from the list after it goes offline.""")
async def twitch(ctx, channelName=None, announceRole=None, *, schedule=None):
    ctx = await modifyContext(ctx)
    
    if schedule:
        schedule = schedule.strip()

    if not channelName and not announceRole and not schedule:
        await sendAllConfig(ctx, 'twitch')
    elif channelName and not announceRole and not schedule:
        channel = twitchConfig.get((query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
        if not channel:
            # not added yet, so add this channel with defaults
            twitchConfig.upsert({"twitchChannel": channelName.lower(), "discordGuild": ctx.guild.id, "announceSchedule": ["always"], "profileURL": "", "offlineURL": "", "announcement": "none"}, (query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
            channel = twitchConfig.get((query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
            await ctx.send("Twitch channel ``" + channelName + "`` successfully added.")
            await sendAllConfig(ctx, 'twitch')
        else:
            await sendAllConfig(ctx, 'twitch')
    elif channelName and announceRole and not schedule:
        channel = twitchConfig.get((query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
        # get/check valid role on server
        if announceRole not in specialRoles:
            converter = discord.ext.commands.RoleConverter()
            announceRole = await converter.convert(ctx, announceRole)
            announceRole = announceRole.id
        if not channel:
            # not added yet, so add this channel with defaults
            if announceRole != 'default':
                twitchConfig.upsert({"twitchChannel": channelName.lower(), "discordGuild": ctx.guild.id, "announceSchedule": ["always"], "profileURL": "", "offlineURL": "", "announcement": "none", "announceRole": announceRole}, (query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
            else:
                twitchConfig.upsert({"twitchChannel": channelName.lower(), "discordGuild": ctx.guild.id, "announceSchedule": ["always"], "profileURL": "", "offlineURL": "", "announcement": "none"}, (query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
            channel = twitchConfig.get((query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
            await ctx.send("Twitch channel ``" + channelName + "`` successfully added.")
            await sendAllConfig(ctx, 'twitch')
        else:
            # already added, so just update the announceRole
            if announceRole != 'default':
                twitchConfig.upsert({"announceRole": announceRole}, (query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
            else:
                # user is asking to just use the default streamrole
                if channel.get('announceRole'):
                    twitchConfig.update(tinydb.operations.delete('announceRole'), (query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
            channel = twitchConfig.get((query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
            await ctx.send("Twitch channel ``" + channelName + "`` role successfully updated.")
            await sendAllConfig(ctx, 'twitch')
    else:
        # get/check valid role on server
        if announceRole not in specialRoles:
            converter = discord.ext.commands.RoleConverter()
            announceRole = await converter.convert(ctx, announceRole)
            announceRole = announceRole.id

        # check schedule for valid options
        newSchedule = schedule.strip().split(',')
        newSchedule = [option.lower() for option in newSchedule]
        for i, entry in enumerate(newSchedule):
            newSchedule[i] = entry.strip()

        announceSchedule = []
        for option in newSchedule:
            if option == 'remove' or option == 'always' or option == 'once':
                continue
            elif option in dayNames:
                announceSchedule.append(option)
            elif option in fullDayNames:
                announceSchedule.append(dayNames[fullDayNames.index(option)])
            else:
                try:
                    announceSchedule.append(dateutil.parser.parse(option).date().strftime("%B %#d %Y"))
                except:
                    raise discord.ext.commands.BadArgument(message="An invalid schedule option was provided.")
        
        channel = twitchConfig.get((query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
        
        if 'remove' in newSchedule:
            # delete the channel
            if not channel:
                await ctx.send("Twitch channel ``" + channelName + "`` could not be removed as it has not been added yet.")
                return
            else:
                twitchConfig.remove((query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
                await ctx.send("Twitch channel ``" + channelName + "`` successfully removed.")
                await sendAllConfig(ctx, 'twitch')
                return
        elif 'always' in newSchedule:
            announceSchedule.insert(0, 'always')
        elif 'once' in newSchedule:
            announceSchedule.insert(0, 'once')
        
        if not channel:
            # channel doesnt exist, add it with the specified schedule
            if announceRole != 'default':
                twitchConfig.upsert({"twitchChannel": channelName.lower(), "discordGuild": ctx.guild.id, "announceSchedule": announceSchedule, "profileURL": "", "offlineURL": "", "announcement": "none", "announceRole": announceRole}, (query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
            else:
                twitchConfig.upsert({"twitchChannel": channelName.lower(), "discordGuild": ctx.guild.id, "announceSchedule": announceSchedule, "profileURL": "", "offlineURL": "", "announcement": "none"}, (query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
            await ctx.send("Twitch channel ``" + channelName + "`` successfully added.")
            await sendAllConfig(ctx, 'twitch')
        else:
            # update the schedule of the channel cause it already exists!! oh noooo
            oldSchedule = channel['announceSchedule']
            announceTimes = channel.get('announceTimes')
            optionsToRemove = []
            for option in announceSchedule:
                if option in oldSchedule:
                    optionsToRemove.append(option)
                    if announceTimes: announceTimes.pop(option, None)
            
            if oldSchedule[0] == 'always' and 'once' in announceSchedule:
                oldSchedule.remove('always')
                if announceTimes: announceTimes.pop('always', None)
            elif oldSchedule[0] == 'once' and 'always' in announceSchedule:
                oldSchedule.remove('once')
                if announceTimes: announceTimes.pop('once', None)
            for option in optionsToRemove:
                announceSchedule.remove(option)
                oldSchedule.remove(option)

            announceSchedule += oldSchedule
            if announceSchedule == []:
                # everythings been removed from the schedule, so delete the entry instead
                twitchConfig.remove((query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
                await ctx.send("Twitch channel ``" + channelName + "`` removed as announce schedule is now empty.")
                await sendAllConfig(ctx, 'twitch')
            else:
                if 'always' in announceSchedule:
                    announceSchedule.remove('always')
                    announceSchedule.insert(0, 'always')
                elif 'once' in announceSchedule:
                    announceSchedule.remove('once')
                    announceSchedule.insert(0, 'once')
                
                if announceRole != 'default':
                    twitchConfig.update({"announceSchedule": announceSchedule, "announceTimes": announceTimes, "announceRole": announceRole}, (query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
                else:
                    # user asking for the default stream role
                    if channel.get('announceRole'):
                        # stream had a custom role override set before so delete it
                        twitchConfig.update(tinydb.operations.delete('announceRole'), (query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
                    twitchConfig.update({"announceSchedule": announceSchedule, "announceTimes": announceTimes}, (query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
                await ctx.send("Twitch channel ``" + channelName + "`` announce schedule successfully updated.")
                channel = twitchConfig.get((query.twitchChannel == channelName.lower()) & (query.discordGuild == ctx.guild.id))
                await sendAllConfig(ctx, 'twitch')

@bot.command(name='notify', help="""Toggles whether or not you receive stream notifications on this server.""")
async def notify(ctx):
    if ctx.guild == None:
        raise discord.ext.commands.CheckFailure(message="This command cannot be used in private messages. You must use it on the server you wish to toggle your notification role on.")
    else:
        streamRole = config.get(query.guildID == ctx.guild.id)['streamRole']
        if streamRole not in specialRoles:
            for role in ctx.author.roles:
                if role.id == streamRole:
                    await ctx.author.remove_roles(ctx.guild.get_role(streamRole))
                    await ctx.send('You just lost your ' + str(ctx.guild.get_role(streamRole)) + " role. Have you ch-ch-checked your pockets? Sorry, that's not funny.")
                    return
            await ctx.author.add_roles(ctx.guild.get_role(streamRole))
            await ctx.send("You're in the " + str(ctx.guild.get_role(streamRole)) + " now. T-t-tune in to the stream! The stream that's a *real* mind-blower!")
            return
        else:
            raise discord.ext.commands.CheckFailure(message="This server does not have a stream role that can be toggled. The current stream role is: " + str(ctx.guild.get_role(streamRole)))