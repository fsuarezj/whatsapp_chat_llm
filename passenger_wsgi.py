from dotenv import load_dotenv

import sys
import os

load_dotenv()
print(os.getenv('HOME'))
INTERP = os.path.join(os.getenv('HOME'), 'whatsapp-chat-llm.xastrin.com/.venv/bin/python')
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

from src.app import app as application

#if __name__ == '__main__':
#    application.run() 