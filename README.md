# **Mustang Mach-E CANbus Playback Utility**

## Table of Contents

- [Overview](#overview)
- [What's new](#whats-new)
- [Requirements](#requirements)
- [Installation](#installation)
- [Debugging](#debugging)
- [Thanks](#thanks)

<a id='overview'></a>

## Overview

The **MME-Playback** is a simple CAN bus module simulator designed to test CAN bus code without having to connect to a physical vehicle. It accepts files from the **MME-Recorder** and updates the supported state variables as they were originally recorded.


<a id='whats-new'></a>

## What's new

- everything is new at this point so just basic functionality

#

<a id='requirements'></a>

### Requirements

- Python 3.10 or later
- Python packages used include (but the list in the `setup.py` file is the definitive list of packages)

  - python-dateutil
  - python-configuration
  - pyyaml
  - python-can
  - can-isotp

#

<a id='installation'></a>

## Installation

1.  Clone the **MME-Playback** repository and install the Python packages:

```
    git clone https://github.com/sillygoose/mache-simulator.git
    cd mache-simulator
    pip3 install -e .
```

2.  Rename the `example.secrets.yaml` file to `mme_secrets.yaml`, if you plan on using secrets. The `mme_secrets.yaml` file is tagged in the `.gitignore` file and will not be included in your repository but if you wish you can put `mme_secrets.yaml` in any parent directory as **MME_SIM** will start in the current directory and look in each parent directory up to your home directory for it (or just the current directory if you are not running in a user profile).

    Edit `mme.yaml` and `mme_secrets.yaml` to match the CAN bus modules you wish to connect to.


#

## Debugging

Create the environment variable MME_SIM_DEBUG and set to 1 or True to enable debug output.

This is also required if you wish to use the debugging options that automatically delete or create the database. This is nice during development but would not want to accidentally cause somthing bad to happen when in production.

#

<a id='thanks'></a>

## Thanks

Thanks for the following packages used to build this software:

- [CAN bus on Python](https://github.com/hardbyte/python-can)
- [UDS](https://github.com/pylessard/python-udsoncan)
- [ISO-TP](https://github.com/pylessard/python-can-isotp)
- [YAML configuration file support](https://python-configuration.readthedocs.io)
