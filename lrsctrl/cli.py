import click
from lrsctrl.client import Client
from lrsctrl import server


@click.group()
def lrsctrl():
    pass


@lrsctrl.command()
def start():
    Client().send_start_adc64()

@lrsctrl.command()
def stop():
    Client().send_stop_adc64()

@lrsctrl.command()
def start_rc():
    Client().send_start_rc()

@lrsctrl.command()
def stop_rc():
    Client().send_stop_rc()

@lrsctrl.command()
def serve():
    server.start_app()
