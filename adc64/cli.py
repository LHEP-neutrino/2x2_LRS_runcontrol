import click
from adc64.client import Client
from adc64 import server


@click.group()
def adc64():
    pass


@adc64.command()
def start():
    Client().send_start_adc64()

@adc64.command()
def stop():
    Client().send_stop_adc64()

@adc64.command()
def start_rc():
    Client().send_start_rc()

@adc64.command()
def stop_rc():
    Client().send_stop_rc()

@adc64.command()
def serve():
    server.start_app()
