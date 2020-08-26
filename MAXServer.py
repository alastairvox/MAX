import asyncio, inspect, datetime, json
import aiohttp
import MAXShared, MAXDiscord, MAXTwitch, MAXYoutube, MAXSpotify
from MAXShared import query, devFlag, auth, generalConfig, youtubeConfig, spotifyConfig, discordConfig, twitchConfig, dayNames, fullDayNames

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
    print('Connected to HTTP server on port ' + config.get(query.name == 'callback')['port'] + '.')
async def on_shutdown(app):
    print('Disconnected from HTTP server on port ' + config.get(query.name == 'callback')['port'] + '.')

# gets the table/subsection of config for this service
config = generalConfig

routes = aiohttp.web.RouteTableDef()
app = aiohttp.web.Application()
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)
session = aiohttp.ClientSession()

connectedTwitchWS = None
lastTwitchWSPingReturned = False



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



async def keepTwitchWSAlive():
    while True:
        await asyncio.sleep(259) #259
        if connectedTwitchWS:
            global lastTwitchWSPingReturned
            lastTwitchWSPingReturned = False
            await connectedTwitchWS.send_json({'type': 'PING'})
            await asyncio.sleep(11)
            if not lastTwitchWSPingReturned:
                print('Twitch did not respond to ping, restarting connection.')
                await connectedTwitchWS.close()
        else:
            continue

async def subscribeTwitchTopic():
    while not MAXTwitch.bot.http.token:
        await asyncio.sleep(30)
    headers = {"Client-ID": MAXTwitch.bot.http.client_id, "Authorization": "Bearer " + MAXTwitch.bot.http.token}
    async with session.post('https://api.twitch.tv/helix/webhooks/hub', headers=headers, json={'hub.callback': config.get(query.name == 'callback')['value'] + 'twitch', 'hub.mode': 'subscribe', 'hub.topic': 'https://api.twitch.tv/helix/streams?user_id=520858550', 'hub.lease_seconds': 864000}) as resp:
        print(resp.status)
        print(await resp.text())

async def twitchWS():
    loop = asyncio.get_event_loop()
    loop.create_task(keepTwitchWSAlive())
    while True:
        try:
            async with session.ws_connect('wss://pubsub-edge.twitch.tv', autoping=False) as ws:
                global connectedTwitchWS
                connectedTwitchWS = ws
                print('WebSocket session established with Twitch.')
                # for entry in spotify config that has a "twitchAccessToken" entry:
                # refresh the access tokens
                # request a topic for each entry
                # more topics are added later by calling connectedTwitchWS.send_json
                for entry in spotifyConfig.all():
                    if entry.get("twitchRefreshToken") and entry.get("twitchChannelID"):
                        async with session.post("https://id.twitch.tv/oauth2/token?grant_type=refresh_token&refresh_token="+entry["twitchRefreshToken"]+"&client_id="+auth.get(query.name=='twitch')['clientID']+"&client_secret="+auth.get(query.name=='twitch')['clientSecret']) as resp:
                            info = await resp.json()
                            if not 'error' in info and 'access_token' in info:
                                spotifyConfig.update({'twitchAccessToken': info['access_token'], 'twitchRefreshToken': info['refresh_token']}, query.discordGuild==entry['discordGuild'])
                                accessToken = info['access_token']
                            else:
                                print("Couldn't fetch new access token for", entry["twitchChannelID"], "so attempting to use old token.")
                                accessToken = entry["twitchAccessToken"]
                        await ws.send_json({"type": "LISTEN", "data": {"topics": ['channel-points-channel-v1.'+entry["twitchChannelID"]], "auth_token": accessToken}})
                async for msg in ws:
                    if msg.json():
                        msgJSON = msg.json()
                        
                        successDict = {"type":"RESPONSE","error":"","nonce":""}
                        
                        if msgJSON.get('type') == "PONG":
                            global lastTwitchWSPingReturned
                            lastTwitchWSPingReturned = True
                        elif msgJSON.get('type') == "RECONNECT":
                            print('Twitch requested reconnect. Waiting 15 seconds and reconnecting.')
                            await asyncio.sleep(15)
                            break
                        elif msgJSON.get('type') == 'MESSAGE' and msgJSON.get('data') and msgJSON['data'].get('message'):
                            # message is a fucking string for some reason...
                            msgJSONMessage = json.loads(msgJSON['data']['message'])
                            if msgJSONMessage and msgJSONMessage.get('type') == "reward-redeemed" and msgJSONMessage.get('data'):
                                rewardData = msgJSONMessage['data']
                                print("Reward redeemed.")

                                channelID = str(rewardData['redemption']['channel_id'])
                                channelEntry = spotifyConfig.get(query.twitchChannelID == channelID)
                                
                                if channelEntry:
                                    monitoredReward = channelEntry['rewardName']
                                    
                                    if rewardData['redemption']['reward']['title'] == monitoredReward:
                                        # check if strimmer is live, if not send a message
                                        # streamLive = True
                                        streamLive = await MAXTwitch.bot.get_stream(channel=channelID)
                                        if streamLive:
                                            loop = asyncio.get_event_loop()
                                            loop.create_task(MAXSpotify.songRequest(discordGuild=channelEntry['discordGuild'], song=rewardData['redemption']['user_input'].strip()))
                                        else:
                                            print("Stream is offline, won't request.")
                                            await MAXTwitch.messageLinkedTwitchChannel(channelEntry['discordGuild'], "You can not redeem songs while the stream is offline. Goodbye cha-cha-channel points!")
                                    elif rewardData['redemption']['reward']['title'] == "Skip Current Song":
                                        # check if strimmer is live, if not send a message
                                        streamLive = True
                                        # streamLive = await MAXTwitch.bot.get_stream(channel=channelID)
                                        if streamLive:
                                            loop = asyncio.get_event_loop()
                                            loop.create_task(MAXSpotify.songRequest(discordGuild=channelEntry['discordGuild'], song=rewardData['redemption']['user_input'].strip()))
                                        else:
                                            print("Stream is offline, won't request.")
                                            await MAXTwitch.messageLinkedTwitchChannel(channelEntry['discordGuild'], "You can not redeem songs while the stream is offline. Goodbye cha-cha-channel points!")

                        elif msgJSON == successDict:
                            print("Twitch sent a success response, likely began listening to a channel successfully.")
                        else:
                            print("Twitch response (not pong, reconnect, reward, success):", msg.data)
                    else:
                        print("Twitch response (not JSON):", msg.data)
                print('TwitchWS connection ended.')
                connectedTwitchWS = None
                continue
        except Exception as error:
            print('Error: There was an error with Twitch websocket connection: ', repr(error))
            connectedTwitchWS = None
            continue

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
    loop.create_task(aiohttp.web._run_app(app, port=config.get(query.name == 'callback')['port'], print=None))



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



@routes.get('/spotify/auth/{discordGuild}')
async def spotifyAuth(request):
    discordGuild = int(request.match_info['discordGuild'])
    spotifyEntry = spotifyConfig.get(query.discordGuild == discordGuild)
    if spotifyEntry:
        raise aiohttp.web.HTTPTemporaryRedirect("https://accounts.spotify.com/authorize?client_id="+auth.get(query.name=='spotify')['clientID']+"&response_type=code&redirect_uri="+generalConfig.get(query.name == 'callback')['value']+"spotify/callback&state="+str(discordGuild)+"&scope=user-read-playback-state user-modify-playback-state user-read-currently-playing user-read-recently-played user-read-private")
    else:
        return aiohttp.web.Response(text="""<div style="height: 100%; display: flex; justify-content: center; align-items: center"><div><b>Error: You must first call MAX's "spotify" command to enable authorization for your server.</b></div></div>""", content_type="text/html")

@routes.get('/spotify/callback')
async def spotifyCallback(request):
    if 'code' not in request.query or 'state' not in request.query:
        return aiohttp.web.Response(text="""<div style="height: 100%; display: flex; justify-content: center; align-items: center"><div><b>Error: Something went wrong with Spotify authorization.</b><br>Please follow the link that MAX provided to try authorization again, or copy and paste it into your browser's URL bar.</div></div>""", content_type="text/html")
    else:
        await MAXSpotify.createClient(discordGuild=int(request.query['state']), code=request.query['code'])
    return aiohttp.web.Response(text="""<div style="height: 100%; display: flex; justify-content: center; align-items: center"><div><b>Spotify authorization successful!</b><br>If you haven't yet, please follow the second link that MAX provided to authorize with Twitch.</div></div>""", content_type="text/html")

@routes.get('/twitch/auth/{discordGuild}')
async def twitchAuth(request):
    discordGuild = int(request.match_info['discordGuild'])
    spotifyEntry = spotifyConfig.get(query.discordGuild == discordGuild)
    if spotifyEntry:
        raise aiohttp.web.HTTPTemporaryRedirect("https://id.twitch.tv/oauth2/authorize?client_id="+auth.get(query.name=='twitch')['clientID']+"&redirect_uri="+generalConfig.get(query.name == 'callback')['value']+"twitch/callback&response_type=code&scope=channel:read:redemptions&state="+str(discordGuild))
    else:
        return aiohttp.web.Response(text="""<div style="height: 100%; display: flex; justify-content: center; align-items: center"><div><b>Error: You must first call MAX's "spotify" command to enable authorization for your server.</b></div></div>""", content_type="text/html")

@routes.get('/twitch/callback')
async def twitchCallback(request):
    if 'code' not in request.query or 'state' not in request.query:
        return aiohttp.web.Response(text="""<div style="height: 100%; display: flex; justify-content: center; align-items: center"><div><b>Error: Something went wrong with Twitch authorization.</b><br>Please follow the link that MAX provided to try authorization again, or copy and paste it into your browser's URL bar.</div></div>""", content_type="text/html")
    else:
        # get access token, refresh token, channel id
        async with session.post("https://id.twitch.tv/oauth2/token?client_id="+auth.get(query.name=='twitch')['clientID']+"&client_secret="+auth.get(query.name=='twitch')['clientSecret']+"&code="+request.query['code']+"&grant_type=authorization_code&redirect_uri="+generalConfig.get(query.name == 'callback')['value']+"twitch/callback") as resp:
            # json encoded access token returned
            info = await resp.json()
            if info and info.get('access_token') and info.get('refresh_token'):
                headers = {"Client-ID": auth.get(query.name=='twitch')['clientID'], "Authorization": "Bearer " + info['access_token']}
                async with session.get("https://api.twitch.tv/helix/users", headers=headers) as resp2:
                    # json with user info returned
                    user = await resp2.json()
                    if user and user.get('data') and type(user['data']) == list and user['data'][0].get('id'):
                        spotifyConfig.update({'twitchAccessToken': info['access_token'], 'twitchRefreshToken': info['refresh_token'], 'twitchChannelID': user['data'][0]['id']}, query.discordGuild==int(request.query['state']))
                        # start listening to channel now that its been added
                        while not connectedTwitchWS:
                            await asyncio.sleep(1)
                        await connectedTwitchWS.send_json({"type": "LISTEN", "data": {"topics": ['channel-points-channel-v1.'+user['data'][0]['id']], "auth_token": info['access_token']}})
                    else:
                        return aiohttp.web.Response(text="""<div style="height: 100%; display: flex; justify-content: center; align-items: center"><div><b>Error: Something went wrong with Twitch authorization.</b><br>Please follow the link that MAX provided to try authorization again, or copy and paste it into your browser's URL bar.</div></div>""", content_type="text/html")
            else:
                return aiohttp.web.Response(text="""<div style="height: 100%; display: flex; justify-content: center; align-items: center"><div><b>Error: Something went wrong with Twitch authorization.</b><br>Please follow the link that MAX provided to try authorization again, or copy and paste it into your browser's URL bar.</div></div>""", content_type="text/html")
    return aiohttp.web.Response(text="""<div style="height: 100%; display: flex; justify-content: center; align-items: center"><div><b>Twitch authorization successful!</b><br>If you haven't yet, please follow the second link that MAX provided to authorize with Spotify.</div></div>""", content_type="text/html")

# editing this out to hopefully not have to deal with the possibility that aiohhtp parses an attack message :(
# @routes.get('/')
# async def hello(request):
#     #print('Responding to', request, 'from', request.remote, 'headers', request.headers, 'body', await request.text())
#     print('Responding to', request, 'from', request.remote)
#     return aiohttp.web.Response(status=404)

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
            loop = asyncio.get_event_loop()
            loop.create_task(MAXYoutube.youtubeWaitForResub(leaseSeconds, discordGuild, channel))
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