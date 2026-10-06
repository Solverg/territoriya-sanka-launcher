# Contact Fuse Drone — package for the launcher

This directory contains the distributable Contact Fuse Drone addon, not Arma 3
files. `contact-fuse-drone.zip` contains only the project's `mod.cpp` and
`addons/umcfd_main.pbo`.

The launcher fetches `mod-manifest.json` from this public GitHub folder every
time the checked mod is enabled. If the installed package receipt does not
match the manifest version and ZIP SHA-256, it verifies the new ZIP and safely
replaces the old package in the current user's launcher data folder:
`%LOCALAPPDATA%\UniversalModder\Arma3ContactFuseLauncher\mods\contact-fuse-drone`.
It does not copy content into the Arma 3, Steam, BattlEye, or save directories.

To publish a new build, create the ZIP with the same root directory and update
the semantic `version`, byte size and SHA-256 in `mod-manifest.json` in the
same commit. Do not add extracted game content, decompiled code, keys, saves,
or profiles.
