# discordfs

Discord's search bar leaves much to be desired when searching for files. You can search for files with `has:file`, but you can't search **by filename** or **file content**. That's what `discordfs` aims to solve.

With `discordfs`, you can search for files in your server **by filename** with `/search [filename]`! (Searching by **file content** is coming soon!) 

Files you upload are *immediately* indexed so that you can search for files as soon as you send them.

I've gotten so many requests for the bot that I've created a form! Sign up for the bot [here](https://forms.gle/UrhqHZNQhJHSdYpW7) and join the [community](https://discord.gg/rp8aZSjevn)!
<!-- Use the last working version [here](https://discord.com/api/oauth2/authorize?client_id=837345172105723985&permissions=2147593280&scope=bot%20applications.commands). -->

<!-- The testing version of this bot was recently up but I took it down to make sure it performed as expected. -->

## Commands

I really like Discord's Slash Commands, so the bot supports older commands (Ex. `fs!all`) and slash commands (Ex. `/all`)

- `/search [filename]` : Search for a file by its filename. Check out [search options](#search-options) to narrow your search! (Also supports: `fs!fsearch`, `fs!s`, `fs!search`, `fs!fs`)
- `/all` : Display all files that the bot can access (Also supports: `fs!all`, `fs!a`)
- `/clear` : Clear all files from the index (This doesn't delete any files/messages in the actual server) (Also supports: `fs!clear`, `fs!c`)
- `/remove [filename]` : Remove the bot's access to files named `filename` (Also supports: `fs!remove`, `fs!rm`)
- `/delete [filename]` : Remove the bot's access to files named `filename` AND delete their respective messages (Also supports: `fs!delete`, `fs!del`)

## Search Options

You can narrow your search by specifying options!
- File name: Searching for files by filenames is **currently** the cool part of discordfs, so this is the only required option in the option list. (That might change in the coming weeks ;)
- File type
- Author
- Channel
- Message Content (file content coming soon!)
- After / Before / During

<!-- [Click here to add the bot to your server](https://discord.com/api/oauth2/authorize?client_id=837345172105723985&permissions=2147593280&scope=bot%20applications.commands)! -->

<!-- If you want to try out any experimental features, [click here to add the test bot to your server](https://discord.com/api/oauth2/authorize?client_id=841182898778275881&permissions=2147871808&scope=bot%20applications.commands)! -->

Plz let me know if you encounter bugs! Feel free to create an issue on this repo, message me at `dhrumilp15#4369` OR join the server: (https://discord.gg/cp6Wv3peec)!
