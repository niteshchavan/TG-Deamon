#!/nitesh/telegram-download-daemon/telegrambot/bin python3
# Telegram Download Daemon
# Author: Alfonso E.M. <alfonso@el-magnifico.org>
# You need to install telethon (and cryptg to speed up downloads)

from os import path
from shutil import move
import subprocess
import math
import time
import random
import string
import multiprocessing
import asyncio

from sessionManager import getSession, saveSession

from telethon import TelegramClient, events
from telethon.tl.types import PeerChannel, DocumentAttributeFilename, DocumentAttributeVideo
import logging

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s]%(name)s:%(message)s',
                    level=logging.WARNING)

TDD_VERSION = "1.5"

TELEGRAM_DAEMON_TEMP_SUFFIX = "tdd"

api_id = 1234567 #your api id
api_hash = 'abcd1234545...' #your api hash
channel_id = 123567890 #your channel id
downloadFolder = '/nitesh/media/movies/'
tempFolder = '/tmp/'
audio_folder = '/nitesh/media/audio/%\(title\)s.%\(ext\)s'
video_folder = '/nitesh/media/video/%\(title\)s.%\(ext\)s'
ls_audio = 'ls /nitesh/media/audio/'
ls_video = 'ls /nitesh/media/video/'
ls_movies = 'ls /nitesh/media/movies/'

worker_count = multiprocessing.cpu_count()
updateFrequency = 10
lastUpdate = 0
# multiprocessing.Value('f', 0)

if not tempFolder:
    tempFolder = downloadFolder

# Edit these lines:
proxy = None


# End of interesting parameters

async def sendHelloMessage(client, peerChannel):
    entity = await client.get_entity(peerChannel)
    print("Telegram Download Daemon " + TDD_VERSION)
    await client.send_message(entity, "Telegram Download Daemon " + TDD_VERSION)
    await client.send_message(entity, "Hi! Ready for your files!")


async def log_reply(message, reply):
    print(reply)
    await message.edit(reply)


def getRandomId(len):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for x in range(len))


def getFilename(event: events.NewMessage.Event):
    mediaFileName = "unknown"
    for attribute in event.media.document.attributes:
        if isinstance(attribute, DocumentAttributeFilename):
            mediaFileName = attribute.file_name
            break
        if isinstance(attribute, DocumentAttributeVideo): mediaFileName = event.original_update.message.message

    if path.exists("{0}/{1}.{2}".format(tempFolder, mediaFileName, TELEGRAM_DAEMON_TEMP_SUFFIX)) or path.exists(
            "{0}/{1}".format(downloadFolder, mediaFileName)):
        mediaFileName = mediaFileName + "." + getRandomId(8)
    return mediaFileName

in_progress = {}

async def set_progress(filename, message, received, total):
    global lastUpdate
    global updateFrequency

    if received >= total:
        try:
            in_progress.pop(filename)
        except:
            pass
        return
    percentage = math.trunc(received / total * 10000) / 100

    progress_message = "{0} % ({1} / {2})".format(percentage, received, total)
    in_progress[filename] = progress_message

    currentTime = time.time()
    if (currentTime - lastUpdate) > updateFrequency:
        await log_reply(message, progress_message)
        lastUpdate = currentTime

with TelegramClient(getSession(), api_id, api_hash,
                    proxy=proxy).start() as client:
    saveSession(client.session)

    queue = asyncio.Queue()
    peerChannel = PeerChannel(channel_id)

    @client.on(events.NewMessage())
    async def handler(event):
        if event.to_id != peerChannel:
            return

        print(event)

        try:

            if not event.media and event.message:
                command = event.message.message
                command = command.lower()
                output = event.message.message + "\n\n"
                if command == "audio":
                    file1 = open('link.txt', 'r')
                    url = file1.read()
                    print(f"Audio: {url}")
                    await client.send_message(channel_id, 'Downloading Audio...')
                    process = subprocess.run([f"youtube-dl -f 140 {url} -o {audio_folder}"], shell=True,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
                    out = process.stdout.decode("utf-8")
                    error = process.stderr.decode("utf-8")
                    print(f"Audio Output: \n{out}\n{error}")
                    file1.close()
                    await client.send_message(channel_id, f"Audio Downloaded:\n{error}")
                elif command == "video":
                    file1 = open('link.txt', 'r')
                    url = file1.read()
                    print(f"Video: {url}")
                    await client.send_message(channel_id, 'Downloading Video')
                    process = subprocess.run([f"youtube-dl -f 18 {url} -o {video_folder}"], shell=True,
                                             stdout=subprocess.PIPE,
                                             stderr=subprocess.PIPE)
                    out = process.stdout.decode("utf-8")
                    error = process.stderr.decode("utf-8")
                    print(f"Video Output: \n{out}\n{error}")
                    file1.close()
                    await client.send_message(channel_id, f"Video Downloaded:\n{error}")
                elif command == "ls":
                    process = subprocess.run([ls_audio], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out1 = process.stdout.decode("utf-8")
                    #        error1 = process.stderr.decode("utf-8")
                    process = subprocess.run([ls_video], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out2 = process.stdout.decode("utf-8")
                    process = subprocess.run([ls_movies], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out3 = process.stdout.decode("utf-8")
                    await client.send_message(channel_id, f"Audio:\n{out1} \nVideo:\n{out2} \nMovies:\n{out3}")

                elif command == "mv":
                    process = subprocess.run(["mv /nitesh/media/audio/* /nitesh/media/mount/audio/"], shell=True,
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out1 = process.stdout.decode("utf-8")
                    error1 = process.stderr.decode("utf-8")
                    process = subprocess.run(["mv /nitesh/media/video/* /nitesh/media/mount/video/"], shell=True,
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out2 = process.stdout.decode("utf-8")
                    error2 = process.stderr.decode("utf-8")
                    process = subprocess.run(["mv /nitesh/media/movies/* /nitesh/media/mount/movies/"], shell=True,
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out3 = process.stdout.decode("utf-8")
                    error3 = process.stderr.decode("utf-8")
                    await client.send_message(channel_id, f"Audio:\n{error1} \nVideo:\n{error2} \nMovies:\n{error3}")

                elif command == "rm audio":
                    process = subprocess.run(["rm /nitesh/media/audio/*"], shell=True,
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out1 = process.stdout.decode("utf-8")
                    error1 = process.stderr.decode("utf-8")
                    await client.send_message(channel_id, f"Audio:\n{error1}")
                elif command == "rm video":
                    process = subprocess.run(["rm /nitesh/media/video/*"], shell=True,
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out2 = process.stdout.decode("utf-8")
                    error2 = process.stderr.decode("utf-8")
                    await client.send_message(channel_id, f"Video:\n{error2}")
                elif command == "rm movies":
                    process = subprocess.run(["rm /nitesh/media/movies/*"], shell=True,
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out3 = process.stdout.decode("utf-8")
                    error3 = process.stderr.decode("utf-8")
                    await client.send_message(channel_id, f"Movies:\n{error3}")

                elif command == "status":
                    try:
                        output = "".join(["{0}: {1}\n".format(key, value) for (key, value) in in_progress.items()])
                        if output:
                            output = "Active downloads:\n\n" + output
                        else:
                            output = "No active downloads"
                    except:
                        output = "Some error occured while checking the status. Retry."
                elif command == "clean":
                    output = "Cleaning " + tempFolder + "\n"
                    output += subprocess.run(["rm " + tempFolder + "/*." + TELEGRAM_DAEMON_TEMP_SUFFIX], shell=True,
                                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout
                else:
                    output = "Available commands:\n ls\n mv\n status\n clean\n rm\n "

                await log_reply(event, output)

            if event.media:
                filename = getFilename(event)
                message = await event.reply("{0} added to queue".format(filename))
                await queue.put([event, message])
        except:
            if event.message.media.webpage.url != None:
                print("link recived writing to link.txt")
                file1 = open('link.txt', 'w')
                link = event.message.media.webpage.url
                file1.write(link)
                file1.close()
                await client.send_message(channel_id, 'Link Captured')

#        except Exception as e:
#            print('Events handler error: ', e)

    async def worker():
        while True:
            try:
                element = await queue.get()
                event = element[0]
                message = element[1]

                filename = getFilename(event)

                await log_reply(
                    message,
                    "Downloading file {0} ({1} bytes)".format(filename, event.media.document.size)
                )

                download_callback = lambda received, total: set_progress(filename, message, received, total)

                await client.download_media(event.message,
                                            "{0}/{1}.{2}".format(tempFolder, filename, TELEGRAM_DAEMON_TEMP_SUFFIX),
                                            progress_callback=download_callback)
                await set_progress(filename, message, 100, 100)
                move("{0}/{1}.{2}".format(tempFolder, filename, TELEGRAM_DAEMON_TEMP_SUFFIX),
                     "{0}/{1}".format(downloadFolder, filename))
                await log_reply(message, "{0} ready".format(filename))

                queue.task_done()
            except Exception as e:
                print('Queue worker error: ', e)

    async def start():

        tasks = []
        loop = asyncio.get_event_loop()
        for i in range(worker_count):
            task = loop.create_task(worker())
            tasks.append(task)
        await sendHelloMessage(client, peerChannel)
        await client.run_until_disconnected()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    client.loop.run_until_complete(start())
