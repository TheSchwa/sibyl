# sibyl

a chat bot for controlling XBMC/Kodi

## Intro

This is my personal XMPP bot made mostly for controlling XBMC on my Raspberry
Pi. I find the `videos`, `seek`, `info`, `bookmark`, and `resume` commands to
be very handy. This is tested on RaspBMC and OSMC, but should work on anything
if you resolve the dependencies and setup python correctly. Sibyl does not
support windows, although you could probably get it working via cygwin. Sibyl
imports chat commands from python files in the directory specified by the
`cmd_dir` config option, which by default is `cmds`. This repository comes with
several plugins that most uers should find useful. For command explanations and
other info check out [the wiki][wiki]. Note that some XBMC commands (notably the
`library` plugin) in sibyl currently assume the bot is running on the same
device that is running XBMC (e.g. an RPi).

## Dependencies

You'll need the following installed in order to use sibyl:

 - [requests][req] - HTTP request and wrapper library - `pip install requests`
 - [smbc][samba] - python samba bindings - `pip install pysmbc`
 - [lxml][lxml] - xml and html parsing - `pip install lxml`
 - [dns][dns] - required for requests - `pip install dnspython`
 - [JSON-RPC][json] - you have to enable the web server in XBMC

You also need the relevant dependencies for your chosen chat protocol. Visit the
[Protocol][proto] page and read about your chosen protocol there.

The following are optional but not having them may render some commands broken:

 - [cec-client][cec] - HDMI CEC client for tv commands

One-liners for Ubuntu/Debian (not including protocol dependencies):

 - `sudo apt install python-requests python-smbc python-lxml python-dnspython`
 - `sudo pip install requests pysmbc lxml dnspython`

## Setup

Setup is very easy, all you really have to do is make a config file.

 1. Clone the repository with `git clone https://github.com/TheSchwa/sibyl.git`
 2. Install dependencies (see above)
 3. Enter the `sibyl` directory and copy `sibyl.conf.default` to `sibyl.conf`
 4. Edit `sibyl.conf` and set the required options
 5. If you want the bot to join a room set `rooms`
 6. Start the bot with `python run.py`
 7. For a full explanation of config options, see `sibyl.conf.default` or [the wiki][wiki]

If you'd rather not have comments cluttering your config, you can use
`sibyl.conf.example` instead of `sibyl.conf.default` or start from a blank file.

## XBMC/Kodi

Sibyl interfaces with XBMC using its JSON-RPC web interface. In
order to use it, you must enable the web server in XBMC (see the link in the
Dependencies section). Therefore, for `xbmc` plug-in commands, the bot does not
actually have to be running on the Pi. It just needs to be able to reach the
Pi's HTTP interface. The `library` plug-in commands, however, do assume the bot
is running on the same box as XBMC. Plesae note the port on which the web
server is running when you activate it. For example, you might set `xbmc_ip =
127.0.0.1:8080` in the config.

## CEC

Sibyl uses the `cec-client` bash script to give commands over HDMI-CEC
to an attached TV. This should be installed on most Pi distros by default. If
not, debian derivatives can install with `sudo apt-get install cec-client`. For
the CEC commands to work, the bot must be running on the Pi itself. Also note
that `cec-client` may not be found depending on your environment. On my Pi it's
located at `/home/pi/.xbmc-current/xbmc-bin/bin/cec-client`. Depending on your
distro, the user running Sibyl might need to be a member of the `videos` group
or similar to run `cec-client`.

## Search Directories

You can add folders to `video_dirs` and `audio_dirs` in
order to search them using the `search`, `audio`, `audios`, `video`, and
`videos` commands. You can add the following as list items:

  - local directory, example: `/media/flashdrive/videos`
  - samba share as `server,share`, example: `mediaserver,videos`
  - samba share as `server,share,user,pass`, example: `mediaserver,videos,pi,1234`


Also be aware that users cannot read `sshfs` mounts from other users by
default. If this is a problem with your setup, you have to specify `sshfs -o
allow_other ...` when you mount the share.

## Init Script

For Debian and derivates I include an init script, `init/sibyl.init` and the
actual execution script `sibyl`. You will have to change the `DAEMON` variable
in `sibyl.init` to the absolute path of `sibyl.sh`. You have to rename
`sibyl.init` to `sibyl` and place it in `/etc/init.d` for compliance with
Debian's init system. To enable auto-start on boot, run `sudo update-rc.d sibyl
defaults`.

## Systemd Service

Many systems have recently switched to systemd. Simply copy
`init/sibyl.service` to `/etc/systemd/system/sibyl.service` and modify the
`ExecStart` line to point to `run.py` and make sure `run.py` is executable
(e.g. `chmod +x run.py`).

## More Info and Troubleshooting

There is a great deal of information on [the wiki][wiki]. Also see the
[Troubleshooting page][trouble] and [Commands page][cmd].

## Contact Me

If you have a bug report or feature request, use github's issue tracker. For
other stuff, you can join my Sibyl XMPP room `sibyl@conference.jahschwa.com`,
the IRC channel `chat.freenode.net#sibyl`, or contact me at
[haas.josh.a@gmail.com][mail].

 [wiki]: https://github.com/TheSchwa/sibyl/wiki
 [req]: http://docs.python-requests.org/en/latest/
 [samba]: https://bitbucket.org/nosklo/pysmbclient/src/057512c24175?at=default
 [cec]: http://libcec.pulse-eight.com/
 [json]: http://kodi.wiki/view/Webserver#Enabling_the_webserver
 [mail]: mailto:haas.josh.a@gmail.com
 [lxml]: http://lxml.de/
 [dns]: http://www.dnspython.org/
 [proto]: https://github.com/TheSchwa/sibyl/wiki/Protocols
 [trouble]: https://github.com/TheSchwa/sibyl/wiki/Troubleshooting
 [cmd]: https://github.com/TheSchwa/sibyl/wiki/Commands
