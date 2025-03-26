#!/bin/bash

# Upgrade your local PIP:
python3.9 -m ensurepip --upgrade
python3.9 -m pip install --upgrade pip

# Make sure that you have your ~/.local/bin early in your path:
cat ~/.bash_profile 
export PATH=$HOME/.local/bin:$PATH
source ~/.bash_profile

echo $PATH > tmp.txt