import itertools, sys, traceback, asyncio, copy
import discord, discord.ext.commands
import MAXShared
from MAXShared import query, authDB, configDB, dev

# overloads print for this module so that all prints (hopefully all the sub functions that get called too) are appended with which service the prints came from
print = MAXShared.printName(print, "DISCORD:")


# ---------- SETUP ----------
#
#
#
# ---------- SETUP ----------


# gets the table/sub section of config for this service
config = configDB.table('discord')

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


# ---------- FUNCTIONS ----------
#
#
#
# ---------- FUNCTIONS ----------


# starts the bot when called
async def engage():
    print("Starting...")
    discordToken = authDB.get(query.name == 'discord')['devToken'] if dev else authDB.get(query.name == 'discord')['token']
    await bot.start(discordToken, reconnect=True)

# creates and returns a fake context for calling commands externally
async def createFakeContext():
    fakeData = {'id': 0, 'attachments': [], 'embeds': [], 'edited_timestamp': None, 'type': None, 'pinned': None, 'mention_everyone': None, 'tts': None, 'content': None}
    fakeMessage = discord.Message(state=None,channel=None,data=fakeData)
    fakeContext = discord.ext.commands.Context(prefix=None, message=fakeMessage, bot=bot, guild=None)
    return fakeContext

# sends a message to a specified channel and notifies the specified role
async def MAXMessageChannel(channel, role, message):
    print('Sending message to "' + str(channel.guild) + '" in "' + str(channel) + '" and notifying "' + str(role) + '".')
    # cast to string in case it's a Role object which doesnt have a function for lower, Role object gives its name as a string when cast
    if role == None or str(role).lower() == 'none':
        # since Context is built from a Message, interally ctx.send() effectively uses channel.send() too
        await channel.send(message)
    elif str(role).lower() == 'everyone':
        await channel.send('@everyone' + message)
    elif str(role).lower() == 'here':
        await channel.send('@here' + message)
    else:
        if role.mentionable:
            await channel.send(role.mention + message)
        else:
            # shouldn't need to do this soon because of changes to mentionable roles permissions, but for now even though its technically changed it isnt for bots
            # https://www.reddit.com/r/discordapp/comments/f62o6f/role_mentions_from_administrators_will_now_ping/fi2hqra/
            await role.edit(mentionable=True, reason="Making mentionable to highlight message.")
            await channel.send(role.mention + message)
            await role.edit(mentionable=False, reason="Sent message.")

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
        userName = ctx
        ctx = await createFakeContext()
        for entry in config:
            if userName in entry['ownerNames']:
                ctx.guild = bot.get_guild(entry['guildID'])
                break
        ctx.internal = internal
        ctx.originalCtx = originalCtx
        ctx.userName = userName
        # if no guild was associated with the external user
        if ctx.guild == None:
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
            defaultConfig = {'guildID': guild.id, 'owner': guild.owner.id, 'ownerNames': [], 'botChannel': defaultChannel.id, 'announceChannel': defaultChannel.id, 'streamRole': 'everyone', 'useActivity': False, 'deleteAnnouncements': True, 'badInternet': False}
            config.upsert(defaultConfig, query.guildID == guild.id)


# ---------- EVENTS ----------
#
#
#
# ---------- EVENTS ----------


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
    print('Command', '"'+ ctx.invoked_with +'"','invoked by', str(ctx.author), '('+ str(ctx.author.id) +')', 'on server "' + str(ctx.guild) + '".' if not ctx.guild == None else 'in private message.')

@bot.event
async def on_command_error(ctx, error):
    """The event triggered when an error is raised while invoking a command.
    ctx   : Context
    error : Exception"""

    if hasattr(ctx, 'internal'):
        if not ctx.internal:
            print("This an external command, my guy. We gotta raise another error or something maybe? Somehow pass this shit back.")
            return
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


# ---------- COMMANDS ----------
#
#
#
# ---------- COMMANDS ----------


@bot.command(name='configure', help="""Check or change MAX options like announcement channel, command prefix, stream role, etc.

    **option:**
        The option you want to check or change (not case-sensitive):
            ``prefix`` - the prefix (``!``, ``.``, ``-``, etc) that you want MAX to use for commands on your server.
            ``owner`` - the user (name or ID) that you want to be allowed to configure MAX or access sensitive commands.
            ``botChannel`` - the channel (name or ID) you want MAX to tell people to use commands in (when making announcements, etc).
            ``announceChannel`` - the channel (name or ID) you want MAX to make announcements in.
            ``streamRole`` - the role (name or ID) that you want MAX to @ mention for announcements and give to users when they join the server (can also be ``everyone``, ``here``, or ``none``). Since MAX keeps roles internally by ID, you don't have to use this if you have only changed the name of your previous stream role: just when you want to change it to a different role object that already exists.
    
    **value:**
        The new value for the specified option (case-sensitive). Don't include this in your command if you just want to check what it's currently set to.""")
async def configure(ctx, option, value=None):
    ctx = await modifyContext(ctx)

    option = option.lower()    
    if option == 'prefix':
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
        if ctx.internal:
            await ctx.send(result)
        return
    
    converted = await converter.convert(ctx, value)
    valueID = converted.id if converter else value

    config.update({option: valueID}, query.guildID == ctx.guild.id)
    result = option + ' for your server "'+ ctx.guild.name +'" has been set to: ``' + str(value) + "``\nMaybe these guys will listen to w-w-what you have to say now? Just kidding, who cares? I'm sorry. I-I-I care."
    if ctx.internal:
        await ctx.send(result)


@bot.command(name='ping', help='Just responds with "pong!" to test if MAX is alive or not.')
async def ping(ctx):
    await ctx.send('pong!')

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
    if ctx.internal:
        await ctx.send(result)
    return True
