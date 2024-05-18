import click
from lrscfg.client import Client

@click.group()
def lrscfg():
    pass

#Data run controls
@lrscfg.command()
@click.option("--tag","-t", required=True, type=str, help="Description tag")
def pull_moas(tag):
    Client().pull_moas(tag)

@lrscfg.command()
def get_latest_moas():
    print(Client().get_latest_moas())
    return Client().get_latest_moas()

@lrscfg.command()
def get_active_moas():
    print(Client().get_active_moas())
    return Client().get_active_moas()

@lrscfg.command()
@click.option("--version","-v", required=True, type=str, help="MOAS version tag ()")
def set_active_moas(version):
    Client().set_active_moas(version)