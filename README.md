# Installation

Clone this repo and install the dependencies
```
pip install nba_api, click
```

# Create teams
Enter all the players on a team. These will be stored on disk locally so you don't have to enter them again.

To create a team:
```
python team.py create
```

To see what other options there are:
```
python team.py --help
```

# Model weekly category winner

```
python categories.py <team 1 name> <team 2 name>
```

To see options:
```
python categories.py --help
```
