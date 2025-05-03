import sys
import os

ApplicationDirectory = 'wcl'
VirtualEnvDirectory = '.venv'
VirtualEnv = os.path.join(os.getcwd(), VirtualEnvDirectory, 'bin', 'python')
if sys.executable != VirtualEnv: os.execl(VirtualEnv, VirtualEnv, *sys.argv)
sys.path.insert(0, os.path.join(os.getcwd(), ApplicationDirectory))
sys.path.insert(0, os.path.join(os.getcwd(), VirtualEnvDirectory, 'bin'))
os.chdir(os.path.join(os.getcwd(), ApplicationDirectory))
from wcl.src.app import app as application

#def app(environ, start_response):
#    start_response('200 OK', [('Content-Type', 'text/plain')])
#    return [b'Hello, World!']
#
#application = app
