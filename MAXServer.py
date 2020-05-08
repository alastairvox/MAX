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
    async with session.post('https://api.twitch.tv/helix/webhooks/hub', headers=headers, json={'hub.callback': 'http://172.103.254.14:81/twitch', 'hub.mode': 'subscribe', 'hub.topic': 'https://api.twitch.tv/helix/streams?user_id=520858550', 'hub.lease_seconds': 864000}) as resp:
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
    print('Responding to HTTP request to "/".')
    return aiohttp.web.Response(text="Hello, world")

@routes.get('/stream')
async def stream(request):
    print('Responding to HTTP request to "/twitch".')
    print(request)

@routes.get('/youtube/{discordGuild}')
async def youtube(request):
    discordGuild = int(request.match_info['discordGuild'])
    print('Responding to HTTP get to "/youtube/' + str(discordGuild) + '":', request)
    if hasattr(request, 'query'):
        channel = request.query.get('hub.topic')
        if channel:
            channel = channel.split('channel_id=')[1]   # [0] = the url https://www.youtube.com/xml/feeds/videos.xml? or any params that came before the channel_id param, [1] = the channel id and any params that come after the channel_id
            channel = channel.split('&')[0]             # [0] = the channel id [1]+ = other params that came after channel_id
        
        hubChallenge = request.query.get('hub.challenge')
        leaseSeconds = request.query.get('hub.lease_seconds')

        if channel and hubChallenge and leaseSeconds:
            # store them in youtube config, we'll check later to see if we need to renew by by finding the difference between the time it was stored and the time it is now in seconds and seeing if >= leaseSeconds (minus 90) and if it is then 
            youtubeConfig.update({'leaseSeconds': leaseSeconds, 'time': str(datetime.datetime.now())}, (query.discordGuild == discordGuild) & (query.channelID == channel))
            return aiohttp.web.Response(status=200, text=hubChallenge)
        else:
            print(request.text())
            return aiohttp.web.Response(status=404, text="invalid request")
    else:
        print('Youtube request has no query attribute!')
        print(request.text())
        return aiohttp.web.Response(status=404, text="what are you doing")

@routes.post('/youtube/{discordGuild}')
async def youtubeUploadedNotification(request):
    discordGuild = int(request.match_info['discordGuild'])
    # store a copy of the youtube video number so i dont re-announce youtube videos if they just get updated, have to parse the xml of the text out for relevant bits
    print('Responding to HTTP post to "/youtube/' + str(discordGuild) + '":', request, 'contenttype-', request.content_type, 'text-', await request.text(), 'headers-', request.headers)
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


