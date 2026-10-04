# Канистра с топливом — package for the launcher

This directory contains the distributable Fuel Canister addon, not Arma 3
files. `fuel-canister.zip` contains only the project's `mod.cpp` and
`addons/umfc_main.pbo`.

When its checkbox is enabled and the PBO is missing, the launcher fetches this
manifest and ZIP, verifies the size, SHA-256, safe ZIP structure and expected
PBO, then installs it only under:
`%LOCALAPPDATA%\UniversalModder\Arma3ContactFuseLauncher\mods\fuel-canister`.
It never copies content into Arma 3, Steam, BattlEye, or save directories.

For a new build, preserve the `fuel-canister/` ZIP root and update the archive
and manifest together. Do not add game content, decompiled code, keys, saves,
or profiles.
