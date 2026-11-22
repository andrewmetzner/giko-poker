#!/usr/bin/env python3
"""Akai's bot: a Gikopoi poker bot for ◆wizardTREQ wizards, paying in Wizcoins.

Run with:  ./giko.py [room]
Type in the console to chat as the bot; start a line with , to walk
(e.g. ",uulr" moves up, up, left, right).
"""

import datetime
import os
import sys
import threading
import time

import requests
import socketio

from plugin import help as help_plugin
from plugin import poker
from plugin import wizcoins

SERVER = "play.gikopoi.com"
AREA = "for"
ROOM = "bar"
CHARACTER = "naito_npc"
BOT_NAME = "Akai's bot"
PASSWORD = "npc"
ANON_NAME = "Spy"
# Optional: put a secret on the first line of tripcode.txt to give the
# bot its own tripcode.
TRIPCODE_FILE = "tripcode.txt"

PLUGINS = [poker, wizcoins, help_plugin]

sio = socketio.Client()
session = requests.Session()
reply_lock = threading.Lock()

Users = {}
my_id = ""
pid = ""
api = ""


def login_name():
    if os.path.exists(TRIPCODE_FILE):
        with open(TRIPCODE_FILE, encoding="utf-8") as f:
            lines = f.read().splitlines()
        if lines and lines[0].strip():
            return BOT_NAME + "#" + lines[0].strip()
    return BOT_NAME


def main():
    global api
    room = sys.argv[1] if len(sys.argv) > 1 else ROOM

    if "poipoi" in SERVER:
        api = "/api"

    if not logon(SERVER, AREA, room, CHARACTER, login_name(), PASSWORD):
        sys.exit(1)

    print(list(Users.values()))

    while True:
        val = input()
        if val.startswith(","):
            move_around(val[1:])
        else:
            sio.emit("user-msg", val)


def logon(server, area, room, character, name, password):
    global my_id
    global pid

    url = "https://" + server
    wss = "ws://" + server + ":8085/socket.io/"
    print("[+] Connect")
    connect_value = {"userName": name,
                     "characterId": character,
                     "areaId": area,
                     "roomId": room,
                     "password": password}
    connect_response = session.post(f"{url}{api}/login", connect_value)
    connect_json = connect_response.json()
    if connect_json.get("isLoginSuccessful") is not True:
        print("Not able to login")
        return False

    print("[+] Connected")
    user_id = str(connect_json["userId"])
    pid = str(connect_json["privateUserId"])
    version = str(connect_json["appVersion"])

    t_form = "%a %b %d %Y %H:%M:%S %Z (%z)"
    timestamp = datetime.datetime.now().strftime(t_form)
    send = " ".join([timestamp, user_id,
                     "window.EXPECTED_SERVER_VERSION:", version,
                     "loginMessage.appVersion:", version,
                     "DIFFERENT: false"])
    session.post(f"{url}/client-log",
                 data=send,
                 headers={"Content-Type": "text/plain"})

    my_id = user_id
    print(f"id: {user_id}")
    sio.connect(wss, headers={"private-user-id": pid})
    get_users(session, url, area, room)
    return True


def get_users(s, server, area, room):
    print("[+] Get Rooms Users")
    val = s.get(f"{server}{api}/areas/{area}/rooms/{room}",
                headers={"Authentication": f"Bearer {pid}"})
    if val.status_code == 200:
        users = val.json()["connectedUsers"]
        print(f"[+] found {len(users)}")
        for user in users:
            Users[user["id"]] = user["name"] or ANON_NAME


def get_username(userid):
    return Users.get(userid, ANON_NAME)


def send_message(msg):
    sio.emit("user-msg", msg)
    sio.emit("user-msg", "")


def move_around(directions):
    uplr = {"u": "up", "d": "down", "l": "left", "r": "right"}
    for d in directions:
        if d in uplr:
            sio.emit("user-move", uplr[d])


@sio.event
def connect():
    print("[+] I'm connected!")


@sio.event
def connect_error(data):
    print("[+] The connection failed!")


@sio.event
def disconnect():
    print("I'm disconnected!")


@sio.on("server-user-joined-room")
def user_join(data):
    if data["id"] == my_id:
        return
    Users[data["id"]] = data["name"] or ANON_NAME
    tstamp = datetime.datetime.now().strftime("%H:%M")
    print(tstamp, f"{Users[data['id']]} joined")


@sio.on("server-user-left-room")
def user_leave(data):
    name = Users.pop(data, None)
    if name is not None:
        tstamp = datetime.datetime.now().strftime("%H:%M")
        print(tstamp, f"{name} left")


@sio.on("server-msg")
def server_msg(user_id, msg):
    if user_id == my_id or not msg:
        return
    author = get_username(user_id)

    tstamp = datetime.datetime.now().strftime("%H:%M")
    print(f"{tstamp} < {author} > {msg}")

    # Messages arrive on separate threads; replying one at a time keeps
    # each player's lines together and in order.
    with reply_lock:
        for plugin in PLUGINS:
            try:
                replies = plugin.cmd(author, msg)
            except Exception as ex:
                print(f"[!] {plugin.__name__} failed on {msg!r}: {ex!r}")
                continue
            for reply in replies:
                send_message(reply)
                time.sleep(1)


if __name__ == "__main__":
    main()
