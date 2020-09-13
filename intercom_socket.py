import sys
import pyaudio
import socket
import select
import math
import requests
import struct
import numpy as np
from os import system, environ
from time import sleep

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 4096
SHORT_NORMALIZE = (1.0/32768.0)
INTERCOM_THRESHOLD = 0.16 #TODO verify


SLACK_WEBHOOK = environ['SLACK_WEB_HOOK']
TELEGRAM_BOT_TOKEN = environ['TELEGRAM_INTERCOM_TOKEN']

audio = pyaudio.PyAudio()

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serversocket.bind(('', 4444))
serversocket.listen(5)

def telegram_message(message='test'):
    r = requests.get('https://api.telegram.org/bot{0}/sendMessage?chat_id=-1001460035878&text={1}'.format(TELEGRAM_BOT_TOKEN, message))
    print("Message sent to telegram, status -> " + r.text)


def slack_message(message='test'):
    system("curl -X POST -H 'Content-type: application/json' --data '{{\"text\":\"{0}\"}}' {1}".format(message, SLACK_WEBHOOK))
    print("Message sent to slack!")


def notification_manager(message):
    notifications_to = [x.lower() for x in sys.argv[1:]]
    for notification_to in notifications_to:
        if "slack" in notification_to:
            slack_message(message)
        if "tele" in notification_to:
            telegram_message(message)


def get_rms( block ):
    count = len(block)/2
    format = "%dh"%(count)
    shorts = struct.unpack( format, block )

    # iterate over the block.
    sum_squares = 0.0
    for sample in shorts:
        # sample is a signed short in +/- 32768. 
        # normalize it to 1.0
        n = sample * SHORT_NORMALIZE
        sum_squares += n*n

    return math.sqrt( sum_squares / count )


def callback(in_data, frame_count, time_info, status):
    for s in read_list[1:]:
        amplitude = get_rms( in_data )
        if amplitude >= INTERCOM_THRESHOLD:
            print("amplitude -> ", str(amplitude))
            notification_manager('CORRI CITOFONO!!!')
            sleep(5)
        try:
            s.send(in_data)
        except:
            pass

    return (None, pyaudio.paContinue)

stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK, stream_callback=callback)

read_list = [serversocket]
print("recording...")

try:
    while True:
        readable, writable, errored = select.select(read_list, [], [])
        for s in readable:
            if s is serversocket:
                (clientsocket, address) = serversocket.accept()
                read_list.append(clientsocket)
                print("Connection from ", address)
            else:
                try:
                    data = s.recv(1024)
                except:
                    read_list.remove(s)
except KeyboardInterrupt:
    pass

print("finished recording")

serversocket.close()
stream.stop_stream()
stream.close()
audio.terminate()
