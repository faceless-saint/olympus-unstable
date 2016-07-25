#!/bin/sh
./import_modpack.py --server modpack.json
exec java -jar forge-server.jar -Xms${RAM_MIN:=1024M} -Xmx${RAM_MAX:=1024M} $@ nogui
