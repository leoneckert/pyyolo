#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Use text editor to edit the script and type in valid Instagram username/password

from InstagramAPIII import InstagramAPI
import ConfigParser
config = ConfigParser.ConfigParser()
config.read("config.txt")

api = InstagramAPI(config.get("IGPYTHON", "username"), config.get("IGPYTHON", "password"))
def loginIG():
    api.login(force=True) # login
def uploadPhoto(path, caption):
    api.uploadPhoto(path, caption=caption)
