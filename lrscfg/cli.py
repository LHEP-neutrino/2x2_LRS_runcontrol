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
@click.option("--version","-v", required=False, default=None, type=str, help="MOAS version tag (if not provided latest pulled MOAS used)")
def activate_moas(version):
    Client().activate_moas(version)
    
@lrscfg.command()
def ramp_down_sipm():
    Client().ramp_down_sipm()

def parse_modules(ctx, param, value):
    if value is None:
        return [1, 2, 3, 4]
    try:
        modules = list(int(m) for m in value.split(",") if int(m) in [1, 2, 3, 4])
        if not modules:
            raise click.BadParameter("modules must be comma-separated integers (1,2,3,4), e.g. 1,3")
        return modules
    except ValueError:
        raise click.BadParameter("modules must be comma-separated integers (1,2,3,4), e.g. 1,2,3")

@lrscfg.command()
@click.argument("direction", type=click.Choice(["up", "down"]))
@click.option("--modules", "-m", default=None, callback=parse_modules, help="Comma-separated list of modules (1,2,3,4), e.g. -m 1,2,3")
def ramp_TTI(direction, modules=None):
    """
    Ramp the TTI in the specified direction for the specified modules.

    The direction to ramp can be either 'up' or 'down'. If no module is specified, all modules will be ramped.
    """
    Client().ramp_TTI(direction, modules)

@lrscfg.command()
def get_latest_moas():
    print(Client().get_latest_moas())
    return Client().get_latest_moas()

@lrscfg.command()
def get_active_moas():
    print(Client().get_active_moas())
    return Client().get_active_moas()

@lrscfg.command()
@click.option("--entries","-n", required=False, default=None, type=int, help="Number of entries to display")
def moas_table(entries):
    """
    Display a table of MOAS configurations.
    """
    Client().moas_table(entries)

# FOAS equivalents to the MOAS commands
@lrscfg.command()
@click.option("--tag","-t", required=True, type=str, help="Description tag")
def pull_foas(tag):
    Client().pull_foas(tag)
    

@lrscfg.command()
@click.option("--version","-v", required=False, default=None, type=str, help="FOAS version tag (if not provided latest pulled FOAS used)")
def activate_foas(version):
    Client().activate_foas(version)
    

@lrscfg.command()
def get_latest_foas():
    print(Client().get_latest_foas())
    return Client().get_latest_foas()


@lrscfg.command()
def get_active_foas():
    print(Client().get_active_foas())
    return Client().get_active_foas()