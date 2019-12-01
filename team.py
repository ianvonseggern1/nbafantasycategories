import click
from nba_api.stats.static import players

import ast
import json
from os import path, mkdir


@click.group()
def team():
    pass


@team.command()
@click.argument('name')
def show(name):
    team = getTeam(name)
    for player in team.values():
        print(player)


@team.command()
def create():
    """ Enter the names of all players on a team to create a team """
    team = promptForPlayers()
    if len(team) == 0:
        return

    name = click.prompt(
        "Enter a name for this team (q to quit without saving)")
    if name.lower() == "q":
        return

    saveTeam(name, team)


@team.command()
@click.argument('name')
@click.option('--include-inactive', is_flag=True, default=False)
def add_players(name, include_inactive):
    print("CURRENT TEAM:")
    team = getTeam(name)
    for player in team.values():
        print(player)
    newPlayers = promptForPlayers(includeInactive=include_inactive)
    team.update(newPlayers)
    saveTeam(name, team, force_overwrite=True)


@team.command()
@click.argument('name')
def remove_players(name):
    team = getTeam(name)
    playerList = list(team.items())

    while True:
        print("CURRENT TEAM:")
        for i, player in enumerate(playerList):
            print("{} {}".format(i, player))
        i = click.prompt("Enter index of player to remove (q to quit)")
        if i.lower() == "q":
            break
        i = int(i)
        playerList.pop(i)

    newTeam = dict(playerList)
    saveTeam(name, newTeam, force_overwrite=True)


def promptForPlayers(includeInactive=False):
    allPlayers = players.get_players()
    rtn = {}
    while True:
        name = click.prompt("Enter player name (q to quit)")
        if name.lower() == "q":
            return rtn
        candidates = [p for p in allPlayers if p['full_name'].lower().count(
            name.lower()) > 0 and (includeInactive or p['is_active'])]
        if len(candidates) == 1:
            if not click.confirm("Add {}?".format(candidates[0]['full_name']), default=True):
                continue
            rtn[candidates[0]['id']] = candidates[0]['full_name']
        elif len(candidates) > 1:
            candidate_str = ["{}: {}".format(
                i, p['full_name']) for i, p in enumerate(candidates)]
            i = click.prompt(
                "Too many players of that name {}. Enter index of player to add (S to skip)".format(candidate_str))
            if i.lower() == "s":
                continue
            i = int(i)
            rtn[candidates[i]['id']] = candidates[i]['full_name']
        else:
            print("No one by that name found")


def getTeam(name):
    importPath = path.join(path.expanduser("~"), ".nbafantasy", name)
    if not path.exists(importPath):
        raise Exception("{} is not a known team name".format(name))
    with open(importPath) as f:
        return ast.literal_eval(f.read())


def saveTeam(name, team, force_overwrite=False):
    saveDir = path.join(path.expanduser("~"), ".nbafantasy")
    if not path.exists(saveDir):
        mkdir(saveDir)

    savePath = path.join(saveDir, name)
    if not force_overwrite and path.exists(savePath):
        if not click.confirm("Do you want to overwrite the existing team {}".format(name), default=True):
            return

    with open(savePath, "w") as f:
        f.write(json.dumps(team))


if __name__ == "__main__":
    team()
