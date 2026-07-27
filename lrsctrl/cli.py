import click
from lrsctrl.client import Client
from lrsctrl import server


@click.group()
def lrsctrl():
    pass

#Data run controls        #####TO BE FIXED######
@lrsctrl.command()
@click.option("--run","-r", required=True, type=int, help="Run number")
@click.option("--data_stream","-d", required=True, type=str, help="Data stream (comissioning, physics)")
@click.option("--run_start_instance", "-i", required=True, type=str, help="Run start instance (lrsctrl,morcs)")
def start_data_run(run,data_stream,run_start_instance):
    Client().start_data_run(run,data_stream,run_start_instance)

@lrsctrl.command()
def stop_data_run():
    Client().stop_data_run()


#Calibration run controls
@lrsctrl.command()
def start_calib_run():
    Client().start_calib_run()

# Channel mapping run controls
@lrsctrl.command()
@click.option("--data_folder","-d", required=True, type=str, help="Data folder path")
def start_channel_map(data_folder):
    click.confirm(f"Is the MOAS activated, the DAQ in timing mode and the output folder set to {data_folder}?", abort=True)
    Client().start_channel_map(data_folder=data_folder)

#Pulser scan run controls
@lrsctrl.command()
def start_pulser_scan():
    Client().start_pulser_scan()


#Test Calibration run controls
@lrsctrl.command()
def start_test():
    Client().start_test()

#####
# NOT USED ANYMORE:
#####

# DAQ software controls
@lrsctrl.command()
def start_adc64():
    Client().send_start_adc64()

@lrsctrl.command()
def stop_adc64():
    Client().send_stop_adc64()

@lrsctrl.command()
def start_rc():
    Client().send_start_rc()

@lrsctrl.command()
def stop_rc():
    Client().send_stop_rc()
