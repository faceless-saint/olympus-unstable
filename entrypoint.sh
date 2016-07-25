#!/bin/sh
./import_modpack.py --server mods.json
exec java -jar forge-server.jar $@ nogui
