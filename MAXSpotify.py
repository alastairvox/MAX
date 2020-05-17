import asyncio, inspect, datetime, spotipy
import aiohttp
import MAXShared, MAXDiscord, MAXTwitch, MAXYoutube, MAXServer
from MAXShared import query, devFlag, auth, generalConfig, youtubeConfig, discordConfig, spotifyConfig, twitchConfig, dayNames, fullDayNames, configPath

# overloads print for this module so that all prints (hopefully all the sub functions that get called too) are appended with which service the prints came from
print = MAXShared.printName(print, "SPOTIFY:")



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
config = spotifyConfig

credentials = {}
requestedSongs = {}
oldSongs = {}


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



async def findSong(spotify, song):
    # url = https://open.spotify.com/track/7mZTno9Pj6JJPRjfmNQ21H?si=NPNHhBVgRmycobAeIAWBqA
    # uri = spotify:track:7mZTno9Pj6JJPRjfmNQ21H
    # id = 7mZTno9Pj6JJPRjfmNQ21H
    # takes a uri, url or id!
    try:
        result = spotify.tracks(tracks=[song], market='from_token')
    except spotipy.exceptions.SpotifyException:
        result = spotify.search(q=song, limit=1, type="track", market='from_token')
        if not result.get('tracks'):
            # big ewwowr widdle boyw - not a song id and song not found in search
            error = "Error: Your search: " + '"' + song + '"' + " didn't return any songs."
            print(error)
            return error
        elif not result['tracks'].get('items'):
            # big ewwowr widdle boyw - not a song id and song not found in search
            error = "Error: Your search: " + '"' + song + '"' + " didn't return any songs."
            print(error)
            return error
            
    if result.get('error') or not result['tracks'] or not (type(result['tracks']) == list and result['tracks'][0]):
        result = spotify.search(q=song, limit=1, type="track", market='from_token')
        if not result.get('tracks'):
            # big ewwowr widdle boyw - not a song id and song not found in search
            error = "Error: Your search: " + '"' + song + '"' + " didn't return any songs."
            print(error)
            return error
        elif not result['tracks'].get('items'):
            # big ewwowr widdle boyw - not a song id and song not found in search
            error = "Error: Your search: " + '"' + song + '"' + " didn't return any songs."
            print(error)
            return error
    
    if type(result['tracks']) == dict:
        playable = result['tracks']['items'][0]['is_playable']
    else:
        playable = result['tracks'][0]['is_playable']
    if playable != True:
        error = "Error: Sorry, that song isn't playable in the streamer's country and Spotify can't find any available versions that are."
        print(error)
        return error
    
    song = result['tracks']['items'][0]['uri'] if type(result['tracks']) == dict else result['tracks'][0]['uri']
    return song


async def songRequest(discordGuild, song):
    if not credentials.get(str(discordGuild)):
        # message the channel aboud da eror
        error = "Error: strimmer hasn't authorized MAX to control Spotify yet. This must be done through the 'spotify' command in discord."
        print(error)
        await MAXTwitch.messageLinkedTwitchChannel(discordGuild, error)
        return

    spotify = spotipy.Spotify(auth_manager=credentials[str(discordGuild)])

    # parse the input message, see if its valid and playable
    song = await findSong(spotify, song)
    if song.startswith('Error:'):
        # message the channel aboud da eror
        await MAXTwitch.messageLinkedTwitchChannel(discordGuild, song)
        return
    
    # if there are songs in the requests already then just add the request to the queue because we've already started monitoring it
    if requestedSongs.get(str(discordGuild)):
        spotify.add_to_queue(song)
        if oldSongs.get(str(discordGuild)):
            spotify.add_to_queue(oldSongs.get(str(discordGuild)))
        msg = "Song requested! There are " + str(len(requestedSongs[str(discordGuild)])) + " requests in the queue before yours."
        requestedSongs[str(discordGuild)].append(song)
        print(msg)
        await MAXTwitch.messageLinkedTwitchChannel(discordGuild, msg)
        return

    oldState = spotify.current_playback()
    checkOldTrack = True
    oldTrack = None
    oldContext = None
    deviceID = None
    if oldState:
        # get the current "is playing" state
        oldPlaying = oldState['is_playing']
        # get the old repeat state
        oldRepeat = oldState['repeat_state']
        # get the current context
        if oldState['context']:
            oldContext = oldState['context']['uri']
        # get the current track
        oldTrack = oldState['item']['uri']
        # if someone requested another copy of the song that's already playing
        if oldTrack == song:
            checkOldTrack = False
        # get the distance into the song (position_ms)
        oldProgress = oldState['progress_ms']
    else:
        deviceID = spotify.devices()
        if not deviceID['devices']:
            error = "Error: strimmer does not have any available Spotify devices to play on. Strimmer must have Spotify open and have recently played a song somewhere to play requests."
            print(error)
            await MAXTwitch.messageLinkedTwitchChannel(discordGuild, error)
            return
        else:
            activeDevice = None
            for device in deviceID['devices']:
                if device['is_active'] == True:
                    activeDevice = device['id']
                    break
            if not activeDevice:
                activeDevice = deviceID['devices'][0]['id']
            deviceID = deviceID['devices'][0]['id']

    try:
        spotify.add_to_queue(uri=generalConfig.get(query.name == 'spotifyTransitionSong')['value'], device_id=deviceID)
    except spotipy.exceptions.SpotifyException:
        if deviceID:
            error = "Error: strimmer does not have any available Spotify devices to play on. Strimmer must have Spotify open and have recently played a song somewhere to play requests."
            print(error)
            await MAXTwitch.messageLinkedTwitchChannel(discordGuild, error)
        else:
            error = "Error: The requested song couldn't be added to the queue."
            print(error)
            await MAXTwitch.messageLinkedTwitchChannel(discordGuild, error)
        return
    spotify.add_to_queue(uri=song, device_id=deviceID)
    requestedSongs[str(discordGuild)] = [generalConfig.get(query.name == 'spotifyTransitionSong')['value']]
    requestedSongs[str(discordGuild)].append(song)
    if oldState:
        spotify.add_to_queue(uri=oldTrack)
        if checkOldTrack:
            oldSongs[str(discordGuild)] = oldTrack
        else:
            oldTrack = None

    spotify.repeat(state='off', device_id=deviceID)
    spotify.next_track(device_id=deviceID)

    msg = "Song requested!"
    print(msg)
    await MAXTwitch.messageLinkedTwitchChannel(discordGuild, msg)

    try:
        # check every second to see if playlist context has changed, or if the song being played is not in the list of requested song
        while True:
            await asyncio.sleep(1)
            state = spotify.current_playback()
            currentContext = None
            if state['context']:
                currentContext = state['context']['uri']
            # if the strimmer began playing a song later on that isn't any of the requested songs or the original song, or the strimmer began playing a different context
            if (state['item']['uri'] not in requestedSongs[str(discordGuild)] and state['item']['uri'] != oldTrack) or (oldContext and currentContext != oldContext):
                print("Song playing is not in requests and not original song, or context has changed from old context.")
                if oldState:
                    spotify.repeat(state=oldRepeat)
                else:
                    spotify.pause_playback()
                requestedSongs.pop(str(discordGuild), None)
                oldSongs.pop(str(discordGuild), None)
                break
            # if the player is playing the original song and there is 1 or fewer requests in the list (so, for example, the last requested song has just finished), reset
            elif state['item']['uri'] == oldTrack and len(requestedSongs[str(discordGuild)]) <= 1:
                print("Original song playing, but only 1 song in requests, so we have finished the queue.")
                if oldState:
                    if not oldPlaying:
                        spotify.pause_playback()
                    spotify.repeat(state=oldRepeat)
                    spotify.seek_track(position_ms=oldProgress)
                    requestedSongs.pop(str(discordGuild), None)
                    oldSongs.pop(str(discordGuild), None)
                    break
                else:
                    requestedSongs.pop(str(discordGuild), None)
                    oldSongs.pop(str(discordGuild), None)
                    break
            # if the player is playing the original song and there ARE requests left in the list, skip it
            elif state['item']['uri'] == oldTrack and requestedSongs[str(discordGuild)]:
                print("Original song playing, but 2 or more songs remain, so skipping and removing top of requests.")
                requestedSongs[str(discordGuild)].pop(0)
                spotify.next_track()
            # if the player is not playing the original song but the context hasnt changed and the song is in the requested list
            else:
                removableIndexes = []
                # clear every song that is in the list before this one
                for index, entry in enumerate(requestedSongs[str(discordGuild)]):
                    if state['item']['uri'] != entry:
                        removableIndexes.append(index)
                    else:
                        break
                # delete indexes in reverse so that we don't throw off the index count
                for index in sorted(removableIndexes, reverse=True):
                    del requestedSongs[str(discordGuild)][index]
    except Exception as error:
        err = 'Error: There was an error while monitoring requests: ' + repr(error)
        print(err)
        await MAXTwitch.messageLinkedTwitchChannel(discordGuild, err)
        requestedSongs.pop(str(discordGuild), None)
        oldSongs.pop(str(discordGuild), None)
    msg = "All requests have finished playing."
    print(msg)
    await MAXTwitch.messageLinkedTwitchChannel(discordGuild, msg)

async def spotifyPrepareAllConnections():
    authConfig = auth.get(query.name == 'spotify')
    for entry in config.all():
        if entry.get('spotifyUserID'):
            credentialManager = spotipy.oauth2.SpotifyOAuth(client_id=authConfig['clientID'], client_secret=authConfig['clientSecret'], redirect_uri=generalConfig.get(query.name == 'callback')['value']+'spotify/callback', state=entry['discordGuild'], cache_path=configPath+'MAXSpotifyTokenCache/'+str(entry['discordGuild']))
            credentials[str(entry['discordGuild'])] = credentialManager
    
    # start the twitch webserver, which listens to a topic for each stored user
    loop = asyncio.get_event_loop()
    loop.create_task(MAXServer.twitchWS())

async def createClient(discordGuild, code):
    authConfig = auth.get(query.name == 'spotify')
    credentialManager = spotipy.oauth2.SpotifyOAuth(client_id=authConfig['clientID'], client_secret=authConfig['clientSecret'], redirect_uri=generalConfig.get(query.name == 'callback')['value']+'spotify/callback', state=discordGuild, cache_path=configPath+'MAXSpotifyTokenCache/'+str(discordGuild))
    credentialManager.get_access_token(code=code)
    # get and store user id
    spotify = spotipy.Spotify(auth_manager=credentialManager)
    userInfo = spotify.me()
    config.update({'spotifyUserID': userInfo['id']}, query.discordGuild == discordGuild)
    credentials[str(discordGuild)] = credentialManager  # use like so: spotipy.Spotify(auth_manager=credentials[str(discordGuild)])
    print('Successfully created config and playlist for Spotify user ' + userInfo['id'] + ' from guild ' + str(discordGuild))

async def getPlaying(discordGuild):
    spotify = spotipy.Spotify(auth_manager=credentials[discordGuild])
    playback = spotify.current_playback()
    print(playback)