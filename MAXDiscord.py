import discord, discord.ext.commands
import itertools
import MAXShared
from MAXShared import query, authDB, configDB, dev

# overloads print for this module so that all prints (hopefully all the sub functions that get called too) are appended with which module the prints came from
print = MAXShared.printName(print, "DISCORD:")
config = configDB.table('discord')

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

def getGuildPrefix(bot, message):
    if message.guild:
        guildConfig = config.get(query.guildID == message.guild.id)
    else:
        # if there is no guild id then this is a private message, so no prefix
        return ""
    return guildConfig['prefix'] if guildConfig else "!"

description = """Ah, 'tis Max Headroom here, and I quote fro-fro-from the bard, Shakespeare, a writer:

*"I can performeth thine following commands:*"""
bot = discord.ext.commands.Bot(command_prefix=getGuildPrefix, description=description, case_insensitive=True, help_command=MAXHelpCommand())

@bot.event
async def on_ready():
    print(f'Connected as {bot.user}.')

@bot.command(name='ping', help='Just responds with "pong!" to test if MAX is alive or not.')
async def ping(ctx):
    await ctx.send('pong!')

@bot.command(name='say', help="""Allows you to speak through MAX on your server. Use it in a DM with MAX so that others don't see your command!

    **channel:**
        The name of the channel you want the message sent to (general, announcements, etc).
    
    **notifyRole:**
        The role you want notified of the message. Type the name of any role on your server and MAX will try to @ mention it (spell it right!). You can also enter here, everyone, streamrole (to mention the role you configured for your stream announcements), or none (for no @ mention).
    
    **text:**
        The message you want to send.""")
async def say(ctx, channel, notifyRole, text):
    # if the context being passed in is from a discord event/called from a discord message then its an instance of the Context class from the discord.py API
    if type(ctx) == discord.ext.commands.Context:
        # check if the userID owns a server in the database
        await ctx.send(channel, notifyRole, text)
    # otherwise this function is being called from another function
    else:
        # called from another function
        # check if the user name is registered with a server in the database
        # check if they supplied a channel (otherwise use general), check if the supplied channel exists
        await print("Hello!")

async def engage():
    print("Engaging...")
    discordToken = authDB.get(query.name == 'discord')['devToken'] if dev else authDB.get(query.name == 'discord')['token']
    await bot.start(discordToken, reconnect=True)