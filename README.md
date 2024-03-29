# TASBot OBS Autoswitcher


## Install
### Requirements
* python3 3.11.x (tested against 3.11.7)
* poetry 
> Install poetry via pip, pipx, or your package manager. Poetry should be available in your PATH for the user running the script.
* OBS Studio with the obs-websocket plugin v5.0.0 or higher (tested against v5.0.1)

Ensure your poetry managed virtual environment is using python 3.11 by using the `poetry env use 3.11` command.

After cloning the repo, run `poetry install --no-dev` to install the dependencies into a virtual environment. 
> I personally recommend setting the config option `virtualenvs.in-project` to true so that the virtual environment is created in the project directory. This makes it easier to find and delete the virtual environment if needed. 
You can set this option by running `poetry config virtualenvs.in-project true` in the project directory, optionally with the `--global` flag to set it globally.
If you do not set this option, the virtual environment will be created in the poetry directory for your user, which is usually located in your home directory. See the [poetry documentation](https://python-poetry.org/docs/configuration/#virtualenvsin-project) for more information.
## Usage
### Running the script
Ensure that you've configured OBS, the obs-websocket plugin, and the script configuration before running the script. Script configuration is described in the [Configuration](#configuration) section.

To run the script, run `poetry run python main.py` in the project directory. This will start the script in the foreground.
### Configuration
config.py contains the configuration for the script. Currently, then configuration is a large dictionary, breaking up the configuration into the following sections: 
#### main
This section contains the main configuration for the script.
##### event
This section selects the event to use. Currently, there is only one event, `agdq2024`, but this script is intended to be extended to support other events and their donation / bid trackers in the future. 
##### env
This section is for declaring the event tracker environment to use. This should match an key at the path  `events.{event}.<env>` in the tracker config file.
#### obs
This section contains the configuration for OBS, and more specifically, the obs-websocket plugin.
##### host
The host to connect to. This should be the IP address of the machine running OBS.
##### port
The port to connect to. This should match the port configured in the obs-websocket plugin.
##### password
The password to use when connecting to the obs-websocket plugin. This should match the password configured in the obs-websocket plugin.
##### ws_update_interval_seconds
The interval, in seconds, to wait between updating the websocket connection. This should be defined as an integer.
##### sources
This is a list of strings indicating the source inputs to adjust the visibility of. This should match the names of the sources in the OBS scene. 
> Note: this will be changed in the future to pull the source names from the event tracker config.
##### scene_switching_interval_seconds
The interval, in seconds, to wait between switching scenes. This should be defined as an integer.
#### events
This section contains the configuration for the event trackers. Each event should have a key in this section, and the value should be a dictionary containing the configuration for that event. The following section describes the configuration for each event.
##### bid_client
This defines the type of API client to use for the bid tracker. Currently, the only supported value is `gdq_donation_tracker`.
##### bid_check_ttl
This defines how long TASBot OBS Autoswitcher should check the bid tracker. This should be defined as a `datetime.datetime.timedelta` object.
##### poll_interval_seconds
This defines how often TASBot OBS Autoswitcher should poll the bid tracker. This should be defined as an integer.
##### \<env>
Each event can support any number of different environments for checking a bid tracker. Each environment should have a key in the event's configuration, and the value should be a dictionary containing the configuration for that environment. This key is then specified at the path `main.env` The following section describes the configuration for each environment.
###### api_base_url
This defines the base URL for the API. This should be a string, and include any query parameters needed retrieve the data.
> In the future, this will be refactored to support multiple trackers via proper API clients.
###### bids_to_track
This is a list of dictionaries describing the bids to track. Each dictionary needs the following keys:
* `bid_id`: The ID of the bid to track. This should be an integer. This currently lines up with GDQ's donation tracker.
* `friendly_name`: Currently unused. This was originally intended to be used to help identify the bid when searching data across multiple sources. This may be removed in the future.
* `source`: The source input to adjust the visibility of when the bid is active. This should match one of the sources defined in the `obs.sources` configuration. 


## Development
### Requirements
In addition to the requirements for running the script, there are additional development requrements. Youc an install these by running `poetry install --group dev` in the project directory.
## Mock Tracker
The mock tracker is a Flask app that both serves a mock API for the script to use, and a web interface for testing the script. The mock tracker is located in the `mock_tracker` directory. It can be used both for development as well as a break-glass option in case the real tracker or internet connection is unavailable.
### Running the mock tracker
To run the mock tracker, cd into the `mock-tracker` directory and run `start_mock_tracker.sh`. This will start a mock tracker server on port 5000. 
### Overview
The mock tracker first loads save and kill persistence files from the `db` directory. The tracker does not do any schema validation, that the files are valid JSON, and that they line up with the schema for the tracker you are using. Right now, like the autoswitcher, the mock tracker is only designed to work with the GDQ donation tracker, and specifically for the workflow for TASBot's exhibition at AGDQ 2024. 

The mock tracker exposes 3 routes: 
 * `/` [**GET**] - The web interface for the mock tracker. This is a simple HTML page that displays the current state of the tracker, and allows you to modify the state of the tracker with big easy to click buttons.
 * `/save` [**GET**/**POST**] - This route exposes the API response for the "save" bid. 
    * **GET** - Returns the current state of the save bid as a JSON object.
        * URL parameters:
            * `status` - Returns the status of the "save" bid as an emoji. This is used by the web interface to display the current status of the save bid.
    * **POST** - This route updates both the save and kill endpoints so that save is ahead. This is done simply by setting the key at `.results[0].total` to 1 for the save bid, and 0 for the kill bid. This route does not accept any parameters.
 * `/kill` [**GET**/**POST**] - This route exposes the API response for the "kill" bid.
    * **GET** - Returns the current state of the kill bid as a JSON object.
        * URL parameters:
            * `status` - Returns the status of the "kill" bid as an emoji. This is used by the web interface to display the current status of the kill bid.
    * **POST** - This route updates both the save and kill endpoints so that kill is ahead. This is done simply by setting the key at `.results[0].total` to 1 for the kill bid, and 0 for the save bid. This route does not accept any parameters.

### Requirements
* python3 3.11.x (tested against 3.11.7)
* flask ^3.0.0

### Usage
To start the mock tracker, cd int the `mock-tracker` directory and run `start_mock_tracker.sh`.
This will start a mock tracker server on port 8000. This uses npx to download and run [http-server](https://www.npmjs.com/package/http-server) to serve the mock tracker files. 