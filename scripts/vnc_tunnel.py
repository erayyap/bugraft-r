#!/usr/bin/env python3
"""Loopback VNC tunnel through Docker exec; unaffected by host VPN routes."""
import socketserver,subprocess,threading,argparse
CONTAINER='bugcraft-windows'
REMOTE='''import socket,sys,threading
s=socket.create_connection(('127.0.0.1',5900),10)
def send():
 try:
  while True:
   b=sys.stdin.buffer.read1(65536)
   if not b:break
   s.sendall(b)
 finally:
  try:s.shutdown(socket.SHUT_WR)
  except OSError:pass
threading.Thread(target=send,daemon=True).start()
while True:
 b=s.recv(65536)
 if not b:break
 sys.stdout.buffer.write(b);sys.stdout.buffer.flush()
'''
class Handler(socketserver.BaseRequestHandler):
 def handle(self):
  p=subprocess.Popen(['docker','exec','-i',CONTAINER,'python3','-u','-c',REMOTE],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
  def send():
   try:
    while True:
     b=self.request.recv(65536)
     if not b:break
     p.stdin.write(b);p.stdin.flush()
   except (OSError,BrokenPipeError):pass
   finally:
    try:p.stdin.close()
    except OSError:pass
  threading.Thread(target=send,daemon=True).start()
  try:
   while True:
    b=p.stdout.read1(65536)
    if not b:break
    self.request.sendall(b)
  except OSError:pass
  finally:
   p.terminate()
   try:p.wait(timeout=3)
   except subprocess.TimeoutExpired:p.kill();p.wait()
class Server(socketserver.ThreadingTCPServer):
 allow_reuse_address=True
 daemon_threads=True
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--container',default='bugcraft-windows');parser.add_argument('--port',type=int,default=5901);args=parser.parse_args()
 if args.container not in ('bugcraft-windows','bugcraft-windows-2','bugcraft-windows-3','bugcraft-windows-4'):raise ValueError('Unknown benchmark container')
 CONTAINER=args.container
 with Server(('127.0.0.1',args.port),Handler) as server:server.serve_forever()
