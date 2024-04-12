# 2x2 LRS Run Control
Switch to the installation directory
```
cd lrsctrl
```

## Server configuration
Open the configuration file `sample_config.yaml` located in `lrsctrl` directory. The configuration allows you to specify the entry point to the backend `AppHost` and `AppPort`. Example
```
# APP server settings
AppHost: 159.83.34.42
AppPort: 5050
```
# Install 2x2 LRS Run Control
## Command line interface
Install CLI lrsctrl
```
pip install -r requirements.txt
python3 setup.py develop
```
To view the commands use
```
lrsctrl
```
# Usage CLI
## LRSCTRL commands
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
