import discord
import discord.ext.commands
import asyncio
import MAXDecorators

# overloads print for this module so that all prints (hopefully all the sub functions that get called too) are appended with which module the prints came from
print = MAXDecorators.printName(print, "DISCORD:")

async def engage(query, authDB, configDB, config, dev):
    print("Engaging...")
    
    def getGuildPrefix(bot, message):
        guildConfig = config.get(query.guildID == message.guild.id)
        return guildConfig['prefix'] if guildConfig else "!"

    bot = discord.ext.commands.Bot(command_prefix=getGuildPrefix, case_insensitive=True)

    @bot.event
    async def on_ready():
        print(f'Connected as {bot.user}.')

    @bot.command(name='ping')
    async def ping(ctx):
        await ctx.send('pong!')

    discordToken = authDB.get(query.name == 'discord')['devToken'] if dev else authDB.get(query.name == 'discord')['token']
    await bot.start(discordToken, reconnect=True)