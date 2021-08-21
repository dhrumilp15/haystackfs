# What is self-hosting??

If you're looking for a way to host the bot on your own server or develop it locally, you're in the right place!

The bot's stack is fairly wide, but simple. It uses:
- discord.py and discord_slash: Libraries to handle communicating with Discord's API
- MongoDB: A database to store file metadata for searching
- Algolia or ElasticSearch: Search solutions with an API. The bot mainly uses this for fuzzy searching and search analytics, but this is an optional requirement.

# Local Setup

Follow these steps to setup the bot on your local machine! You'll have full access to the bot's search capabilities but you need an extra step for hosting the bot!

## Setup your environment!

The bot was developed and tested using python 3.8.8 and is deployed with 3.8.10. You can use a different python version if you'd like, but you'll have to watch for issues.

I would recommend creating a [python virtual environment](https://realpython.com/python-virtual-environments-a-primer/) for your work with the bot, but that's optional.

## Setup the project!

Clone the repo! If you're using commandline, you can use:

> git clone https://github.com/dhrumilp15/discordfs.git

Most services that help you use git (github desktop, gitKraken, etc.) have their own tutorials for cloning repos, so you should follow those.

Next, you'll want to install the libraries that make this project possible!

> python-m pip install -r requirements.txt

Depending on your setup, that command can just be:

> pip install -r requirements.txt

## Register a bot with Discord!

Head over to the [Discord Developer Portal](https://discord.com/developers/applications) to [create a bot](https://www.freecodecamp.org/news/create-a-discord-bot-with-python/).

Make a new application and [copy the token](https://www.freecodecamp.org/news/content/images/2021/06/image-122.png). We'll need it later.

Generate the link for your bot in the OAuth2 page. Make sure that you have these permissions checked:

- Bot (this is a scope)
- applications.commands (this is also a scope)
- View Channels
- Send Messages
- Manage Messages
- Embed Links
- Attach Files
- Read Message History
- Add Reactions
- Use Slash Commands

You can add this bot to your server now if you'd like, or you can do it later.

## Create the config file!

For the bot to communicate with discord, it needs secrets like the bot's token. All of the bot's secrets are stored in a `.env` file with the format outlined in `.env.template`:

```
DISCORD_TOKEN=<Insert your discord token here>
TEST_DISCORD_TOKEN=<Optional, test bot token>
GUILD_ID=<Include your server's ID here>
MONGO_ENDPOINT=<Link to MongoDB Endpoint>
MONGO_USER=<Link to MongoDB User>
MONGO_PASSWD=<Link to MongoDB Password>
DB_NAME=<`testing` or `production`>
```

## Run the bot!

Run the bot on your local machine with `python bot.py`. You should see a short message that looks like this:

```
TEST_discordfs#1696 has connected to Discord!
dhrumilp15#4369 is my owner!
Guild ids: [...]
```

Though, the bot name, owner name and guild id should be different!

With this section of the guide, you should be able to run the bot and access its capabilities with search and discord files! To have the bot continue running after you close your terminal, read the next section on deploying the bot!

# Deploying the bot (to DigitalOcean)

The bot is currently hosted on a DigitalOcean droplet. The bot has been designed to perform without stack or heap overflow for DigitalOcean's cheapest hosting option (This was a real pain to figure out, but it works!):

## Create a droplet

```
Intel CPU, regular SSD
$5 / month
1 GB / 1 CPU
25 GB SSD Disk
1000 GB Transfer
```

You'll have to [create a DigitalOcean droplet](https://docs.digitalocean.com/products/droplets/how-to/create/) before we get started with the rest of deployment. The bot currently runs on a droplet with an Ubuntu 20.04 image.

## Push your code to the droplet

Connect a terminal to your droplet, whether that's with the cloud console or SSH.

There are a few ways to push the code to the droplet, but we can use git. Run this command to clone the current `discordfs` repo:

> git clone https://github.com/dhrumilp15/discordfs.git

Create your `.env` file from the steps in local setup and ensure that the `.env` file is placed in the same directory as `bot.py`.

You can also create a [python virtual environment](https://realpython.com/python-virtual-environments-a-primer/) here.

Run the bot with this command:

> nohup python bot.py &

The `nohup` command continues running `python bot.py` even after you close the terminal.

# Teardown

## Local Development

Feel free to just use `Ctrl+C` to interrupt the bot until it exits.

## Deployed Bot

Run these commands:

> ps ax | grep bot.py

There should be a process id in the left most column that maps to `python bot.py`. Use that number for this command:

> kill <That number here>

# Setup MongoDB

We use MongoDB as a database to store metadata about files. This allows us to reduce the record size of objects in our search provider to enable fast search.

## Create a cluster with MongoDB

[Create a cluster with MongoDB](https://docs.atlas.mongodb.com/tutorial/create-new-cluster/). Depending on your usecase, you can simply use their free tier.

## Update the .env file

If you want the bot to store metadata about files, you'll have to add the MongoDB username, password and endpoint to the `.env` file.

# See you later...

That's all there is to run `discordfs` locally! Create an issue if you're having trouble with something or a PR if you'd like to contribute!

Feel free to join the [server](https://discord.gg/rp8aZSjevn) and [add the official bot to your server](https://discord.com/api/oauth2/authorize?client_id=837345172105723985&permissions=2147593280&scope=bot%20applications.commands)!