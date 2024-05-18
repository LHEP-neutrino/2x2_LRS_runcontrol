import click
from lrsctrl.client import Client
from lrsctrl import server


@click.group()
def lrsctrl():
    pass

#Data run controls
@lrsctrl.command()
@click.option("--run", required=True, type=int, help="Run number")
@click.option("--data_stream", required=True, type=str, help="Data stream (comissioning, physics)")
def start_data_run(run,data_stream):
    Client().start_data_run(run,data_stream)

@lrsctrl.command()
def stop_data_run():
    Client().stop_data_run()


#Calibration run controls
@lrsctrl.command()
def start_calib_run():
    Client().start_calib_run()

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
