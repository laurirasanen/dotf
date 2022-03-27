#!/bin/bash

dest=/home/gameserver/hlserver/tf2/tf

directiories=(
	addons/source-python/plugins/dotf
	cfg/source-python/dotf
	resource/source-python/translations/dotf
	resource/source-python/events/dotf
	sound/source-python/dotf
)

for d in "${directiories[@]}"; do
	rm -rf "${dest}/${d}"
	cp -r "${d}" "${dest}/${d}"
	chown gameserver:gameserver -R "${dest}/${d}"
done
