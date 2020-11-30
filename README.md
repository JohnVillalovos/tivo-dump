# TiVo Dump

This is a barebones Python tool for downloading all the recordings from your TiVo in one shot.

Note: Please use the [GitLab repository](https://gitlab.com/Blazin64/tivo-dump). The [GitHub repository](https://github.com/Blazin64/tivo-dump) is only a mirror.

### Usage:

Before running this tool, you need to edit the `password` and `tivo_ip` values to match your TiVo MAK (Media Access Key) and IP address. Once those edits are made, run it with `python3 tivodump.py`.

### Requirements:

* Python 3
* Python Libraries:
  * Tqdm - `pip3 install tqdm`
