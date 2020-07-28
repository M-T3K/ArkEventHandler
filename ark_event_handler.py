# This script is  intended to work as a daemon that handles events in the Ark Server
# It works by
# 1. Checking its internal file clock to see if enough time has passed since the previous event.
# 1.1 if not enough time has passed, broadcast a warning message in chat specifying the amount of time left for the current event and that after it is done there will be a restart.
# 2. Count the amount of json files in the same directory to determine quantity of events
# 3. Backup existing config files.
# 4. Select one of these events at random (pseudorandom, really) and parse the file.
# 5. Parse the config files to find the appropriate key, and substitute the <key,value> pairs specified in the json file.
# 6. Save World, Stop server, relaunch server.
import os
import shutil
import glob
import json
import configparser
import random
import subprocess
import time

from datetime import datetime
from collections import OrderedDict

ARKMAN_DIR = "/usr/local/bin/arkmanager"
CLOCK_FILE = "/home/steam/event_handler/ev_clock.evc"
CONFIG_DIR = "/home/steam/ARK/ShooterGame/Saved/Config/LinuxServer/"
BACKUP_DIR = "/home/steam/event_handler/DefaultBackup/"
EVENTS_DIR = "/home/steam/event_handler/events/"

# @info stolen from StackOverflow cuz I'm not a Python Guru
class MultiOrderedDict(OrderedDict):
    def __setitem__(self, key, value):
        if isinstance(value, list) and key in self:
            self[key].extend(value)
        else:
            # super(MultiOrderedDict, self).__setitem__(key, value)
            super().__setitem__(key, value) # in Python 3
        # END else
    # END setitem

    @staticmethod
    def getlist(value):
        return value.split(os.linesep)
    # END getlist
# END MultiOrderedDict


def update_clock(current, start_time, duration, nxt, prevs):
    cfg = configparser.ConfigParser(allow_no_value=True, strict=False, dict_type=MultiOrderedDict, converters={"list": MultiOrderedDict.getlist})
    cfg.add_section('EventsInformation')
    cfg['EventsInformation']['currentevent'] = current
    cfg['EventsInformation']['launchtime']   = start_time
    cfg['EventsInformation']['duration']     = duration
    if nxt != "":
        cfg['EventsInformation']['nextevent'] = nxt
    with open(CLOCK_FILE, 'w') as clock_file:
        cfg.write(clock_file, False)
        if prevs != []:
            previous_events = "\nprevevents=" + "\nprevevents=".join(prevs)
            clock_file.write(previous_events)
        # END if
    # END with
#END update_clock

def switch_events(ev_nxt, ev_after, prevs):
    # 2. Count Number of Json Files
    events = glob.glob1(EVENTS_DIR,"*.json")
    num_events = len(events)
    if num_events <= 0:
        print("There are no possible events")
        return
    # END if
    # 3. Backup existing config files
    if not os.path.exists(BACKUP_DIR): 
        os.makedirs(BACKUP_DIR)
    # END if
    for cfg_file in glob.glob1(CONFIG_DIR, "*.*"):
        src = CONFIG_DIR + cfg_file
        shutil.copy2(src, BACKUP_DIR)
    # END for

    find_next_event = True
    ev_nxt = ev_nxt.strip()
    if not ev_nxt == "":
        for ev_file in events:
            ev_file = ev_file.strip()
            if ev_nxt.strip() == ev_file.strip():
                print(ev_file)
                find_next_event = False
                break
            # END IF
        # END FOR
    # END IF

    if find_next_event:
        # 4. Select file at random and parse
        # 4.1 Select file at random
        ev_selected_idx = random.randint(0, num_events - 1)
        ev_selected_file = events[ev_selected_idx]
    else:
        ev_selected_file = ev_nxt
    # END ifelse
    print(ev_selected_file)
    # 4.2 Parse file
    ev_json = {}
    with open(EVENTS_DIR + ev_selected_file) as ev_doc:
        ev_json = json.load(ev_doc)
    # END with
    # 5. Parse the config files and substitute

    # 5.1 Game.ini
    cfg = configparser.ConfigParser(allow_no_value=True, strict=False, dict_type=MultiOrderedDict, converters={"list": MultiOrderedDict.getlist})
    cfg.optionxform = str # Important to preserve casing

    file_path = CONFIG_DIR + "Game.ini"
    cfg.read(file_path) # Reading Game.ini
    for k in ev_json['Game.ini']:
        print ("%s@%s: %s=%s -> %s" % (ev_selected_file, file_path, k, cfg['/script/shootergame.shootergamemode'][k], ev_json['Game.ini'][k]))
        cfg['/script/shootergame.shootergamemode'][k] = str(ev_json['Game.ini'][k])
    # END for
    # Now We must ensure we don't remove the duplicate entries for EngramEntryAutoUnlocks
    # Since configparser is uncapable of writing them, we have to do it ourselves
    engram_autounlocks = cfg.getlist('/script/shootergame.shootergamemode', 'EngramEntryAutoUnlocks')
    cfg.remove_option('/script/shootergame.shootergamemode', 'EngramEntryAutoUnlocks') # Erase those Contents
    # engram_autounlocks = engram_autounlocks[0].split("\n") # This seems to be only necessary in Windows, apparently WIN does something different in regards to the previous steps
    app_unlocks = "\nEngramEntryAutoUnlocks=" + "\nEngramEntryAutoUnlocks=".join(engram_autounlocks)
    with open(file_path, 'w') as game_ini:
        cfg.write(game_ini, False)
    # END with
    with open(file_path, 'a') as game_ini:
        game_ini.write(app_unlocks)
    # END with

    # 5.2 GameUserSettings.ini
    file_path = CONFIG_DIR + "GameUserSettings.ini"
    # ? If I don't create a new instance of the config parser I run into issues that prevent the program from functioning
    cfg = configparser.ConfigParser(allow_no_value=True, strict=False, dict_type=MultiOrderedDict)
    cfg.optionxform = str # Important to preserve casing
    cfg.read(file_path)
    for k in ev_json['GameUserSettings.ini']:
        print ("%s@%s: %s=%s -> %s" % (ev_selected_file, file_path, k, cfg['ServerSettings'][k], ev_json['GameUserSettings.ini'][k]))
        cfg['ServerSettings'][k] = str(ev_json['GameUserSettings.ini'][k])
    # END for

    # 5.3 ark-server-tools config 
    # @todo
    # @info not doing this right now, it should not be necessary
    # plus I'd have to develop a workaround for the system, since configparser
    # doesnt allow sectionless config files (why? just why?)

    # 5.4 MotD
    ev_type = ev_json['type']
    ev_duration = ev_json['duration']
    ev_admin_info = "\\n[INFO] EVENTID: %s, TYPE: %s, DURATION (HOURS): %s" % (ev_json['event'], ev_type, ev_duration)
    ev_extended_info = "\\n[INFO]"
    if ev_type == "none":
        ev_extended_info += " THERE ARE NO CONFIGURED EVENTS"
    elif ev_type == "battle":
        ev_extended_info += " THIS IS A BATTLE"
    elif ev_type == "rates":
        ev_extended_info += " THIS CHANGES SEVERAL RATES"
    elif ev_type == "race":
        ev_extended_info += " THIS IS A RACE"
    else:
        ev_extended_info += "[ERROR] UNKNOWN EVENT! CONTACT ADMINS ASAP!" #@info This should never happen if event json files are valid
    motd = '\\n'.join(ev_json['motd']) + ev_admin_info + ev_extended_info
    # 5.4.2 Update MotD

    cfg.optionxform=str # Again
    cfg['MessageOfTheDay']['Message'] = motd
    # END for
    with open(file_path, 'w') as gameuser_ini:
        cfg.write(gameuser_ini, False)
    # END with

    if ev_after == "":
        ev_after = ev_json['next']
    if ev_after == None:
        ev_after = ""
    update_clock(ev_selected_file, str(datetime.now().timestamp()), str(ev_duration), ev_after, prevs)
# END switch_events()

if __name__ == "__main__":
    # 1. Check internal Clock
    ev_launchtime = 0.0
    ev_current    = ""
    ev_duration   = ""
    ev_nxt        = ""
    evs_prevs     = []

    # 1.1) Check if file exists. If it doesnt, create it with actual contents.
    if not os.path.isfile(CLOCK_FILE):
        print("Creating file...")
        update_clock("None", str(datetime.now().timestamp()), "0", "", [])
    # END if

    # 1.2) Read File Contents

    cfg = configparser.ConfigParser(allow_no_value=True, strict=False, dict_type=MultiOrderedDict, converters={"list": MultiOrderedDict.getlist})
    cfg.read(CLOCK_FILE) 
    ev_current    = cfg['EventsInformation']['currentevent']
    ev_launchtime = float(cfg['EventsInformation']['launchtime'])
    ev_duration   = float(cfg['EventsInformation']['duration'])
    if cfg.has_option('EventsInformation', 'nextevent'):
        ev_nxt    = cfg['EventsInformation']['nextevent']
    if cfg.has_option('EventsInformation', 'prevevents'):
        evs_prevs = cfg.getlist('EventsInformation', 'prevevents')

    # 1.3) Check if we are done with the event
    current_time = datetime.now().timestamp()
    delta = (current_time - ev_launchtime)/3600
    if delta >= ev_duration or ev_duration <= 0:
        subprocess.run([ARKMAN_DIR, "broadcast", "\"Server will restart in 15mins to make room for the new events. Please, stop flying and disconnect to prevent further issues.\""])
        time.sleep(600) # Sleep for 600s = 10mins
        subprocess.run([ARKMAN_DIR, "broadcast", "\"Server will restart in 5mins to make room for the new events. Please, stop flying and disconnect to prevent further issues.\""])
        time.sleep(240) # Sleep for 240s = 4mins
        subprocess.run([ARKMAN_DIR, "broadcast", "\"SERVER RESTART IMMINENT. LAND ALL FLYERS AND DISCONNECT TO PREVENT MORE ISSUES.\""])
        time.sleep(60) # Sleep for 60s = 1min
        
        subprocess.run([ARKMAN_DIR, "stop", "--warn", "--saveworld"])
        # We load the Default one to undo any modifications the previous one may have done
        # This is necessary to avoid simultaneous events
        prevs = []
        switch_events("ev_default.json", None, prevs)
        if evs_prevs:
            prevs.extend(evs_prevs)
        # END if
        prevs.append(ev_current)
        switch_events(ev_nxt, None, prevs)

        subprocess.run([ARKMAN_DIR, "start"])
        # Restart the server
    else:
        print("We should not switch events")
    # END if
# END main