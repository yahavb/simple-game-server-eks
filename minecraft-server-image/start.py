#!/usr/bin/python
import sys
import os
import socket
import random
import subprocess
from ec2_metadata import ec2_metadata

def get_rand_port():
    print 'in get random port'
    s=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print 'socket created'
    try:
      s.bind(('',0))
    except socket.error as msg:
      print 'bind failed. Error is '+str(msg[0])+' Msg '+msg[1]
    print 'socket bind complete '
    port=s.getsockname()[1]
    s.close()
    print 'dynamic port ito start the game server is '+str(port)
    return port

if __name__ == '__main__':
  server_port=get_rand_port()
  print 'got server port '+str(server_port)
  os.environ['SERVER_PORT'] = str(server_port)
  rcon_port=get_rand_port()
  print 'got rcon server port '+str(rcon_port)
  os.environ['RCON_PORT'] = str(rcon_port)
  print 'populated the SERVER_PORT environment variable before launching the game-server'
  public_host=ec2_metadata.public_hostname
  print 'about to launch the game server '+public_host 
  subprocess.call(['/start'])
