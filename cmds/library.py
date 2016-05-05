#!/usr/bin/env python

import os,pickle,time,traceback

import smbc

from sibyl.jabberbot import botcmd,botfunc,botinit
from sibyl.sibylbot import botconf
from sibyl.util import *

@botconf
def conf(bot):
  """add config options"""

  return [{'name' : 'lib_file',
            'default' : 'data/sibyl_lib.pickle',
            'valid' : bot.conf.valid_file},
          {'name' : 'max_matches',
            'default' : 10,
            'parse' : bot.conf.parse_int},
          {'name' : 'audio_dirs',
            'default' : [],
            'valid' : valid_lib,
            'parse' : parse_lib},
          {'name' : 'video_dirs',
            'default' : [],
            'valid' : valid_lib,
            'parse' : parse_lib}]

def valid_lib(conf,lib):
  """return True if the lib contains valid directories or samba shares"""

  for (i,l) in enumerate(lib):
    if isinstance(l,str):
      if not os.path.isdir(l):
        conf.log('warning','path "'+l+'" is not a valid directory')
        return False
    elif isinstance(l,dict):
      if 'server' not in l.keys():
        conf.log('warning','key "server" missing from item '+str(i+1))
        return False
      if 'share' not in l.keys():
        conf.log('warning','key "share" missing from item '+str(i+1))
        return False
  return True

def parse_lib(conf,opt,val):
  """parse the lib into a list"""

  val = val.replace('\n','')
  entries = split_strip(val,';')
  lib = []
  for entry in entries:
    if entry=='':
      continue
    if ',' in entry:
      params = split_strip(entry,',')
      item = {'server':params[0], 'share':params[1], 'username':None, 'password':None}
      if len(params)>2:
        item['username'] = params[2]
      if len(params)>3:
        item['password'] = params[3]
    else:
      item = entry
    lib.append(item)
  return lib

@botinit
def init(bot):
  """create libraries"""
  
  if os.path.isfile(bot.lib_file):
    bot.run_cmd('library','load')
  else:
    bot.lib_last_rebuilt = time.asctime()
    bot.lib_last_elapsed = 0
    bot.lib_audio_dir = None
    bot.lib_audio_file = None
    bot.lib_video_dir = None
    bot.lib_video_file = None
    bot.run_cmd('library','rebuild')

@botcmd
def library(bot,mess,args):
  """control media library - library (info|load|rebuild|save)"""

  # read the library from a pickle and load it into sibyl
  if args=='load':
    with open(bot.lib_file,'r') as f:
      d = pickle.load(f)
    bot.lib_last_rebuilt = d['lib_last_rebuilt']
    bot.lib_last_elapsed = d['lib_last_elapsed']
    bot.lib_video_dir = d['lib_video_dir']
    bot.lib_video_file = d['lib_video_file']
    bot.lib_audio_dir = d['lib_audio_dir']
    bot.lib_audio_file = d['lib_audio_file']

    n = len(bot.lib_audio_file)+len(bot.lib_video_file)
    s = 'Library loaded from "'+bot.lib_file+'" with '+str(n)+' files'
    bot.log.info(s)
    return s

  # save sibyl's library to a pickle
  elif args=='save':
    d = ({'lib_last_rebuilt':bot.lib_last_rebuilt,
          'lib_last_elapsed':bot.lib_last_elapsed,
          'lib_video_dir':bot.lib_video_dir,
          'lib_video_file':bot.lib_video_file,
          'lib_audio_dir':bot.lib_audio_dir,
          'lib_audio_file':bot.lib_audio_file})
    with open(bot.lib_file,'w') as f:
      pickle.dump(d,f,-1)

    s = 'Library saved to "'+bot.lib_file+'"'
    bot.log.info(s)
    return s

  # rebuild the library by traversing all paths then save it
  elif args=='rebuild':

    # when sibyl calls this method on init mess is None
    if mess is not None:
      t = sec2str(bot.lib_last_elapsed)
      bot.send_simple_reply(mess,'Working... (last rebuild took '+t+')')

    # time the rebuild and update library vars
    start = time.time()
    bot.lib_last_rebuilt = time.asctime()

    libs = [('lib_video_dir','dir',bot.video_dirs),
            ('lib_video_file','file',bot.video_dirs),
            ('lib_audio_dir','dir',bot.audio_dirs),
            ('lib_audio_file','file',bot.audio_dirs)]
    errors = []
    for lib in libs:
      (r,e) = find(bot,lib[1],lib[2])
      setattr(bot,lib[0],r)
      for x in e:
        if x not in errors:
          bot.log.error(x[1])
          errors.append(x)
    
    bot.lib_last_elapsed = int(time.time()-start)
    result = bot.run_cmd('library','save')

    s = 'Library rebuilt in '+sec2str(bot.lib_last_elapsed)
    bot.log.info(s)
    if errors:
      s += ' with errors (see log): '+str([x[0] for x in errors])
    return s

  # default prints some info
  t = bot.lib_last_elapsed
  s = str(int(t/60))+':'
  s += str(int(t-60*int(t/60))).zfill(2)
  n = len(bot.lib_audio_dir)+len(bot.lib_video_dir)
  return 'Rebuilt on '+bot.lib_last_rebuilt+' in '+s+' with '+str(n)+' files'

@botcmd
def search(bot,mess,args):
  """search all paths for matches - search [include -exclude]"""

  name = args.split(' ')
  _matches = []

  # search all library paths
  dirs = [bot.lib_video_dir,bot.lib_video_file,bot.lib_audio_dir,bot.lib_audio_file]
  for d in dirs:
    _matches.extend(matches(d,name))

  if len(_matches)==0:
    return 'Found 0 matches'

  # reply with matches based on max_matches setting
  if len(_matches)>1:
    if bot.max_matches<1 or len(_matches)<=bot.max_matches:
      return 'Found '+str(len(_matches))+' matches: '+list2str(_matches)
    else:
      return 'Found '+str(len(_matches))+' matches'

  return 'Found '+str(len(_matches))+' match: '+str(_matches[0])

def find(bot,fd,dirs):
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
  errors = []

  # find all matching directories or files depending on fd parameter
  for path in paths:
    try:
      if fd=='dir':
        contents = rlistdir(path)
      else:
        contents = rlistfiles(path)
      for entry in contents:
        result.append(entry)
    except Exception as e:
      msg = 'Unable to traverse "%s": %s' % (path,traceback.format_exc(e).split('\n')[-2])
      errors.append((path,msg))

  # same as above but for samba shares
  for path in smbpaths:
    try:
      smb = smbc.Context()
      if path['username']:
        smb.functionAuthData = lambda se,sh,w,u,p: (w,path['username'],path['password'])
      share = 'smb://'+path['server']+'/'+path['share']
      smb.opendir(share[:share.rfind('/')])
      if fd=='dir':
        contents = rsambadir(smb,share)
      else:
        contents = rsambafiles(smb,share)
      for entry in contents:
        result.append(entry)
    except Exception as e:
      msg = 'Unable to traverse "%s": %s' % (share,traceback.format_exc(e).split('\n')[-2])
      errors.append((share,msg))

  return (result,errors)
