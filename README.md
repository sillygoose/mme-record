# **Mustang Mach-E Record/Playback Utilities**

## Table of Contents

- [Overview](#overview)
- [What's new](#whats-new)
- [Requirements](#requirements)
- [Installation](#installation)
- [Debugging](#debugging)
- [Thanks](#thanks)

<a id='overview'></a>

## Overview
The **Record** and **Playback** utilities are simple CAN bus module record and playback tools designed to test CAN bus code application code without having to connect to a physical vehicle.  **Playback** accepts input files from the **Record** and appears as a Mustang Mach-E or other vehicle responding to ISOTP-compliant Read DID requests.  **Record** is implemented on the Unified Diagnostic Services (UDS) protocol and queries the vehicle with Read DID requests (service 0x22) and outputs decoded messages and writes the state changes to output files that can be played back in the **Playback** utility.

**Record** is intended to be a state machine, dynamically changing the DIDs read from the vehicle depending on if it is idle, on a trip, or charging.  It isn't there yet but that is the direction I hope to take it.

Both utilities can be configured via a YAML configuration file.  Definitions for the vehicle CAN bus modules and supported DIDs use JSON input files in most cases, some Python data structures might exist as everything is a work in progress.

**Record** runs fine connected to **Playback** or the vehicle and happily logs the requested CAN bus data, connecting **Playback** to your vehicle may have unintended consequences and is not recommended.


<a id='whats-new'></a>
## What's new
- everything is new at this point so just basic functionality in both **Playback** and **Record**

<a id='requirements'></a>
## Requirements

- Python 3.10 or later
- Python packages used include (but the list in the `setup.py` file is the definitive list of packages)

  - python-dateutil
  - python-configuration
  - pyyaml
  - python-can
  - can-isotp

  Both **Record** and **Playback** use SocketCAN for the networking and use UDS and ISO-TP protocols on top of the SocketCAN connections.  You need to have access to the OBDII connector HSCAN and MSCAN buses if you wish to access all of the vehicle modules.  My hardware consists of:
  - Raspberry Pi 4
  - SK Pang PiCAN2 Duo CAN Bus Board For Raspberry Pi 4 With 3A SMPS

  Other hardware may work but your mileage will vary.


<a id='installation'></a>
## Installation
1.  Clone the repository and install the Python packages:

```
    git clone https://github.com/sillygoose/mache-utilities.git
    cd mache-utilities
    pip3 install -e .
```

2.  The YAML configuration search starts in the current directory and looks in each parent directory up to your home directory for it (or just the current directory if you are not running in a user profile).  Edit `mme.yaml` to set the desired **Playback** and **Record** options.

#
## Debugging
Create the environment variable MME_SIM_DEBUG and set to 1 or True to enable debug output.

This is also required if you wish to use the debugging options that automatically delete or create the database. This is nice during development but would not want to accidentally cause somthing bad to happen when in production.

I run both **Playback** and **Record** in VS Code on a Raspberry Pi with can0 bus tied to the can1 bus,

#
<a id='thanks'></a>
## Thanks

Thanks for the following packages used to build this software:

- [CAN bus on Python](https://github.com/hardbyte/python-can)
- [UDS](https://github.com/pylessard/python-udsoncan)
- [ISO-TP](https://github.com/pylessard/python-can-isotp)
- [YAML configuration file support](https://python-configuration.readthedocs.io)
