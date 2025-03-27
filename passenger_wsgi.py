import sys
import os

ApplicationDirectory = '.'
ApplicationName = 'app'
VirtualEnvDirectory = '.venv'
VirtualEnv = os.path.join(os.getcwd(), VirtualEnvDirectory, 'bin', 'python')
if sys.executable != VirtualEnv: os.execl(VirtualEnv, VirtualEnv, *sys.argv)
sys.path.insert(0, os.path.join(os.getcwd(), ApplicationDirectory))
#sys.path.insert(0, os.path.join(os.getcwd(), ApplicationDirectory, ApplicationName))
sys.path.insert(0, os.path.join(os.getcwd(), VirtualEnvDirectory, 'bin'))
os.chdir(os.path.join(os.getcwd(), ApplicationDirectory))
#os.environ.setdefault('DJANGO_SETTINGS_MODULE', ApplicationName + '.settings')

def app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'Hello, World!']

application = app

#from dotenv import load_dotenv
#load_dotenv()
#print(os.getenv('HOME'))
#INTERP = os.path.join(os.getenv('HOME'), 'whatsapp-chat-llm.xastrin.com/.venv/bin/python')
#if sys.executable != INTERP:
#    os.execl(INTERP, INTERP, *sys.argv)
#
#from src.app import app as application

#if __name__ == '__main__':
#    application.run() 