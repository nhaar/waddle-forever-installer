#!/bin/bash

VERSION="0.2.0"
URL="https://waddleforever.com/"
CLIENT="client"
SERVER="server"
STATIC="static"
SPECIAL="special"
CLIENT_URL="$URL$CLIENT-$VERSION-linux.zip"
SERVER_URL="$URL$SERVER-$VERSION-linux.zip"
STATIC_URL="$URL$STATIC-$VERSION.zip"
SPECIAL_URL="$URL$SPECIAL-$VERSION.zip"
DEST_FOLDER="."
CLIENT_ZIP="client.zip"
SERVER_ZIP="server.zip"
STATIC_ZIP="static.zip"
SPECIAL_ZIP="special.zip"

curl -o "$CLIENT_ZIP" "$CLIENT_URL"
curl -o "$SERVER_ZIP" "$SERVER_URL"
curl -o "$STATIC_ZIP" "$STATIC_URL"
curl -o "$SPECIAL_ZIP" "$SPECIAL_URL"

unzip "$CLIENT_ZIP" -d "."
unzip "$SERVER_ZIP" -d "."

mkdir -p "media"
mkdir -p "media/static"
mkdir -p "media/special"
unzip "$STATIC_ZIP" -d "media/static"
unzip "$SPECIAL_ZIP" -d "media/special"

rm "$CLIENT_ZIP"
rm "$SERVER_ZIP"
rm "$STATIC_ZIP"
rm "$SPECIAL_ZIP"

echo "{}" > "settings.json"

echo "Installation finished! Please check details in https://waddleforever.com/linux on how to run the game."
