# **Mustang Mach-E Record/Playback Utilities**

## Table of Contents

- [Overview](#overview)
- [What's new](#whats-new)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running](#running)
- [Debugging](#debugging)
- [Thanks](#thanks)

<a id='overview'></a>

## Overview
The **Record** and **Playback** utilities are simple CAN bus module record and playback tools designed to test CAN bus code application code without having to connect to a physical vehicle.  **Playback** accepts input files from the **Record** and appears as a Mustang Mach-E or other vehicle responding to ISOTP-compliant Read DID requests.  **Record** is implemented on the Unified Diagnostic Services (UDS) protocol and queries the vehicle with Read DID requests (service 0x22) and outputs decoded messages and writes the state changes to output files that can be played back in the **Playback** utility.

**Record** is a state machine, dynamically changing the DIDs read from the vehicle depending on if it is idle, on a trip, or charging.

Both utilities can be configured via a YAML configuration file.  Definitions for the vehicle CAN bus modules and supported DIDs use JSON input files in most cases, some Python data structures might exist as everything is a work in progress.

**Record** runs fine connected to **Playback** via a loop-back cable (CAN0 connected to CAN1) or the vehicle OBDII port and happily logs the requested CAN bus data.  Connecting **Playback** to your vehicle may have unintended consequences and is not recommended.


<a id='whats-new'></a>
## What's new
- everything is new at this point so just basic functionality in both **Playback** and **Record**

<a id='requirements'></a>
## Requirements

- Python 3.10 or later
- Python packages used include (but the list in the `setup.py` file is the definitive list of packages)

  - python-configuration
  - pyyaml
  - python-can
  - can-isotp
  - udsoncan

  Both **Record** and **Playback** use SocketCAN for the networking and use UDS and ISO-TP protocols on top of the SocketCAN connections.  You need to have access to both of the OBDII connector HSCAN and MSCAN buses if you wish to access all of the vehicle modules.  My hardware setup consists of:
  - Raspberry Pi 4
  - SK Pang PiCAN2 Duo CAN Bus Board For Raspberry Pi 4 With 3A SMPS (powered from OBDII port)

  Other hardware may work but your mileage will vary.


<a id='installation'></a>
## Installation
1.  Clone the repository and install the Python packages:

```
    git clone https://github.com/sillygoose/mache-record.git
    cd mache-record
    pip3 install -e .
```

2.  The YAML configuration search starts in the current directory and looks in each parent directory up to your home directory for it (or just the current directory if you are not running in a user profile).  Edit `mme.yaml` to set the desired **Playback** and **Record** options.

#
<a id='running'></a>
## Running **Record**
You can run **Record** from the command line via SSH, using a VS Code remote connection, or at startup using a script.  Using a script is the most useful since no internet connection is needed, the project has the script `run_record.sh` that can be used for this purpose.

I run Ubuntu 20.04 LTS on my Raspberry Pi so the following instructions are tailored for this OS:

Start by creating a system service file with your editor:

```
% sudo nano /etc/systemd/system/mme-record.service
```
and add the following text with edits to the `ExecStart`, `User`, and `WorkingDirectory` entries to relect your system setup:
```
[Unit]
Description=MME Record
After=multi-user.target
After=network.service
[Service]
Type=simple
ExecStart=/home/sillygoose/mme-record/run_record.sh
User=sillygoose
WorkingDirectory=/home/sillygoose/mme-record/source
Restart=on-failure
[Install]
WantedBy=multi-user.target
```
Enable and start the service with
```
% sudo systemctl enable mme-record.service
% sudo systemctl start mme-record.service
```
You can check if it running by using the command line
```
% sudo systemctl status mme-record.service
```
You should see something simiar to this:
```
% sudo systemctl status mme-record.service
● mme-record.service - MME Record
     Loaded: loaded (/etc/systemd/system/mme-record.service; enabled; vendor preset: enabled)
     Active: active (running) since Thu 2022-01-13 11:07:31 EST; 4min 20s ago
   Main PID: 12806 (run_record.sh)
      Tasks: 6 (limit: 9257)
     CGroup: /system.slice/mme-record.service
             ├─12806 /bin/bash /home/sillygoose/mme-record/run_record.sh
             └─12809 /home/sillygoose/.pyenv/versions/3.10.1/bin/python3 /home/sillygoose/mache-simulator/source/record.py

Jan 13 11:07:31 greta systemd[1]: Started MME Record.
Jan 13 11:07:32 greta run_record.sh[12809]: [2022-01-13 11:07:32,271] [logfiles] [INFO] Created application log /home/sillygoose/mme-record>
Jan 13 11:07:32 greta run_record.sh[12809]: [2022-01-13 11:07:32,305] [record] [INFO] Mustang Mach E Record Utility version 0.6.0
Jan 13 11:07:32 greta run_record.sh[12809]: [2022-01-13 11:07:32,339] [state_manager] [INFO] Vehicle state changed to 'Unknown'
Jan 13 11:07:32 greta run_record.sh[12809]: [2022-01-13 11:07:32,558] [state_manager] [INFO] Vehicle state changed to 'On'
Jan 13 11:10:48 greta run_record.sh[12809]: [2022-01-13 11:10:48,298] [state_manager] [INFO] Vehicle state changed to 'Trip'
```
Now reboot and reconnect to a terminal and check that **Record** is running:
```
% sudo systemctl status mme-record.service
```
If you don't want **Record** to run automatically, disable the service and reboot, you can always use the start and stop commands from a terminal to control if **Record** runs in the background.

Other commands for controlling the new service are:
```
sudo systemctl enable mme-record.service
sudo systemctl disable mme-record.service
sudo systemctl start mme-record.service
sudo systemctl stop mme-record.service
sudo systemctl status mme-record.service
```

#
<a id='debugging'></a>
## Debugging
Create the environment variable MME_SIM_DEBUG and set to 1 or True to enable debug output.

I run both **Playback** and **Record** in VS Code on a Raspberry Pi with CAN0 bus tied to the CAN1 bus in a loopback mode, makes for easy testing of **Record** changes playing back recorded files from a trip or chnaging session.

#
<a id='thanks'></a>
## Thanks

Thanks for the following packages used to build this software:

- [CAN bus on Python](https://github.com/hardbyte/python-can)
- [UDS](https://github.com/pylessard/python-udsoncan)
- [ISO-TP](https://github.com/pylessard/python-can-isotp)
- [YAML configuration file support](https://python-configuration.readthedocs.io)
