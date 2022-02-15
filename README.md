# **Mustang Mach-E Record/Playback Utilities**

## Table of Contents

- [Overview](#overview)
- [What's new](#whats-new)
- [Requirements](#requirements)
- [Installation](#installation)
- [Running](#running)
- [State files](#state_files)
- [Debugging](#debugging)
- [Utilities](#utilities)
- [Thanks](#thanks)

<a id='overview'></a>

## Overview
The **Record** and **Playback** utilities are simple CAN bus module record and playback tools designed to test CAN bus code application code without having to connect to a physical vehicle.  **Playback** accepts input files from the **Record** and appears as a Mustang Mach-E or other vehicle responding to ISOTP-compliant Read DID requests.  **Record** is implemented on the Unified Diagnostic Services (UDS) protocol and queries the vehicle with Read DID requests (service 0x22) and outputs decoded messages and writes the state changes to output files that can be played back in the **Playback** utility.

**Record** is a state machine, dynamically changing the DIDs read from the vehicle depending on if it is idle, on a trip, or charging.  Each state has an associated JSON state file that determines how often DIDs are sampled for chagnes.

Both utilities can be configured via a YAML configuration file.  Definitions for the vehicle CAN bus modules and supported DIDs use JSON input files in most cases, some Python data structures might exist as everything is a work in progress.

**Record** runs fine connected to **Playback** via a loop-back cable (CAN0 connected to CAN1) or the vehicle OBDII port and happily logs the requested CAN bus data.  Connecting **Playback** to your vehicle may have unintended consequences and is not recommended.

<a id='whats-new'></a>
## What's new
- InfluxDB support (now with backing cache if internet connection is lost)
- YAML secrets supported
- switched to venv for Python3.10 support
- catch SIGTERM to write out cached data before exiting
- new command line options for setting the YAML and log files
- service files for running Record and/or Playback as a Linux service
- Extract utility
- added default value for read requests that timeout or error
- Geocodio reverse geocoding added
- access accurate GPS location using iPhone app

<a id='requirements'></a>
## Requirements

- Python 3.10 or later
- Python packages used include (but the list in the `setup.py` file is the definitive list of packages)

  - python-configuration
  - pyyaml
  - python-can
  - can-isotp
  - udsoncan
  - influxdb-client
  - pygeocodio

  Both **Record** and **Playback** use SocketCAN for the networking and use UDS and ISO-TP protocols on top of the SocketCAN connections.  You need to have access to both of the OBDII connector HSCAN and MSCAN buses if you wish to access all of the vehicle modules.  My hardware setup consists of:
  - Raspberry Pi 4
  - SK Pang PiCAN2 Duo CAN Bus Board For Raspberry Pi 4 With 3A SMPS (powered from OBDII port)

  Other hardware may work but your mileage will vary.

<a id='installation'></a>
## Installation
1.  Clone the repository and install the required Python packages:
```
    git clone https://github.com/sillygoose/mme-record.git
```
2.  Enable venv in the project:
```
    cd mme-record
    python3.10 -m venv .venv
    source .venv/bin/activate
```
3.  Install the required Python packages:
```
    cd mme-record
    pip3 install -e .
```
4.  Configure the YAML file
The included file `mme.yaml` is a sample configuration file that can be used with both **Record** and **Playback**.

The YAML configuration search starts in the current directory and looks in each parent directory up to your home directory for it (or just the current directory if you are not running in a user profile).  Edit `mme.yaml` to set the desired **Playback** and **Record** options as well as InfluxDB options if you wish to have **Record** save the data in an InfluxDB2 database.

If you need to switch between YAML and/or log files, use the command line to select the desired file:

```
    python3 record.py yamlfile=my_yaml.yaml logfile=my_log.log
```

You can now use a secrets file to store sensitive information like the token used to access your InfluxDB database.  The secrets file name is the same as YAML file with `_secrets` added.  For example, the default YAML file is `mme.yaml` so the default secrets file is `mme_secrets.yaml`, if you used `my_mme.yaml` for your configuration the secrets file will be `my_mme_secrets.yaml`.  The search for the secrets file will be the same as the YAML file.

#
<a id='running'></a>
## Running **Record**
I use a Tailscale client on Raspberry Pi and on the InfluxDB host so you always have a static IP.  Tailscale is an excellent WireGuard implementation and allows me to open an SSH session or write to the database server on my home network no matter where the car is.  At home I plug into a wired network or use WiFi, on the road I connect to a cell phone serving as a hotspot and nothing would work without the services provided by Tailscale.

You can run **Record** from the command line via SSH, using a VS Code remote connection, or at startup using a script.  The project has the script `run_record.sh` that can be used for this purpose to allow data collection without an SSH or other connection.

I run Ubuntu 20.04 LTS on my Raspberry Pi so the following instructions are tailored for this OS:

Start by editing the **Record** system service file with your editor:

```
% cd ~/mme-record
% nano /etc/systemd/system/mme-record.service
```

You need to fix the path names to reflect the user profile where the MME-Record project is located.  Reperat this for the playback service file if you will be running Playback unattended.

Next copy the record and playback system service files:
```
% sudo cd ~/mme-record
% sudo cp *.service /etc/systemd/system
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

All the commands for controlling the MME-Record service are:
```
sudo systemctl enable mme-record.service
sudo systemctl disable mme-record.service
sudo systemctl start mme-record.service
sudo systemctl stop mme-record.service
sudo systemctl status mme-record.service
```

#
<a id='state_files'></a>
## State files
JSON state files are used to select the DIDs read in each state, you can control when they start and how often they are repeated.

DIDs involved in state transitions should be read frequently to catch state transitions.  Other states can be read as needed, slow changing states should be read less often than rapidly changing data so nt to consume too much CAN bus bandwidth.

Here is a sample state file entry with an explanation of the fields it might contain:
```
    {
        "module": "BECM",
        "arbitration_id": 2020,
        "arbitration_id_hex": "07E4",
        "enable": true,
        "period": 5,
        "offset": 2,
        "dids": [
            {
                "did_name": "ChargingStatus",
                "did_id": 18509,
                "did_id_hex": "484D",
                "codec_id": 18509
            }
        ]
    }
```
    module                required
    arbitration_id        required
    arbitration_id_hex    optional, easier to recognize than the hexidecimal version
    enable                enables this entry, default setting is true
    period                how often this entry will be scheduled (every 5 seconds in this example)
    offset                when this entry will start, default is 0 (this example will start after two seconds has passed)

#
<a id='debugging'></a>
## Debugging
I run both **Playback** and **Record** in VS Code on a Raspberry Pi with CAN0 bus tied to the CAN1 bus in a loopback mode, makes for easy testing of **Record** changes playing back recorded files from a trip or charging session without requiring the vehicle.

#
<a id='utilities'></a>
## Utilities
### Extract
I found I needed the ability to sniff the CAN buses but this is not possible on the Mustang Mach-E as the Gateway module makes sure there is no traffic to sniff.  **Extract** is a work-around to this problem, you can use this to extract some or all the DIDs in a module and run these in **Record** to look for state changes.  Just temporarily replace the `unknown.json` with the output file of Extract and exercise the vehicle to capture state changes.

#
<a id='thanks'></a>
## Thanks

Thanks for the following packages used to build this software:

- [CAN bus on Python](https://github.com/hardbyte/python-can)
- [UDS](https://github.com/pylessard/python-udsoncan)
- [ISO-TP](https://github.com/pylessard/python-can-isotp)
- [YAML configuration file support](https://python-configuration.readthedocs.io)
- [InfluxDB Python API](https://influxdb-client.readthedocs.io/en/stable/api.html)
- [Geocodio Python API](https://github.com/bennylope/pygeocodio)
