# ArkEventHandler
ArkEventHandler (ARKEV) is a python script that is designed to automatically and dynamically switch configurations to allow for the quick switch of events in a server.

## Events

In the sense used here, events represent different settings in the game's configuration files (and more!) that change the experience for players. In summary, take something like Ark's Evolution event on official servers. It changes several rates. If you wanted to put that in your server, ARKEV should be able to do it with ease.

## Objectives

At its core, this script simply changes one configuration with another. This can be done simply by having a System Administrator switch one config file with another, but that's not a practical solution.
A better solution would be to simply have a shell script that switches one config with another one. ARKEV goes one step further: it parses event specific json files that are much simpler than modifying the entire .ini files of the game.
Thus, we can say that the objective behind ARKEV is to provide a simple and extensible solution to automatically switch events for an ark server. 

Keep in mind I originally developed this script for my personal use. The Code isn't clean, but should be easily extensible. It also depends on ark-server-tools, but it should be easy enough to switch to the basic ark server or ark-server-manager.

## How does it work?

First, download the script onto your server. You may choose to clone the repo with `git clone https://github.com/M-T3K/ArkEventHandler.git` if you want to download the sample files. You will need [Git Version Control](https://git-scm.com/) for this to work.
Then, you have a couple options:
- You may wrap the script's main function in a while loop if you intend to run this permanently (as long as your computer is on).
- If you're on a *Nix System, you can create a Systemd service.
- If you're on a common *Nix Systems, you may take advantage of the Cron Daemon, and use crontab to schedule a crontab task. To do this, and to avoid issues regarding permissions, you should be the `root` user. Do `sudo crontab -e` to open the crontab file for the root user, no matter your current user. There you can type a cron expression for your task. The cron expression for this should look something along these lines: `* * * * * /usr/bin/python3 /home/user/path/to/ARKEV/ark_event_handler.py`. Exit and save.

Ark Server Tools are recommended for this script to work as intended. Feel free to PR if you create an alternative. 

## Event .json format

To be a valid events .json file, it will require to have the following fields:
```
"event": "None",
"type": "none",
"duration": 24,
"GameUserSettings.ini": {},
"Game.ini": {},
 "motd": []
```

You can find examples in the `events/` directory in this repo. All items in "GameUserSettings.ini" should be actual options in this file, and the same applies for "Game.ini".

## Requirements

The only true requirement is Python3, but there are some software distributions that are heavily recommended to use alongside ARKEV:

- [Python3](https://www.python.org/downloads/)
- ARKEV was tested on CENTOS8, and should run on all Linux distributions. Most of the script should be Windows compatible, but you'll need to work out what the subprocess commands are within the script.
- [FezVrasta's Ark Server Tools](https://github.com/FezVrasta/ark-server-tools)

