
#!/usr/bin/env python3
# Telegram Download Daemon
# Author: Alfonso E.M. <alfonso@el-magnifico.org>
# You need to install telethon (and cryptg to speed up downloads)

from os import getenv, path
from shutil import move
import subprocess
import math
import time
import random
import string
import os.path
import re
from mimetypes import guess_extension
from subprocess import run, PIPE, Popen

from sessionManager import getSession, saveSession

from telethon import TelegramClient, events, Button
from telethon.tl.types import PeerChannel, DocumentAttributeFilename, DocumentAttributeVideo
import logging

import multiprocessing
import asyncio


logging.basicConfig(format='[%(levelname) 5s/%(asctime)s]%(name)s:%(message)s',
                    level=logging.WARNING)


TDD_VERSION="1.12"

TELEGRAM_DAEMON_SESSION_PATH = getenv("TELEGRAM_DAEMON_SESSION_PATH")
TELEGRAM_DAEMON_TEMP_SUFFIX="tdd"

api_id = 12345678
api_hash = ''
channel_id = 123456789
downloadFolder = '/nitesh/media/movies/'
tempFolder = '/nitesh/media/movies/'
duplicates= 'ignore'
token = 'abcde:dsfjsdflsdkjf'
audio_folder = '/nitesh/media/audio/%\(title\)s.%\(ext\)s'
video_folder = '/nitesh/media/video/%\(title\)s.%\(ext\)s'
folder = '/nitesh/media/video'


worker_count = multiprocessing.cpu_count()
updateFrequency = 10
lastUpdate = 0
#multiprocessing.Value('f', 0)

if not tempFolder:
    tempFolder = downloadFolder

# Edit these lines:
proxy = None

# End of interesting parameters

async def sendHelloMessage(client, peerChannel):
    entity = await client.get_entity(peerChannel)
    print("Telegram Download Daemon "+TDD_VERSION)
    await client.send_message(entity, "Telegram Download Daemon "+TDD_VERSION)
    await client.send_message(entity, "Hi! Ready for your files!")
 

async def log_reply(message, reply):
    print(reply)
    await message.edit(reply)

def getRandomId(len):
    chars=string.ascii_lowercase + string.digits
    return  ''.join(random.choice(chars) for x in range(len))
 
def getFilename(event: events.NewMessage.Event):
    mediaFileName = "unknown"

    if hasattr(event.media, 'photo'):
        mediaFileName = str(event.media.photo.id)+".jpeg"
    elif hasattr(event.media, 'document'):
        for attribute in event.media.document.attributes:
            if isinstance(attribute, DocumentAttributeFilename): 
              mediaFileName=attribute.file_name
              break     
            if isinstance(attribute, DocumentAttributeVideo):
              if event.original_update.message.message != '': 
                  mediaFileName = event.original_update.message.message
              else:    
                  mediaFileName = str(event.message.media.document.id)
              mediaFileName+=guess_extension(event.message.media.document.mime_type)    
     
    mediaFileName="".join(c for c in mediaFileName if c.isalnum() or c in "()._- ")
      
    return mediaFileName


in_progress={}

async def set_progress(filename, message, received, total):
    global lastUpdate
    global updateFrequency

    if received >= total:
        try: in_progress.pop(filename)
        except: pass
        return
    percentage = math.trunc(received / total * 10000) / 100

    progress_message= "{0} % ({1} / {2})".format(percentage, received, total)
    in_progress[filename] = progress_message

    currentTime=time.time()
    if (currentTime - lastUpdate) > updateFrequency:
        await log_reply(message, progress_message)
        lastUpdate=currentTime


with TelegramClient(getSession(), api_id, api_hash,
                    proxy=proxy).start(bot_token=token) as client:

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
                output = "Unknown command"

                if command == "list":
                    output = subprocess.run(["ls -l "+downloadFolder], shell=True, stdout=subprocess.PIPE,stderr=subprocess.STDOUT).stdout.decode('utf-8')
                elif command == "status":
                    try:
                        output = "".join([ "{0}: {1}\n".format(key,value) for (key, value) in in_progress.items()])
                        if output:
                            output = "Active downloads:\n\n" + output
                        else:
                            output = "No active downloads"
                    except:
                        output = "Some error occured while checking the status. Retry."
                elif command == "clean":
                    output = "Cleaning "+tempFolder+"\n"
                    output+=subprocess.run(["rm "+tempFolder+"/*."+TELEGRAM_DAEMON_TEMP_SUFFIX], shell=True, stdout=subprocess.PIPE,stderr=subprocess.STDOUT).stdout
                else:
                    output = "Available commands: list, status, clean"

                await log_reply(event, output)


            if event.media:
                if hasattr(event.media, 'document') or hasattr(event.media,'photo'):
                    filename=getFilename(event)
                    if ( path.exists("{0}/{1}.{2}".format(tempFolder,filename,TELEGRAM_DAEMON_TEMP_SUFFIX)) or path.exists("{0}/{1}".format(downloadFolder,filename)) ) and duplicates == "ignore":
                        message=await event.reply("{0} already exists. Ignoring it.".format(filename))
                    else:
                        message=await event.reply("{0} added to queue".format(filename))
                        await queue.put([event, message])
                else:
                    if event.message.message:
                        link = event.message.message
                        message = re.search("(?P<url>https?://[^\s]+)", link)
                        if message is not None:
                            geturl = re.search("(?P<url>https?://[^\s]+)", link).group('url')
                            file = open('link.txt', 'w')
                            file.write(geturl)
                            file.close()
                            keyboard = [
                                [
                                    Button.inline("Play", b"1"),
                                    Button.inline("Stop", b"2"),
                                    Button.inline("Play Music", b"0")
                                ],
                                [
                                    Button.inline("Volume Up", b"3"),
                                    Button.inline("Volume Down", b"4"),
                                    Button.inline("Puase", b"12")
                                ],
                                [
                                    Button.inline("Save Audio", b"5"),
                                    Button.inline("Save Video", b"6")
                                ],
                                [
                                    Button.inline("Start Kodi", b"7"),
                                    Button.inline("Stop Kodi", b"8")
                                ],
                                [
                                    Button.inline("Aria2c Download", b"9")
                                ]
                            ]
                            await event.respond("Link received", buttons=keyboard)

        #                    message=await event.reply("That is not downloadable. Try to send it as a file.")

        except Exception as e:
                print('Events handler error: ', e)

    async def worker():
        while True:
            try:
                element = await queue.get()
                event=element[0]
                message=element[1]

                filename=getFilename(event)
                fileName, fileExtension = os.path.splitext(filename)
                tempfilename=fileName+"-"+getRandomId(8)+fileExtension

                if path.exists("{0}/{1}.{2}".format(tempFolder,tempfilename,TELEGRAM_DAEMON_TEMP_SUFFIX)) or path.exists("{0}/{1}".format(downloadFolder,filename)):
                    if duplicates == "rename":
                       filename=tempfilename

 
                if hasattr(event.media, 'photo'):
                   size = 0
                else: 
                   size=event.media.document.size

                await log_reply(
                    message,
                    "Downloading file {0} ({1} bytes)".format(filename,size)
                )

                download_callback = lambda received, total: set_progress(filename, message, received, total)

                await client.download_media(event.message, "{0}/{1}.{2}".format(tempFolder,filename,TELEGRAM_DAEMON_TEMP_SUFFIX), progress_callback = download_callback)
                set_progress(filename, message, 100, 100)
                move("{0}/{1}.{2}".format(tempFolder,filename,TELEGRAM_DAEMON_TEMP_SUFFIX), "{0}/{1}".format(downloadFolder,filename))
                await log_reply(message, "{0} ready".format(filename))

                queue.task_done()
            except Exception as e:
                try: await log_reply(message, "Error: {}".format(str(e))) # If it failed, inform the user about it.
                except: pass
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

    @client.on(events.CallbackQuery)
    async def handler(event):
        print(event.data)
        if event.data == b'1':
            file = open('link.txt', 'r')
            url = file.read()
            mplayer_process = subprocess.Popen([f"mpv --vo=gpu --gpu-context=drm --drm-connector=1.HDMI-A-1 -cookies -cookies-file /tmp/cookie.txt "
                                                f"$(youtube-dl -q -f best -g --cookies /tmp/cookie.txt {url})"],
                                               shell=True)
            file.close()
            await event.answer()

        elif event.data == b'0':
            file = open('link.txt', 'r')
            url = file.read()
            mplayer_process = subprocess.Popen([f"mpv -cookies -cookies-file /tmp/cookie.txt "
                                                f"$(youtube-dl -q -f bestaudio -g --cookies /tmp/cookie.txt {url})"],
                                               shell=True)
            file.close()
            await event.answer()

        elif event.data == b'12':
            process = subprocess.run([f"mpv -p"], shell=True)
            await event.answer()

        elif event.data == b'2':
            process = subprocess.run([f"kill $(ps -aux | pgrep mpv)"], shell=True)
            await event.answer()

        elif event.data == b'3':
            process = subprocess.run("amixer -q sset Speaker 10%+ && amixer sget Speaker | grep 'Front Right:' "
                                     "| awk -F'[][]' '{print $2}'", shell=True, stdout=subprocess.PIPE)
            await event.answer()

        elif event.data == b'4':
            process = subprocess.run("amixer -q sset Speaker 10%- && amixer sget Speaker | grep 'Front Right:' "
                                     "| awk -F'[][]' '{print $2}'", shell=True, stdout=subprocess.PIPE)
            await event.answer()

        elif event.data == b'5':
            file = open('link.txt', 'r')
            url = file.read()
            process = subprocess.run([f"youtube-dl -f 140 {url} -o {audio_folder}"], shell=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            error = process.stderr.decode("utf-8")
            file.close()
            await client.send_message(channel_id, f"Audio Downloaded:\n{error}")
            await event.answer()

        elif event.data == b'6':
            file = open('link.txt', 'r')
            url = file.read()
            process = subprocess.run([f"youtube-dl -f best {url} -o {video_folder}"], shell=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            error = process.stderr.decode("utf-8")
            file.close()
            await client.send_message(channel_id, f"Video Downloaded:\n{error}")
            await event.answer()

        elif event.data == b'7':
            process = subprocess.run(["systemctl start kodi"], shell=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            await client.send_message(channel_id, "Kodi Started")
            await event.answer()
        elif event.data == b'8':
            process = subprocess.run(["systemctl stop kodi"], shell=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            await client.send_message(channel_id, "Kodi Stoped")
            await event.answer()
        elif event.data == b'9':
            file = open('link.txt', 'r')
            url = file.read()
            process = subprocess.run([f"aria2c -d {downloadFolder} {url}"], shell=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output = process.stdout.decode("utf-8")
            file.close()
            await client.send_message(channel_id, f"File Downloaded:\n{output}")
            await event.answer()
#            while True:
#                output = process.stdout.decode("utf-8")
#                if output:
#                    file.close()
#                    await client.send_message(channel_id, f"File Downloaded:\n{output}")
#                    await event.answer()

    client.loop.run_until_complete(start())
