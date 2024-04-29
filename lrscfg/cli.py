import click
from lrscfg.client import Client

@click.group()
def lrscfg():
    pass

#Data run controls
@lrscfg.command()
def pull_moas():
    Client().pull_moas()