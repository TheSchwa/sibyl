#!/usr/bin/env python
#
# XBMC JSON-RPC XMPP MUC bot

# built-ins
import sys,json,time,os,subprocess,logging,pickle,socket

# dependencies
import requests
from jabberbot import JabberBot,botcmd
from smbclient import SambaClient

class SibylBot(JabberBot):
  """More details: https://github.com/TheSchwa/sibyl/wiki/Commands"""
  
  ######################################################################
  # Setup                                                              #
  ######################################################################
  
  def __init__(self,*args,**kwargs):
    """override to only answer direct msgs"""
    
    # required kwargs
    self.rpi_ip = kwargs.get('rpi_ip')
    
    # optional kwargs
    self.nick_name = kwargs.get('nick_name','Sibyl')
    self.audio_dirs = kwargs.get('audio_dirs',[])
    self.video_dirs = kwargs.get('video_dirs',[])
    self.lib_file = kwargs.get('lib_file','sibyl.pickle')
    self.max_matches = kwargs.get('max_matches',10)
    self.xbmc_user = kwargs.get('xbmc_user',None)
    self.xbmc_pass = kwargs.get('xbmc_pass',None)
    self.chat_ctrl = kwargs.get('chat_ctrl',False)
    
    # configure logging
    self.log_file = kwargs.get('log_file','/var/log/sibyl.log')
    logging.basicConfig(filename=self.log_file,format='%(asctime)-15s | %(message)s')
    
    # delete kwargs before calling super init
    words = (['rpi_ip','nick_name','audio_dirs','video_dirs','log_file',
        'lib_file','max_matches','xbmc_user','xbmc_pass','chat_ctrl'])
    for w in words:
      try:
        del kwargs[w]
      except KeyError:
        pass
    
    self.__born = time.time()
    
    # add an additional kwarg for enabling only direct messages
    self.only_direct = kwargs.get('only_direct',False)
    try:
      del kwargs['only_direct']
    except KeyError:
      pass
    
    # create libraries
    if os.path.isfile(self.lib_file):
      self.library(None,'load')
    else:
      self.lib_last_rebuilt = time.asctime()
      self.lib_last_elapsed = 0
      self.lib_audio_dir = None
      self.lib_audio_file = None
      self.lib_video_dir = None
      self.lib_video_file = None
      self.library(None,'rebuild')
    
    super(SibylBot,self).__init__(*args,**kwargs)

  def callback_message(self,conn,mess):
    """override to only answer direct msgs"""
    
    # wait 5 seconds before executing commands to account for XMPP MUC history
    # playback since JabberBot and XMPPpy don't let you disable it by
    # modifying the presence stanza
    now = time.time()
    if now<self.__born+5:
      return
    
    # discard blank messages
    msg = mess.getBody()
    if not msg:
      return
    
    # don't respond to messages from myself
    if self.nick_name.lower() in str(mess.getFrom()).lower():
      return
    
    # only respond to direct messages (i.e. those containing NICKNAME)
    if not self.only_direct or msg.lower().startswith(self.nick_name.lower()):
      mess.setBody(' '.join(msg.split(' ',1)[1:]))
      return super(SibylBot,self).callback_message(conn,mess)

  def unknown_command(self,mess,cmd,args):
    """override unknown command callback"""
    
    return 'Unknown command "'+cmd+'"'

  ######################################################################
  # General Commands                                                   #
  ######################################################################

  @botcmd
  def git(self,mess,args):
    """return a link to the github page"""
  
    return 'https://github.com/TheSchwa/sibyl'

  @botcmd
  def hello(self,mess,args):
    """reply if someone says hello"""
    
    return 'Hello world!'
  
  @botcmd
  def network(self,mess,args):
    """reply with some network info"""
    
    s = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    s.connect(('8.8.8.8',80))
    myip = s.getsockname()[0]
    s.close()
    
    piip = self.rpi_ip
    exip = requests.get('http://ipecho.net/plain').text.strip()
    
    return 'My IP - '+myip+' --- RPi IP - '+piip+' --- External IP - '+exip

  @botcmd
  def die(self,mess,args):
    """kill sibyl"""
    
    if not self.chat_ctrl:
      return 'chat_ctrl disabled'
    
    sys.exit()

  @botcmd
  def reboot(self,mess,args):
    """restart sibyl"""
    
    if not self.chat_ctrl:
      return 'chat_ctrl disabled'
    
    DEVNULL = open(os.devnull,'wb')
    subprocess.Popen(['service','sibyl','restart'],
        stdout=DEVNULL,stderr=DEVNULL,close_fds=True)
    sys.exit()

  @botcmd
  def tv(self,mess,args):
    """pass command to cec-client - tv (on|standby|as)"""
    
    cmd = ['echo',args+' 0']
    cec = ['cec-client','-s']
    
    # execute echo command and pipe output to PIPE
    p = subprocess.Popen(cmd,stdout=subprocess.PIPE)
    
    # execute cec-client using PIPE as input and sending output to /dev/null
    DEVNULL = open(os.devnull,'wb')
    subprocess.call(cec,stdin=p.stdout,stdout=DEVNULL,close_fds=True)

  @botcmd
  def ups(self,mess,args):
    """get latest UPS tracking status - sibyl ups number"""
    
    try:
      url = ('http://wwwapps.ups.com/WebTracking/track?track=yes&trackNums='
          + args + '&loc=en_us')
      page = requests.get(url).text
      
      start = page.find('Activity')
      (location,start) = getcell(start+1,page)
      (newdate,start) = getcell(start+1,page)
      (newtime,start) = getcell(start+1,page)
      (activity,start) = getcell(start+1,page)
      timestamp = newdate + ' ' + newtime
      return timestamp+' - '+location+' - '+activity
      
    except:
      return 'Invalid tracking number'

  @botcmd
  def wiki(self,mess,args):
    """return a link and brief from wikipedia - wiki title"""
    
    url = ('http://en.wikipedia.org/w/api.php?action=opensearch&search='
        + args + '&format=json')
    response = requests.get(url)
    result = json.loads(response.text)
    title = result[1][0]
    text = result[2]
    try:
      text.remove(u'')
      text = '\n'.join(text)
    except ValueError:
      pass
    url = result[3][0]
    return unicode(title)+' - '+unicode(url)+'\n'+unicode(text)
  
  ######################################################################
  # XBMC Commands                                                      #
  ######################################################################
  
  @botcmd
  def info(self,mess,args):
    """display info about currently playing file"""
    
    # abort if nothing is playing
    pid = self.xbmc_active_player()
    if pid is None:
      return 'Nothing playing'
    
    # get file name
    result = self.xbmc('Player.GetItem',{'playerid':pid})
    name = result['result']['item']['label']
    
    # get speed, current time, and total time
    result = self.xbmc('Player.GetProperties',{'playerid':pid,'properties':['speed','time','totaltime']})
    current = result['result']['time']
    total = result['result']['totaltime']
    
    # translate speed: 0 = 'paused', 1 = 'playing'
    speed = result['result']['speed']
    status = 'playing'
    if speed==0:
      status = 'paused'
    
    playlists = ['Audio','Video','Picture']
    return playlists[pid]+' '+status+' at '+time2str(current)+'/'+time2str(total)+' - "'+name+'"'
  
  @botcmd
  def play(self,mess,args):
    """if xbmc is paused, resume playing"""
    
    self.playpause(0)
  
  @botcmd
  def pause(self,mess,args):
    """if xbmc is playing, pause"""
    
    self.playpause(1)
  
  @botcmd
  def stop(self,mess,args):
    """if xbmc is playing, stop"""
    
    # abort if nothing is playing
    pid = self.xbmc_active_player()
    if pid is None:
      return None

    self.xbmc('Player.Stop',{"playerid":pid})
  
  @botcmd
  def prev(self,mess,args):
    """go to previous playlist item"""
    
    # abort if nothing is playing
    pid = self.xbmc_active_player()
    if pid is None:
      return None
    
    # the first call goes to 0:00, the second actually goes back in playlist
    self.xbmc('Player.GoTo',{'playerid':pid,'to':'previous'})
    self.xbmc('Player.GoTo',{'playerid':pid,'to':'previous'})

  @botcmd
  def next(self,mess,args):
    """go to next playlist item"""
    
    # abort if nothing is playing
    pid = self.xbmc_active_player()
    if pid is None:
      return None
    
    self.xbmc('Player.GoTo',{'playerid':pid,'to':'next'})

  @botcmd
  def jump(self,mess,args):
    """jump to an item# in the playlist - jump #"""
    
    # abort if nothing is playing
    pid = self.xbmc_active_player()
    if pid is None:
      return None
    
    # try to parse the arg to an int
    try:
      num = int(args.split(' ')[-1])-1
      self.xbmc('Player.GoTo',{'playerid':pid,'to':num})
      return None
    except ValueError:
      return 'Playlist position must be an integer greater than 0'
  
  @botcmd
  def seek(self,mess,args):
    """go to a specific time - seek [hh:]mm:ss"""
    
    # abort if nothing is playing
    pid = self.xbmc_active_player()
    if pid is None:
      return None
    
    # try to parse the arg as a time
    try:
      t = args.split(' ')[-1]
      c1 = t.find(':')
      c2 = t.rfind(':')
      s = int(t[c2+1:])
      h = 0
      if c1==c2:
        m = int(t[:c1])
      else:
        m = int(t[c1+1:c2])
        h = int(t[:c1])
      self.xbmc('Player.Seek',{'playerid':pid,'value':{'hours':h,'minutes':m,'seconds':s}})
    except ValueError:
      return 'Times must be in the format m:ss or h:mm:ss'

  @botcmd
  def restart(self,mess,args):
    """start playing again from 0:00"""
    
    # abort if nothing is playing
    pid = self.xbmc_active_player()
    if pid is None:
      return None
    
    self.xbmc('Player.Seek',{'playerid':pid,'value':{'seconds':0}})

  @botcmd
  def hop(self,mess,args):
    """move forward or back - hop [small|big] [back|forward]"""
    
    # abort if nothing is playing
    pid = self.xbmc_active_player()
    if pid is None:
      return None
    
    # check for 'small' (default) and 'big'
    s = ''
    if 'big' in args:
      s += 'big'
    else:
      s += 'small'
    
    # check for 'back' (default) and 'forward'
    if 'forward' in args:
      s += 'forward'
    else:
      s += 'backward'
    
    self.xbmc('Player.Seek',{'playerid':pid,'value':s})
    return None

  @botcmd
  def stream(self,mess,args):
    """stream from [YouTube, Twitch (Live)] - stream url"""
    
    msg = mess.getBody()
    
    if 'youtube' in msg:
      
      vid = msg[msg.find('watch?v=')+8:]
      html = requests.get('http://youtube.com/watch?v='+vid).text
      title = html[html.find('<title>')+7:html.find(' - YouTube</title>')]
      title = title.replace('&#39;',"'")
      
      channel = html.find('class="yt-user-info"')
      start = html.find('>',channel+1)
      start = html.find('>',start+1)+1
      stop = html.find('<',start+1)
      channel = html[start:stop]
      
      response = self.xbmc('Player.Open',{'item':{'file':'plugin://plugin.video.youtube/play/?video_id='+vid}})
      return 'Streaming "'+title+'" by "'+channel+'" from YouTube'
      
    elif 'twitch' in msg:
      
      vid = msg[msg.find('twitch.tv/')+10:]
      html = requests.get('http://twitch.tv/'+vid).text
      
      stream = html.find("property='og:title'")
      stop = html.rfind("'",0,stream)
      start = html.rfind("'",0,stop)+1
      stream = html[start:stop]
      
      title = html.find("property='og:description'")
      stop = html.rfind("'",0,title)
      start = html.rfind("'",0,stop)+1
      title = html[start:stop]
      
      response = self.xbmc('Player.Open',{'item':{'file':'plugin://plugin.video.twitch/playLive/'+vid}})
      return 'Streaming "'+title+'" by "'+stream+'" from Twitch Live'
      
    else:
      return 'Unsupported URL'
  
  @botcmd
  def search(self,mess,args):
    """search all paths for matches - search [include -exclude]"""
    
    name = args.split(' ')
    matches = []
    
    dirs = [self.lib_video_dir,self.lib_video_file,self.lib_audio_dir,self.lib_audio_file]
    for d in dirs:
      matches.extend(self.matches(d,name))
    
    if len(matches)==0:
      return 'Found 0 matches'
    
    if len(matches)>1:
      if self.max_matches<1 or len(matches)<=self.max_matches:
        return 'Found '+str(len(matches))+' matches: '+str(matches)
      else:
        return 'Found '+str(len(matches))+' matches'
    
    return 'Found '+str(len(matches))+' matche: '+str(matches[0])

  @botcmd
  def videos(self,mess,args):
    """search and open a folder as a playlist - videos [include -exclude] [track#]"""
    
    return self.files(args,self.lib_video_dir,1)

  @botcmd
  def video(self,mess,args):
    """search and play a single video - video [include -exclude]"""

    return self.file(args,self.lib_video_file)

  @botcmd
  def audios(self,mess,args):
    """search and open a folder as a playlist - audios [include -exclude] [track#]"""
    
    return self.files(args,self.lib_audio_dir,0)
  
  @botcmd
  def audio(self,mess,args):
    """search and play a single audio file - audio [include -exclude]"""
    
    return self.file(args,self.lib_audio_file)

  @botcmd
  def fullscreen(self,mess,args):
    """toggle fullscreen"""
    
    self.xbmc('GUI.SetFullscreen',{'fullscreen':'toggle'})
  
  @botcmd
  def library(self,mess,args):
    """control media library - library (info|load|rebuild|save)"""
    
    if args=='load':
      with open(self.lib_file,'r') as f:
        d = pickle.load(f)
      self.lib_last_rebuilt = d['lib_last_rebuilt']
      self.lib_last_elapsed = d['lib_last_elapsed']
      self.lib_video_dir = d['lib_video_dir']
      self.lib_video_file = d['lib_video_file']
      self.lib_audio_dir = d['lib_audio_dir']
      self.lib_audio_file = d['lib_audio_file']
      return 'Library loaded from: "'+self.lib_file+'"'
      
    elif args=='save':
      d = ({'lib_last_rebuilt':self.lib_last_rebuilt,
            'lib_last_elapsed':self.lib_last_elapsed,
            'lib_video_dir':self.lib_video_dir,
            'lib_video_file':self.lib_video_file,
            'lib_audio_dir':self.lib_audio_dir,
            'lib_audio_file':self.lib_audio_file})
      with open(self.lib_file,'w') as f:
        pickle.dump(d,f,-1)
      return 'Library saved to: "'+self.lib_file+'"'
      
    elif args=='rebuild':
      if mess is not None:
        t = self.lib_last_elapsed
        s = str(int(t/60))+':'
        s += str(int(t-60*int(t/60))).zfill(2)
        self.send_simple_reply(mess,'Working... (last rebuild took '+s+')')
      start = time.time()
      self.lib_last_rebuilt = time.asctime()
      self.lib_video_dir = self.find('dir',self.video_dirs)
      self.lib_video_file = self.find('file',self.video_dirs)
      self.lib_audio_dir = self.find('dir',self.audio_dirs)
      self.lib_audio_file = self.find('file',self.audio_dirs)
      result = self.library(None,'save')
      self.lib_last_elapsed = time.time()-start
      if mess is not None:
        self.log.debug('Library rebuilt in '+str(self.lib_last_elapsed))
      return 'Library rebuilt and'+result[7:]
    
    t = self.lib_last_elapsed
    s = str(int(t/60))+':'
    s += str(int(t-60*int(t/60))).zfill(2)
    return 'Last rebuilt on '+self.lib_last_rebuilt+' in '+s
  
  ######################################################################
  # Helper Functions                                                   #
  ######################################################################
  
  def xbmc(self,method,params=None):
    """wrapper method to always provide IP to static method"""
    
    return xbmc(self.rpi_ip,method,params,self.xbmc_user,self.xbmc_pass)
  
  def xbmc_active_player(self):
    """wrapper method to always provide IP to static method"""
    
    return xbmc_active_player(self.rpi_ip,self.xbmc_user,self.xbmc_pass)
  
  def playpause(self,target):
    """helper function for play() and pause()"""
    
    pid = self.xbmc_active_player()
    if pid is None:
      return None

    speed = self.xbmc('Player.GetProperties',{'playerid':pid,'properties':["speed"]})
    speed = speed['result']['speed']
    if speed==target:
      self.xbmc('Player.PlayPause',{"playerid":pid})
  
  def files(self,args,dirs,pid):
    """helper function for videos() and audios()"""
    
    # check for item# as last arg
    args = args.split(' ')
    num = None
    try:
      num = int(args[-1])-1
    except ValueError:
      pass
    
    # default is 0 if not specified
    if num is None:
      num = 0
      name = args
    else:
      name = args[:-1]
    
    # find matches and respond if len(matches)!=1
    matches = self.matches(dirs,name)
    
    if len(matches)==0:
      return 'Found 0 matches'
    
    if len(matches)>1:
      if self.max_matches<1 or len(matches)<=self.max_matches:
        return 'Found '+str(len(matches))+' matches: '+str(matches)
      else:
        return 'Found '+str(len(matches))+' matches'
    
    # if there was 1 match, add the whole directory to a playlist
    self.xbmc('Playlist.Clear',{'playlistid':pid})
    self.xbmc('Playlist.Add',{'playlistid':pid,'item':{'directory':matches[0]}})
    self.xbmc('Player.Open',{'item':{'playlistid':pid,'position':num}})
    self.xbmc('GUI.SetFullscreen',{'fullscreen':True})

    return 'Playlist from "'+matches[0]+'" starting at #'+str(num+1)
  
  def file(self,args,dirs):
    """helper function for video() and audio()"""
    
    name = args.split(' ')
    
    # find matches and respond if len(matches)!=1
    matches = self.matches(dirs,name)
    
    if len(matches)==0:
      return 'Found 0 matches'
    
    if len(matches)>1:
      if self.max_matches<1 or len(matches)<=self.max_matches:
        return 'Found '+str(len(matches))+' matches: '+str(matches)
      else:
        return 'Found '+str(len(matches))+' matches'
    
    # if there was 1 match, play the file
    self.xbmc('Player.Open',{'item':{'file':matches[0]}})
    self.xbmc('GUI.SetFullscreen',{'fullscreen':True})

    return 'Playing "'+matches[0]+'"'
  
  def matches(self,lib,name):
    """helper function for search(), files(), and file()"""
    
    matches = []
    for entry in lib:
      try:
        if checkall(name,entry):
          matches.append(entry)
      except:
        pass
    return matches

  def find(self,fd,dirs):
    """helper function for library()"""
    
    paths = []
    smbpaths = []
    
    # sort paths into local and samba based on whether they're tuples
    for path in dirs:
      if isinstance(path,dict):
        smbpaths.append(path)
      else:
        paths.append(path)
    
    result = []
    
    # find all matching directories or files depending on fd parameter
    for path in paths:
      try:
        if fd=='dir':
          contents = rlistdir(path)
        else:
          contents = rlistfiles(path)
        for entry in contents:
          try:
            result.append(str(entry))
          except UnicodeError:
            self.log.error('Unicode error parsing path "'+entry+'"')
      except OSError:
        self.log.error('Unable to traverse "'+path+'"')
    
    # same as above but for samba shares
    for path in smbpaths:
      try:
        smb = SambaClient(**path)
        if fd=='dir':
          contents = rsambadir(smb,'/')
        else:
          contents = rsambafiles(smb,'/')
        smb.close()
        for entry in contents:
          try:
            result.append(str(entry))
          except UnicodeError:
            self.log.error('Unicode error parsing path "'+entry+'"')
      except RuntimeError:
        self.log.error('Unable to traverse "'+path+'"')
    
    return result

########################################################################
# Static Functions                                                     #
########################################################################

def xbmc(ip,method,params=None,user=None,pword=None):
  """make a JSON-RPC request to xbmc and return the resulti as a dict"""
  
  p = {'jsonrpc':'2.0','id':1,'method':method}
  if params is not None:
    p['params'] = params
  
  url = 'http://'+ip+'/jsonrpc'
  headers = {'content-type':'application/json'}
  payload = p
  params = {'request':json.dumps(payload)}
  
  r = requests.get(url,params=params,headers=headers,auth=(user,pword))
  
  return json.loads(r.text)

def xbmc_active_player(ip,user=None,pword=None):
  """return the id of the currently active player or None"""
  
  j = xbmc(ip,'Player.GetActivePlayers',user=user,pword=pword)
  if len(j['result'])==0:
    return None
  return j['result'][0]['playerid']

def time2str(t):
  """change the time dict to a string"""
  
  s = ''
  hr = str(t['hours'])
  mi = str(t['minutes'])
  sec = str(t['seconds'])
  
  if t['hours']>0:
    s += (hr+':')
    s+= (mi.zfill(2)+':')
  else:
    s+= (mi+':')
  s+= sec.zfill(2)
  
  return s

def rlistdir(path):
  """list folders recursively"""
  
  alldirs = []
  for (cur_path,dirnames,filenames) in os.walk(path):
    for dirname in dirnames:
      alldirs.append(os.path.join(cur_path,dirname)+'/')
  return alldirs

def rlistfiles(path):
  """list files recursively"""
  
  allfiles = []
  for (cur_path,dirnames,filenames) in os.walk(path):
    for filename in filenames:
      allfiles.append(os.path.join(cur_path,filename))
  return allfiles

def rsambadir(smb,path):
  """recursively list directories"""
  
  alldirs = []
  items = smb.listdir(path)
  for item in items:
    cur_path = os.path.join(path,item)
    if smb.isdir(cur_path):
      alldirs.append(str('smb:'+smb.path+cur_path)+'/')
      alldirs.extend(rsambadir(smb,cur_path))
  return alldirs

def rsambafiles(smb,path):
  """recursively list files"""
  
  allfiles = []
  items = smb.listdir(path)
  for item in items:
    cur_path = os.path.join(path,item)
    if smb.isfile(cur_path):
      allfiles.append(str('smb:'+smb.path+cur_path))
    elif smb.isdir(cur_path):
      allfiles.extend(rsambafiles(smb,cur_path))
  return allfiles

def checkall(l,s):
  """make sure all strings in l are in s unless they start with '-' """
  
  for x in l:
    if (x[0]!='-') and (x.lower() not in s.lower()):
      return False
    if (x[0]=='-') and (x[1:].lower() in s.lower()):
      return False
  return True

def getcell(start,page):
  """return the contents of the next table cell and its end index"""
  
  start = page.find('<td',start+1)                                                                                                                                                   
  start = page.find('>',start+1)                                                                                                                                                     
  stop = page.find('</td>',start+1)                                                                                                                                                  
  s = page[start+1:stop].strip()
  s = s.replace('\n',' ').replace('\t',' ')
  return (' '.join(s.split()),stop)
