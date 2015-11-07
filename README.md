# sibyl
an XMPP bot for controlling XBMC/Kodi

## Intro
This is my personal XMPP bot made mostly for controlling XBMC on my Raspberry Pi. I find the `videos`, `seek`, `info`, `bookmark`, and `resume` commands to be very handy. This is tested on RaspBMC, but should work on anything if you resolve the dependencies and setup python correctly. The code is in the `sibylbot.py` as a library, and an example script `sibyl.py` is shown for running the bot. For command explanations and other info check out [the wiki][1]. Currently sibyl is built assuming the bot is running on the same device that is running XBMC (e.g. an RPi).

## Dependencies
You'll need the following installed in order to use sibyl:
 - [jabberbot][2] - XMPP bot using xmpppy - `pip install jabberbot`
 - [requests][3] - HTTP request and wrapper library - `pip install requests`
 - [pysmbclient][4] - crude `smbclient` wrapper - add the source to your python path
 - [JSON-RPC][6] - enable the web server in XBMC

The following are optional but not having them may render some commands broken:
 - [cec-client][5] - HDMI CEC client for tv commands

## Setup
Below is a minimum working example, but most users will want to take a look at `sibyl.py` or `sibyl_adv.py` for more details on common use cases.

```
from sibylbot import SibylBot

USERNAME = 'sibyl@xmpp.com'
PASSWORD = 'password'
RPI_IP = '192.168.1.314'

bot = SibylBot(USERNAME,PASSWORD,rpi_ip=RPI_IP)
bot.run_forever()
```

## JabberBot
By default sibyl is setup to join an XMPP MUC (i.e. group chat) but you can change that if you want. Refer to the [examples directory][7] for JabberBot. Adding additional commands is easy as well. Simply define a new method inside the `SibylBot` class and preface it with `@botcmd` to register the command.

Note that there is currently a bug in JabberBot. It does not correctly ignore message from itself when in a MUC. This is fixed naievly in sibyl by simply searching for `NICKNAME` in the from field of XMPP replies. Therefore, as currently implemented, any user whose name contains sibyl's `NICKNAME` will be ignored.

## XBMC/Kodi
Sibyl interfaces with XBMC using its JSON-RPC web interface. In order to use it, you must enable the web server in XBMC (see the link in the Dependencies section). Therefore, for these commands, the bot does not actually have to be running on the Pi. It just needs to be able to reach the Pi's HTTP interface..

## CEC
Sibyl uses the `cec-client` bash script to give commands over HDMI-CEC to an attached TV. This should be installed on most Pi distros by default. If not, debian derivatives can install with `sudo apt-get install cec-client`. For the CEC commands to work, the bot must be running on the Pi itself. Also note that `cec-client` may not be found depending on your environment. On my Pi it's located at `/home/pi/.xbmc-current/xbmc-bin/bin/cec-client`.

## Search Directories
You can add folders to `VIDEODIRS` and `AUDIODIRS` in order to search them using the `search`, `audio`, `audios`, `video`, and `videos` commands. You can add the following as list items:
  - local directory, example: `'/media/flashdrive/videos'`
  - samba share, example: `{'server':'THESCHWA','share':'videos','username':'user','password':'pass'}`

For samba shares not protected by a passowrd, you can exclude the `'username'` and `'password'` keys in the above example.

Also be aware that root cannot read `sshfs` mounts from other users by default. If this is a problem with your setup (e.g. I run sibyl as `root` via the init script, but the `sshfs` mount requires the `pi` user's pubkey), you have to specify `sshfs -o allow_root ...` when you mount the share as a non-root user.

## Init Script
For Debian and derivates I include an init script, `sibyl.init` and the actual execution script `sibyl`. Note that if you want to use these you may have to change the `DAEMON` variable in `sibyl.init`. In my setup, `sibyl.init` is in `/etc/init.d/`, `sibyl` is in `/home/pi/bin`, and `sibyl.py` is in `/home/pi/bin`. You will likely have to rename `sibyl.init` to `sibyl` for compliance with Debian's init system.

## Logging
By default, sibyl logs to `/var/log/sibyl.log`. To enable debug logging, simply uncomment the debug line in `sibyl.py`. This log file requires sibyl be run as root. If that is undesirable, you can specify a different log file when initializing the bot with the `log_file` kwarg.

## Known Bugs
 - Very large media libraries may cause smaller devices like the Pi to run out of RAM.

## Contact Me
If you have a bug report or feature request, use github's issue tracker. For other stuff, you can join my Sibyl XMPP room `sibyl@conference.jahschwa.com`, the IRC channel `chat.freenode.net#sibyl`, or contact me at [haas.josh.a@gmail.com][8].

 [1]: https://github.com/TheSchwa/sibyl/wiki
 [2]: https://thp.io/2007/python-jabberbot/
 [3]: http://docs.python-requests.org/en/latest/
 [4]: https://bitbucket.org/nosklo/pysmbclient/src/057512c24175?at=default
 [5]: http://libcec.pulse-eight.com/
 [6]: http://kodi.wiki/view/Webserver#Enabling_the_webserver
 [7]: https://github.com/antont/pythonjabberbot/tree/master/examples
 [8]: mailto:haas.josh.a@gmail.com
