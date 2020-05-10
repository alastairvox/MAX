import asyncio, inspect, datetime
import aiohttp
import MAXShared, MAXDiscord, MAXTwitch
from MAXShared import query, devFlag, auth, generalConfig, youtubeConfig, discordConfig, twitchConfig, dayNames, fullDayNames

# overloads print for this module so that all prints (hopefully all the sub functions that get called too) are appended with which service the prints came from
print = MAXShared.printName(print, "SERVER:")



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



async def on_startup(app):
    print('Connected to HTTP server on port 81.')
async def on_shutdown(app):
    print('Disconnected from HTTP server on port 81.')

# gets the table/subsection of config for this service
config = generalConfig

routes = aiohttp.web.RouteTableDef()
app = aiohttp.web.Application()
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)
session = aiohttp.ClientSession()



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



async def subscribeTwitchTopic():
    while not MAXTwitch.bot.http.token:
        await asyncio.sleep(30)
    headers = {"Client-ID": MAXTwitch.bot.http.client_id, "Authorization": "Bearer " + MAXTwitch.bot.http.token}
    async with session.post('https://api.twitch.tv/helix/webhooks/hub', headers=headers, json={'hub.callback': generalConfig.get(query.name == 'callback')['value'] + 'twitch', 'hub.mode': 'subscribe', 'hub.topic': 'https://api.twitch.tv/helix/streams?user_id=520858550', 'hub.lease_seconds': 864000}) as resp:
        print(resp.status)
        print(await resp.text())

async def twitchWS():
    async with session.ws_connect('wss://pubsub-edge.twitch.tv') as ws:
        print('WebSocket session established with Twitch.')
        await ws.send_json({"type": "PING"})
        async for msg in ws:
            if msg.json()['type'] == 'PONG':
                print("Twitch response (pong):", msg.data, "Waiting 30s to PING.")
                await asyncio.sleep(30)
                await ws.send_json({"type": "PING"})
            else:
                print("Twitch response (not pong):", msg.json())

async def echoWS():
    async with session.ws_connect('ws://echo.websocket.org') as ws:
        print('WebSocket session established with Echo Server.')
        await ws.send_json({"dog": "woof"})
        async for msg in ws:
            print("Echo", msg.data)
            await asyncio.sleep(5)
            await ws.send_json({"cat": "kitten"})

async def engage():
    print("Starting...")
    app.add_routes(routes)

    loop = asyncio.get_event_loop()
    loop.create_task(aiohttp.web._run_app(app, port='81', print=None))



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



@routes.get('/')
async def hello(request):
    print('Responding to', request, 'from', request.remote, 'headers', request.headers, 'body', await request.text())
    return aiohttp.web.Response(status=404)

@routes.get('/stream')
async def stream(request):
    print('Responding to', request, 'from', request.remote, 'headers', request.headers, 'body', await request.text())
    return aiohttp.web.Response(status=404)

@routes.get('/youtube/{discordGuild}')
async def youtube(request):
    discordGuild = int(request.match_info['discordGuild'])
    print('Responding to', request)
    if hasattr(request, 'query'):
        channel = request.query.get('hub.topic')
        if channel:
            channel = channel.split('channel_id=')[1]   # [0] = the url https://www.youtube.com/xml/feeds/videos.xml? or any params that came before the channel_id param, [1] = the channel id and any params that come after the channel_id
            channel = channel.split('&')[0]             # [0] = the channel id [1]+ = other params that came after channel_id
        
        hubChallenge = request.query.get('hub.challenge')
        if request.query.get('hub.lease_seconds'):
            leaseSeconds = int(request.query.get('hub.lease_seconds'))-90

        if channel and hubChallenge and leaseSeconds:
            # store them in youtube config, we'll check later to see if we need to renew by by finding the difference between the time it was stored and the time it is now in seconds and seeing if >= leaseSeconds (minus 90) and if it is then resubscribe xx nvm do it the way i say below
            youtubeConfig.update({'leaseSeconds': leaseSeconds, 'time': str(datetime.datetime.now())}, (query.discordGuild == discordGuild) & (query.channelID == channel))
            # CALL FUNCTION THAT AWAITS SLEEP FOR THE NUMBER OF SECONDS EQUAL TO the stored leaseSeconds (because i subtract 90 when storing) then calls the resubscribe, make a function that will look through all the stored youtube channels when discord starts, and calls the same function for each channel that has a leaseSeconds stored
            print('Lease aquired for guild', discordGuild, 'and channel', channel)
            return aiohttp.web.Response(status=200, text=hubChallenge)
        else:
            print('missing channel, challenge or lease: ', await request.text())
            return aiohttp.web.Response(status=404, text="missing channel, challenge or lease")
    else:
        print('Youtube request has no query attribute!')
        print(await request.text())
        return aiohttp.web.Response(status=404, text="what are you doing")

@routes.post('/youtube/{discordGuild}')
async def youtubeUploadedNotification(request):
    discordGuild = int(request.match_info['discordGuild'])
    # store a copy of the youtube video number so i dont re-announce youtube videos if they just get updated, have to parse the xml of the text out for relevant bits
    # pass the text (xml, xml.etree.ElementTree?) and guildID to a discord function that parses out the author name, video title, URL (<link rel="alternate" href="), and the time published and then announces the stream
    print('Responding to', request)
    # we add this to the end of the event loop so that we can return a response to the request right away, allowing us to respond and then process the data later
    loop = asyncio.get_event_loop()
    loop.create_task(MAXDiscord.announceYoutubeUpload(discordGuild, await request.read()))
    return aiohttp.web.Response(status=200)



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


