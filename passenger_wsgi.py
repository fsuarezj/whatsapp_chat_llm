import os
import sys

application_directory = os.path.dirname(os.path.abspath(__file__))
src_directory = os.path.join(application_directory, "src")
virtualenv_python = os.path.join(application_directory, ".venv", "bin", "python")

if os.path.exists(virtualenv_python) and sys.executable != virtualenv_python:
    os.execl(virtualenv_python, virtualenv_python, *sys.argv)

sys.path.insert(0, src_directory)
os.chdir(application_directory)

from dotenv import load_dotenv

load_dotenv()

from app import app as application  # noqa: E402
