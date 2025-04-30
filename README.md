# 2x2 LRS Run Control

The 2x2 LRS Run Control works as an interface to the AFI DAQ software and controls the system configuration (SiPM bias, VGA gain, etc.).
Further it can be used to perform automated calibration runs using the [2x2 LED Pulser](https://github.com/LHEP-neutrino/2x2PulserSoft).

The following schematic gives an overview of the functionality:
![LRS_run_control_schematic](https://github.com/user-attachments/assets/0976eb7f-01a3-451e-88ba-5763f492be06)

## Installation

### Clone repo
```
git clone https://github.com/LHEP-neutrino/2x2_LRS_runcontrol/
git checkout FSD
cd 2x2_LRS_runcontrol
```

### Update configuration file
Copy the example config file
```
cp config.yaml.example config.yaml
```

Modify the config file if needed:
- Set `AppHost` to the IP of the server the LRS control server is installed on.
- Set all directory paths. All the directories defined MUST exist (except the `lrsdetconfig.db` file).
  
### Install package
```
pip install -r requirements.txt
python3 setup.py develop
```

## Setup server
```
mkdir -p ~/.config/systemd/user/
cp lrsctrlserver.service ~/.config/systemd/user/
```
Update the file `~/.config/systemd/user/lrsctrlserver.service` with the necessary paths and username.

Enable and start the service
```
systemctl --user enable lrsctrlserver.service
systemctl --user restart lrsctrlserver.service
```
Check if server is running
```
systemctl --user status lrsctrlserver.service
```


### Check installation
To view the available commands run
```
lrsctrl
```

## Usage CLI
### LRSCTRL commands
- **serve** - run application server
- **start** - ADC64 instance start
- **start-rc** - RUN CONTROL instance start
- **stop** - ADC64 instance stop
- **stop-rc** - RUN CONTROL instance stop

To view command options use
```
--help
```
## Run 2x2 LRS Run Control server
To start the server use
```
lrsctrl serve
```
# lrsctrl REST API
## URLs
To manage lrsctrl instance you can use URL requests

**/api/start_adc64** - ADC64 instance start
```
http://159.83.34.42:5050/api/start_adc64
```

**/api/stop_adc64** - ADC64 instance stop
```
http://159.83.34.42:5050/api/stop_adc64
```

**/api/start_rc** - RUN CONTROL instance start
```
http://159.83.34.42:5050/api/start_rc
```

**/api/stop_rc** - RUN CONTROL instance stop
```
http://159.83.34.42:5050/api/stop_rc
```
