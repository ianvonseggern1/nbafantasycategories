import time
from datetime import timedelta

import pandas as pd
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players


# Imports stats from all games from a single player for 2019-2020 season
# Returns the info in a dataframe
def playerLogToDataframe(player_id, full_name):
    p = playergamelog.PlayerGameLog(player_id, season="2019-20")
    rs = p.get_dict()["resultSets"]
    assert len(rs) == 1
    resp = rs[0]
    df = pd.DataFrame.from_records(resp["rowSet"], columns=resp["headers"])
    df["Player_Name"] = full_name
    return df


# Imports stats for all currently active players from the 2019-2020 season
def seasonDataframe():
    all_players = players.get_players()
    active_players = [p for p in all_players if p["is_active"]]
    frames = []
    for i, player in enumerate(active_players):
        frames.append(playerLogToDataframe(player["id"], player["full_name"]))
        print(f"Done with player {i} of {len(active_players)}")

        # This API doesn't like us very much...
        time.sleep(1)

    result = pd.concat(frames, ignore_index=True)
    result.to_pickle("nba_player_stats_2019_2020.zip")


if __name__ == "__main__":
    seasonDataframe()


# Returns a dataframe filtered to just the pre bubble games in the
# 2019-2020 regular season
def getRegularSeason():
    # Load
    df = pd.read_pickle("nba_player_stats_2019_2020.zip")

    # Filter out post restart in bubble
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"], format="%b %d, %Y")
    quarentineDate = pd.to_datetime("2020 4 1", format="%Y %m %d")
    df = df.loc[df["GAME_DATE"] < quarentineDate]

    df = df.astype({"PTS": int})
    df.reset_index(inplace=True)

    return df


# Adds a column with the average score of that player over the games of the prior nDays
# Also adds a column recording how many games that is
# TODO: use groupBy and rolling to get the same info much more efficently
# def addAverageOverLast(df, nDays):
#     # Returns (mean PTS, number of games) for games in interval [endDate - nDays, endDate)
#     def averageForPlayer(playerID, endDate):
#         startDate = endDate - pd.Timedelta(days=nDays)
#         games = df.loc[
#             (df["Player_ID"] == playerID)
#             & (df["GAME_DATE"] < endDate)
#             & (df["GAME_DATE"] >= startDate)
#         ]
#         return (games["PTS"].mean(), len(games))

#     averageLabel = "{}_DAY_MEAN_PTS".format(nDays)
#     countLabel = "{}_DAY_GAMES".format(nDays)

#     newValues = []
#     for i, row in df.iterrows():
#         averagePoints, numberGames = averageForPlayer(row["Player_ID"], row["GAME_DATE"])
#         newValues.append((i, averagePoints, numberGames))

#     for v in newValues:
#         i, averagePoints, numberGames = v
#         df.loc[df.index[i], averageLabel] = averagePoints
#         df.loc[df.index[i], countLabel] = numberGames

#     return newValues


def addAverageOverLast(df, nDays):
    sorted_df = df.sort_values(["Player_ID", "GAME_DATE"])

    player_ids = sorted_df["Player_ID"].unique()

    mean_label = f"PTS_MEAN_{nDays}_DAY"
    count_label = f"COUNT_{nDays}_DAY"

    frames = []
    for player in player_ids:
        player_df = sorted_df.loc[sorted_df["Player_ID"] == player][["GAME_DATE", "PTS"]]
        rolling = player_df.rolling(timedelta(days=nDays), on="GAME_DATE", closed="left")
        counts = rolling.count().rename({"PTS": count_label}, axis=1)[count_label]
        means = rolling.mean().rename({"PTS": mean_label}, axis=1)[mean_label]
        combined = pd.concat([counts, means], axis=1)
        frames.append(combined)

    return pd.concat([sorted_df, pd.concat(frames)], axis=1)


# x.groupby('Player_Name').PTS.describe()

# datatypes = {
#     'SEASON_ID': int,
# 'Player_ID': int,
# 'Game_ID': int,
# #'GAME_DATE': str,
# #'MATCHUP': str,
# #'WL': str,
# 'MIN': float,
# 'FGM': int,                 object
# 'FGA': int,                object
# 'FG_PCT':             float64
# FG3M                object
# FG3A                object
# FG3_PCT            float64
# FTM                 object
# FTA                 object
# FT_PCT             float64
# OREB                object
# DREB                object
# REB                 object
# AST                 object
# STL                 object
# BLK                 object
# TOV                 object
# PF                  object
# PTS                  int64
# PLUS_MINUS          object
# VIDEO_AVAILABLE     object
# Player_Name         object
