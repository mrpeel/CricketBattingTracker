#!/bin/bash
mkdir -p app/src/main/res/mipmap-mdpi app/src/main/res/mipmap-hdpi app/src/main/res/mipmap-xhdpi app/src/main/res/mipmap-xxhdpi app/src/main/res/mipmap-xxxhdpi
mkdir -p wear/src/main/res/mipmap-mdpi wear/src/main/res/mipmap-hdpi wear/src/main/res/mipmap-xhdpi wear/src/main/res/mipmap-xxhdpi wear/src/main/res/mipmap-xxxhdpi

sips -z 48 48 icon.png --out app/src/main/res/mipmap-mdpi/ic_launcher.png
sips -z 72 72 icon.png --out app/src/main/res/mipmap-hdpi/ic_launcher.png
sips -z 96 96 icon.png --out app/src/main/res/mipmap-xhdpi/ic_launcher.png
sips -z 144 144 icon.png --out app/src/main/res/mipmap-xxhdpi/ic_launcher.png
sips -z 192 192 icon.png --out app/src/main/res/mipmap-xxxhdpi/ic_launcher.png

# Copy to wear app
cp app/src/main/res/mipmap-*/ic_launcher.png wear/src/main/res/mipmap-*/
for d in wear/src/main/res/mipmap-*; do cp app/src/main/res/${d#wear/src/main/res/}/ic_launcher.png $d/ic_launcher.png; done

# Replace round icons (Wear OS uses round by default, we'll just make them the same since the SVG is squircle)
for d in app/src/main/res/mipmap-*; do cp $d/ic_launcher.png $d/ic_launcher_round.png; done
for d in wear/src/main/res/mipmap-*; do cp $d/ic_launcher.png $d/ic_launcher_round.png; done

