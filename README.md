# Discord-Payment-Bot

### discord bot control:
https://discord.com/developers/applications/1187756421807353867/bot

### discord text formatting:
https://www.writebots.com/discord-text-formatting/
https://support.discord.com/hc/en-us/articles/210298617-Markdown-Text-101-Chat-Formatting-Bold-Italic-Underline-#h_01GY0EQVRRRB2F19HXC2BA30FG

### discord.py documentation:
https://discordpy.readthedocs.io/en/stable/index.html

### discord-ui documentation:
https://discord-ui.readthedocs.io/en/latest/usage.html

### discord bot introduction:
https://hackmd.io/@smallshawn95/python_discord_bot_base
https://hackmd.io/@smallshawn95/python_discord_bot_event?utm_source=preview-mode&utm_medium=rec

### Quick install packages: 
> pip install -r requirements.txt

- ctrl shift +/- -> expand/fold everything
- ctrl D -> dulplicate current line

```
if str(client.user.id) in message.content:
     await message.channel.send('You mentioned me!')
```



Test conditions:
```
pm jaga owe ppl1 100
=> jaga needs to pay ppl1: 100.0

pm ppl1 owe jaga 100
=> ppl1 needs to pay jaga: 100.0

pm ppl1 owe ppl2 100
=> ppl1 needs to pay jaga: 100.0
=> jaga needs to pay ppl2: 100.0

pm jaga,ppl1 owe ppl2 100
=> jaga needs to pay ppl2: 100.0
=>
=> ppl1 needs to pay jaga: 100.0
=> jaga needs to pay ppl2: 100.0 -> 200.0

pm ppl1,ppl2 owe jaga 100
=> ppl1 needs to pay jaga: 100.0
=>
=> ppl2 needs to pay jaga: 100.0

pm ppl1,ppl2 owe ppl3 100
=> ppl1 needs to pay jaga: 100.0
=> jaga needs to pay ppl3: 100.0
=>
=> ppl2 needs to pay jaga: 100.0
=> jaga needs to pay ppl3: 100.0 -> 200.0
```