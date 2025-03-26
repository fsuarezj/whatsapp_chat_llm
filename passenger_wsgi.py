from src.app import app as application

import sys
import os
INTERP = os.path.join(os.environ['HOME'], '.venv/bin/python')
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

if __name__ == '__main__':
    application.run() 