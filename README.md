# Discordfs

Discord's search bar leaves much to be desired when searching for files. Sure, you can search for files with `has:file`, but you can't search **by filename** or **file content**. That's what `discordfs` aims to solve.

With `discordfs`, you can search for files **by filename** with a simple command: `/search [filename]`!

Files you upload are *immediately* indexed so that you can search for files as soon as you send them.

[**Click here to add the bot to your server**](https://discord.com/api/oauth2/authorize?client_id=837345172105723985&permissions=2147593280&scope=bot%20applications.commands) and [**click here to join the community**](https://discord.gg/rp8aZSjevn).

Check out our site [here](https://typedream.site/discordfs)!

**Check out the [self-hosting guide](docs/SELF_HOSTING_GUIDE.md) if you'd like to use the bot locally!**

## Commands

The bot supports supports slash commands! You can also use classic commands with `fs!` (Ex. `fs!all`).

- `/search [filename]` : Search for a file by its filename. Check out [search options](#search-options) to narrow your search! (Also supports: `fs!fsearch`, `fs!s`, `fs!search`, `fs!fs`)
- `/remove [filename]` : Remove the bot's access to files named `filename` (Also supports: `fs!remove`, `fs!rm`)
- `/delete [filename]` : Remove the bot's access to files named `filename` AND delete their respective messages (Also supports: `fs!delete`, `fs!del`)

## Search Options

You can narrow your search by specifying options!
- File name: Searching for files by filenames is **currently** the cool part of discordfs, so this is the only required option in the option list.
- File type
- Author
- Channel
- Message Content (file content coming soon!)
- After / Before / During

# FAQ

<details open>
  <summary> Will I be able to search for files uploaded before the bot is added to the server? </summary>
    <b>YES!</b> You should experience little to no delay between response times for files uploaded before vs. after the bot is added to a server.
</details>

<details open>
  <summary> Will my files be shared with other servers? </summary>
    <b>Nope!</b> Servers can only access content in itself, so your files will never be shared with other servers.
</details>

Plz let me know if you encounter bugs! Feel free to create an issue on this repo, message me at `dhrumilp15#4369` OR post in the server: (https://discord.gg/cp6Wv3peec)!
