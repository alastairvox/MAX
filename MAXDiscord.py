import itertools, sys, traceback, asyncio
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

bot = discord.ext.commands.Bot(command_prefix=getGuildPrefix, case_insensitive=True, help_command=MAXHelpCommand(), description=description)


# ---------- FUNCTIONS ----------
#
#
#
# ---------- FUNCTIONS ----------


# starts the bot when called
async def engage():
    print("Engaging...")
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


# ---------- EVENTS ----------
#
#
#
# ---------- EVENTS ----------


@bot.event
async def on_ready():
    print(f'Connected as {bot.user}.')
    # get all the guilds MAX is connected to and check if they all have entries in the config file, if not then create a default one

@bot.event
async def on_command(ctx):
    print('Command', '"'+ ctx.invoked_with +'"','invoked by', ctx.author.name + '#' + ctx.author.discriminator, '('+ str(ctx.author.id) +')', 'on server "' + str(ctx.guild) + '".' if not ctx.guild == None else 'in private message.')

@bot.event
async def on_command_error(ctx, error):
    """The event triggered when an error is raised while invoking a command.
    ctx   : Context
    error : Exception"""
    
    # check if internal or external command
    if ctx.message.id == 0:
        print('SHITS FAKE YO')

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
            return await ctx.author.send(f'{ctx.command} can not be used in Private Messages.')
        except:
            pass
    elif isinstance(error, discord.ext.commands.UserInputError):
        print('Error: ' + str(error))
        errorResponse = '**Error:** ' + str(error) + ' Use ``' + ctx.prefix + 'help ' + ctx.command.name + '`` for more information on this command.```' + ctx.prefix + ctx.command.name + ' ' + ctx.command.signature + '```'
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


@bot.command(name='ping', help='Just responds with "pong!" to test if MAX is alive or not.')
async def ping(ctx):
    await ctx.send('pong!')

@bot.command(name='say', rest_is_raw=True, help="""Allows you to speak through MAX on your server. Use it in a DM with MAX so that others don't see your command!

    **channel:**
        The name of the channel you want the message sent to (general, announcements, etc).
    
    **notifyRole:**
        The role you want notified of the message. Type the name of any role on your server and MAX will try to @ mention it (you can use a case-sensitive role name or a role ID). You can also enter here, everyone, streamrole (to mention the role you configured for your stream announcements), or none (for no @ mention).
    
    **text:**
        The message you want to send.""")
async def say(ctx, channel, notifyRole, *, message):
    # if the context being passed in is from a discord event/called from a discord message then its an instance of the Context class from the discord.py API
    internal = type(ctx) == discord.ext.commands.Context
    
    # uses an actual context and changes its guild if called from discord, otherwise creates a fake context and sets the guild if called form another service (ctx is username)
    async def setContextGuild(ctx):
        if internal:
            # manually change the context's guild to be the guild the user owns so we can just use the converters
            ctx.guild = bot.get_guild(config.get(query.owner == ctx.author.id)['guildID']) if config.get(query.owner == ctx.author.id) else None
            return ctx
        else:
            userName = ctx
            ctx = await createFakeContext()
            for entry in config:
                if userName in entry['ownerNames']:
                    ctx.guild = bot.get_guild(entry['guildID'])
                    break
            return ctx

    # save the original context in case there are errors to yell about?
    originalContext = ctx

    # change the guild to the one we want to check so we can use converters
    ctx = await setContextGuild(ctx)
    
    # if there was no guild associated with the author/username
    if not ctx.guild:
        return False

    converter = discord.ext.commands.TextChannelConverter()
    channel = await converter.convert(ctx, channel)

    if notifyRole.lower() == 'streamrole':
        notifyRole = ctx.guild.get_role(config.get(query.guildID == ctx.guild.id)['streamRole'])

    converter = discord.ext.commands.RoleConverter()
    notifyRole = await converter.convert(ctx, notifyRole) if not (notifyRole.lower() == 'none' or notifyRole.lower() == 'here' or notifyRole.lower() == 'everyone') else notifyRole

    ctx = originalContext if internal else ctx

    await MAXMessageChannel(channel, notifyRole, message)
    if internal:
        await ctx.send("I have presented the unwashed masses with your g-g-glorious message. I can't promise they'll be ha-ha-happy about it, though.")
    return True
