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

if __name__ == '__main__':
    lrsctrl()