#!/bin/bash
mkdir -p "$HOME/.config"
if [ -d "$PWD/.devcontainer/config" ]; then
	rsync -a --ignore-existing "$PWD/.devcontainer/config/" "$HOME/.config/"
else
	echo "skipping copy of devcontainer config"
fi
set +x
