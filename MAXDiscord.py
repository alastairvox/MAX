import discord, discord.ext.commands
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
        self.no_category = "**Commands**"
        self.paginator = discord.ext.commands.Paginator(prefix='', suffix='', max_size=2000)
    def get_max_size(self, commands):
        defaultSize = super().get_max_size(commands)
        return defaultSize + 1
    def get_ending_note(self):
        # mostly copied from the original definition v
        command_name = self.invoked_with
        return '*I also giveth users a role when they join a server and announceth Twitch and YouTube streams when they go live."*\n\n' \
                "Type {0}{1} command for more info on a command. Mo-mo-more questions? Don't shoot the messenger: ask DrawnActor#0001.".format(self.clean_prefix, command_name)

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

@bot.command(name='say', help="""Allows you to speak through MAX on your server. Use it in a DM with MAX so that others don't see your command.

    channel:
        The name of the channel you want the message sent to (general, announcements, etc).
    
    notifyRole:
        The role you want notified of the message. Type the name of any role on your server and MAX will try to @ mention it (spell it right!). You can also enter here, everyone, streamrole (to mention the role you configured for your stream announcements), or none (for no @ mention).
    
    text:
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