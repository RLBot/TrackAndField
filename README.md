# RLBot Track and Field

This is a script that facilitates track and field style events
for Rocket League bots, e.g. waypoint races, shotput, etc.

It uses the [Scripts system](https://github.com/RLBot/RLBot/wiki/Scripts)
and [Matchcomms](https://github.com/RLBot/RLBot/wiki/Matchcomms).

## Usage
Track and Field relies on RLBotGUI.
1. Clone this repository
2. Open RLBotGUI, and in that interface:
   1. Add -> Load Folder
   2. Choose the folder where this code lives
   3. In the "Scripts" section, toggle on "Track and Field".
   4. If there's a yellow triangle, click it and install dependencies.
   5. Choose bots to compete, drag them on to any team.
   6. Start the match
3. Expect the match to start, and the bots to de-spawn during kickoff.
4. Follow instructions that will appear in-game.

Event progress is saved in a file at ./data/current_competition.json,
and and additional files in subfolders.
- You can resume an event by re-running the match through RLBotGUI
- If you want to start a new event, you must move or rename current_competition.json.

## Making Bots to Compete
To compete in Track and Field, a bot must support
[Matchcomms](https://github.com/RLBot/RLBot/wiki/Matchcomms), and it
also needs to understand the messages associated with each event.

Each python file in the 'events' folder has specific documentation on
the message(s) it sends and how a bot is expected to behave.

## Contributing new events to Track and Field
Pull requests are welcome!

Create a new class in the 'events' folder, as a subclass of `Event`
(see event.py). You may find it convenient to copy-paste waypoint_race.py
and modify it to create your new event.

To start using your event, modify the `get_event_list` function in
track_and_field.py.
