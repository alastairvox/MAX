import asyncio, io, sys
import MAXShared
import MAXDiscord, MAXTwitch, MAXServer

# forces the stdout to flush constantly so that nssm can actually keep the logfile updated (nothing will show until after close, lost on crash otherwise)
# does this by reopening the stdout as a writable binary with no buffering then wraps it in an io text wrapper?? and overwrites the default stdout
sys.stdout = io.TextIOWrapper(open(sys.stdout.fileno(), 'wb', 0), write_through=True, errors="namereplace")

# overloads print for this module so that all prints (hopefully all the sub functions that get called too) are appended with which service the prints came from
print = MAXShared.printName(print, "MAIN:") 

async def testFunction():
    await MAXDiscord.bot.wait_until_ready()
    try:
        await MAXDiscord.say(ctx='DrawnActor', channel='general', notifyRole='none', message="Hello")
    except Exception as exception:
        print('Error: ' + repr(exception))
    await asyncio.sleep(5)
    await testFunction()

def main():
    print("MAX is alive again.")

    # gets the current event loop or i guess creates one (there can only ever be one running event loop)
    loop = asyncio.get_event_loop()
    # schedules a task to run on the event loop next time the event loop checks for stuff, unless the event loop got closed!! (which is why we run forever, otherwise it wont even start them)
    loop.create_task(MAXDiscord.engage())
    loop.create_task(MAXTwitch.engage())
    loop.create_task(MAXServer.engage())
    # makes the event loop run forever (this is blocking), so any current and future scheduled tasks will run until we explicitly tell the loop to die with loop.stop()
    loop.run_forever()

if __name__ == '__main__':
    main()