import click
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.endpoints import playernextngames

from collections import Counter
from datetime import datetime, timedelta

from team import getTeam

# Raw categories to collect stats from
RAW_CATEGORIES = ["PTS", "BLK", "STL", "AST",
                  "REB", "FG3M", "FGM", "FGA", "FTM", "FTA"]
FINAL_CATEGORIES = {
    "PTS": lambda x: x["PTS"],
    "BLK": lambda x: x["BLK"],
    "STL": lambda x: x["STL"],
    "AST": lambda x: x["AST"],
    "REB": lambda x: x["REB"],
    "FG3": lambda x: x["FG3M"],
    "FG%": lambda x: x["FGM"] / x["FGA"] if x["FGA"] > 0 else 0,
    "FT%": lambda x: x["FTM"] / x["FTA"] if x["FTA"] > 0 else 0,
}
TIE_BREAK = "PTS"


# Get all games that are in the range [startDate, endDate)
# This is purely by date, time is not considered
def getFutureGames(playerID, startDate, endDate):
    p = playernextngames.PlayerNextNGames(playerID)
    rs = p.get_dict()["resultSets"]
    if len(rs) != 1:
        print("Found next n games reult set of length " +
              str(len(rs)) + " for player " + str(playerID))
    allGames = [datetime.strptime(x[1], "%b %d, %Y").date()
                for x in rs[0]["rowSet"]]
    return [day for day in allGames if day >= startDate and day < endDate]


# Returns a map of historical date to the stats for that game for the player
def getPlayerStatsMap(playerID):
    p = playergamelog.PlayerGameLog(playerID)
    rs = p.get_dict()["resultSets"]
    if len(rs) != 1:
        print("Found result set of length " + str(len(rs)))
    resp = rs[0]
    index_map = getIndexMap(resp, RAW_CATEGORIES)
    rtn = {}
    for game in resp["rowSet"]:
        data = {}
        for stat in RAW_CATEGORIES:
            data[stat] = game[index_map[stat]]
        rtn[game[3]] = data  # The 4th column is the date of the game
    return rtn


# stats: A stats map
# since: the earliest date to include (inclusive)
# average: a bool, if its true the average stats per game are returned, if its false the sum is
#
# Returns a dictonary mapping stat to average/sum stat value since sinceDate, excluding today
def aggregateStats(stats, sinceDate, average=True):
    today = datetime.now().date()
    summedStats = Counter()
    games = 0
    for dayString, dayStats in stats.items():
        day = datetime.strptime(dayString, '%b %d, %Y').date()
        if day >= sinceDate and day < today:
            games += 1
            for stat, value in dayStats.items():
                summedStats[stat] += value

    if not average:
        return summedStats

    rtn = {}
    for stat, value in summedStats.items():
        rtn[stat] = value / games
    return rtn


# Helper to process historical game data
# Returns a map of index to name of field i.e. PTS: 24
def getIndexMap(resp, fields):
    rtn = {}
    for field in fields:
        # index throws if it can't find a field
        i = resp["headers"].index(field)
        rtn[field] = i
    return rtn


# Projected stats for [startDate, endDate). Uses actual stats from start date up to today
# and projects from today forward. Also prints counts of games by player
#
# team: dictionary of player id (int) to player name (string)
# name: string name of team
# startDate: day to start projecting stats from (inclusive)
# endDate: day to projects up to (exclusive)
# priorDays: the number of prior days to average stats over to predict
# player quality
#
# TODO support midgame, currently assumes todays games haven't started yet
def printStatsForTeam(team, name, startDate, endDate, priorDays):
    click.echo(click.style("Stats for team {} (size {})".format(name.upper(), len(team)), bold=True))
    c = Counter()
    for playerID, name in team.items():
        stats = getPlayerStatsMap(playerID)
        # Add up actual performance so far in week
        actualStats = aggregateStats(stats, startDate, average=False)
        for stat, value in actualStats.items():
            c[stat] += value

        # Average performance over priorDays games and multiply by the number of remaining games
        # to predict player performance over the remainder of the week
        # Today is not listed if the game is already started so instead we check if today is listed in stats
        today = datetime.now().date()
        daysPlayedThisSeason = [datetime.strptime(dayString, '%b %d, %Y').date() for dayString in stats.keys()]
        playingToday = today in daysPlayedThisSeason and today < endDate and today >= startDate

        aggregateSince = today - timedelta(days=priorDays)
        avgStats = aggregateStats(stats, aggregateSince)
        futureGames = getFutureGames(playerID, startDate, endDate)
        if playingToday:
            futureGames += [today]
        numGamesLeft = len(futureGames)
        for stat, value in avgStats.items():
            c[stat] += value * numGamesLeft

        # Print how many games the player has played and has left in the week
        daysPlaying = [day for day in daysPlayedThisSeason if day >= startDate and day < today]
        daysPlaying += futureGames
        daysPlaying = sorted(daysPlaying)
        daysStr = ", ".join([x.strftime('%a') for x in daysPlaying])
        totalGameStr = click.style("{}".format(len(daysPlaying)), fg='green')
        gamesLeftStr = click.style("{}".format(numGamesLeft), fg='green')
        print("{} has {} games, {} left, this week ({})".format(name, totalGameStr, gamesLeftStr, daysStr))
    print("")
    final = {}
    for stat, func in FINAL_CATEGORIES.items():
        final[stat] = func(c)
    return final


def printComparison(teamA, teamB, nameA, nameB):
    countA = 0
    countB = 0
    for stat in teamA.keys():
        valA = teamA[stat]
        valB = teamB[stat]
        if valA > valB:
            countA += 1
        elif valB > valA:
            countB += 1
    winner = "tie"
    if countA > countB:
        winner = nameA
    elif countB > countA:
        winner = nameB
    elif teamA[TIE_BREAK] > teamB[TIE_BREAK]:
        winner = nameA
    elif teamB[TIE_BREAK] > teamA[TIE_BREAK]:
        winner = nameB
    winner = click.style(winner.upper(), fg='green')
    scoreString = "{} {} - {} {}".format(nameA, countA, nameB, countB)
    click.echo(click.style("Expected winner {} ({})".format(winner, scoreString), bold=True))
    for stat in teamA.keys():
        a = teamA[stat]
        b = teamB[stat]
        textA = "{:.3f}".format(a).ljust(8)
        textB = "{:.3f}".format(b)
        if a > b:
            textA = click.style(textA, fg='green')
        elif b > a:
            textB = click.style(textB, fg='green')
        click.echo("{} {} {}".format(stat, textA, textB))


@click.command()
@click.argument('name_a')
@click.argument('name_b')
@click.option('-w', '--week', default=0, type=int,
              help="Which week to compare. The current week is 0, next week is 1, etc")
@click.option('-d', '--prior-days', default=30, type=int,
              help="The number of days back to average a players stats to predict future performance")
def runComparison(name_a, name_b, week, prior_days):
    today = datetime.now().date()
    lastMonday = today - timedelta(days=today.weekday())
    startDate = lastMonday + timedelta(weeks=week)
    endDate = startDate + timedelta(days=7)

    teamA = getTeam(name_a)
    teamB = getTeam(name_b)

    statsA = printStatsForTeam(teamA, name_a, startDate, endDate, prior_days)
    statsB = printStatsForTeam(teamB, name_b, startDate, endDate, prior_days)
    printComparison(statsA, statsB, name_a, name_b)


# If you pass an argument it is treated as a dict of player id to player name, otherwise you will be prompted
if __name__ == "__main__":
    runComparison()
