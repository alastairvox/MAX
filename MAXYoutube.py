import asyncio, datetime, dateutil.parser
import aiohttp
import MAXShared, MAXDiscord, MAXTwitch, MAXServer
from MAXShared import query, devFlag, auth, generalConfig, youtubeConfig, discordConfig, twitchConfig, dayNames, fullDayNames

# overloads print for this module so that all prints (hopefully all the sub functions that get called too) are appended with which service the prints came from
print = MAXShared.printName(print, "YOUTUBE:")



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
config = youtubeConfig



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



async def subscribeYoutubeUploads(discordGuild, channel):
    async with MAXServer.session.post('https://pubsubhubbub.appspot.com/subscribe?hub.callback=' + generalConfig.get(query.name == 'callback')['value'] + 'youtube/' + str(discordGuild) + '&hub.topic=https://www.youtube.com/xml/feeds/videos.xml?channel_id=' + channel + '&hub.verify=async&hub.mode=subscribe') as resp:
        print('Subscription request to youtube channel ' + channel + ' for guild ' + str(discordGuild) + ' completed with status ' + str(resp.status))
        return resp.status

async def getAllYoutubeUploads(channel):
    token = auth.get(query.name == 'youtube')['token']
    params = {'part': 'contentDetails', 'id': channel, 'key': token}
    async with MAXServer.session.get('https://www.googleapis.com/youtube/v3/channels', params=params) as resp:
        print('Beginning requests to collect all youtube videos for ' + channel + '. Requested upload playlist id, received status: ' + str(resp.status))
        if resp.status != 200:
            return resp.status
        else:
            data = await resp.json()
            data = data.get('items')
            if not data:
                print('Error - No items in response - channel likely doesnt exist.')
                return "channel likely doesnt exist"
            uploadPlaylist = data[0]['contentDetails']['relatedPlaylists'].get('uploads')
            if not uploadPlaylist:
                print('Error - Channel does not have an uploads playlist?')
                return "channel has no uploads playlist"
            else:
                # now we get playlist items/videos, loop until we don't have anymore pages
                params = {'part': 'contentDetails', 'maxResults': 50, 'playlistId': uploadPlaylist, 'key': token}
                async with MAXServer.session.get('https://www.googleapis.com/youtube/v3/playlistItems', params=params) as resp:
                    if resp.status != 200:
                        return resp.status
                    else:
                        data = await resp.json()
                        videoList = []
                        nextPage = data.get('nextPageToken')
                        for video in data['items']:
                            videoList.append(video['contentDetails']['videoId'])
                        while nextPage:
                            params = {'part': 'contentDetails', 'maxResults': 50, 'pageToken': nextPage, 'playlistId': uploadPlaylist, 'key': token}
                            async with MAXServer.session.get('https://www.googleapis.com/youtube/v3/playlistItems', params=params) as resp:
                                if resp.status != 200:
                                    return resp.status
                                else:
                                    data = await resp.json()
                                    nextPage = data.get('nextPageToken')
                                    for video in data['items']:
                                        videoList.append(video['contentDetails']['videoId'])
                        config.update({'announcedVideos': videoList}, query.channelID == channel)
                        print('Finished requests for', channel, 'videos. Inserted', len(videoList), 'videos into config.')
                        return resp.status

async def youtubeWaitForResub(seconds, discordGuild, youtubeChannel):
    print('waiting', seconds, 'seconds to resub to', youtubeChannel)
    await asyncio.sleep(seconds)
    await subscribeYoutubeUploads(discordGuild, youtubeChannel)

async def youtubePrepareAllResubs():
    loop = asyncio.get_event_loop()
    for entry in config.all():
        leaseSeconds = entry.get('leaseSeconds')
        timeAdded = entry.get('time')
        if leaseSeconds and timeAdded:
            leaseSecondsDelta = datetime.timedelta(seconds=leaseSeconds)
            timeAdded = dateutil.parser.parse(timeAdded)
            timeNow = datetime.datetime.now()
            timeDifference = timeNow - timeAdded
            if timeDifference >= leaseSecondsDelta:
                # resub immediately
                loop.create_task(subscribeYoutubeUploads(entry.get('discordGuild'), entry.get('channelID')))
            else:
                timeDifference = leaseSecondsDelta - timeDifference
                loop.create_task(youtubeWaitForResub(timeDifference.total_seconds(), entry.get('discordGuild'), entry.get('channelID')))