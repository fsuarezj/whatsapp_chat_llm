import sys
import os

def application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'Hello, World!']

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