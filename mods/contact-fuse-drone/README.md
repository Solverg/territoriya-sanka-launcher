# Contact Fuse Drone — package for the launcher

This directory contains the distributable Contact Fuse Drone addon, not Arma 3
files. `contact-fuse-drone.zip` contains only the project's `mod.cpp` and
`addons/umcfd_main.pbo`.

The launcher fetches `mod-manifest.json` and the ZIP from this public GitHub
folder when the checked mod is missing. It verifies the ZIP SHA-256 and its
expected layout before installing it to the current user's launcher data folder:
`%LOCALAPPDATA%\UniversalModder\Arma3ContactFuseLauncher\mods\contact-fuse-drone`.
It does not copy content into the Arma 3, Steam, BattlEye, or save directories.

To publish a new build, create the ZIP with the same root directory and update
the byte size and SHA-256 in `mod-manifest.json` in the same commit. Do not add
extracted game content, decompiled code, keys, saves, or profiles.
