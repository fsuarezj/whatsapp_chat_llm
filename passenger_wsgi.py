import sys
import os

ApplicationDirectory = 'whatsapp-chat-llm'
#ApplicationName = 'app'
VirtualEnvDirectory = '.venv'
VirtualEnv = os.path.join(os.getcwd(), VirtualEnvDirectory, 'bin', 'python')
if sys.executable != VirtualEnv: os.execl(VirtualEnv, VirtualEnv, *sys.argv)
sys.path.insert(0, os.path.join(os.getcwd(), ApplicationDirectory))
#sys.path.insert(0, os.path.join(os.getcwd(), ApplicationDirectory, ApplicationName))
sys.path.insert(0, os.path.join(os.getcwd(), VirtualEnvDirectory, 'bin'))
os.chdir(os.path.join(os.getcwd(), ApplicationDirectory))
#os.environ.setdefault('DJANGO_SETTINGS_MODULE', ApplicationName + '.settings')
from whatsapp-chat-llm.src.app import app as application