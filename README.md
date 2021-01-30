# Chinese Flash Card Exporter

Work in progress - made for my uses but maybe someone else will come across
this. If I get time I'll expand this to take command line args.

This takes a Google sheet in a specific format and generates an export you can
easily pull into Pleco. Only works in this direction.

But right now to run:

```
# google how to install the required packages... need to automate/record
python main.py
```

Reads a file from Google Drive with at least three columns - Week, Chinese, and
Pinyin. It can have more for your own uses, but they are ignored.

Run this script and it will generate `{date}_pleco_import.txt` and upload it to
your Google Drive to the `pleco` folder (you might have to create this folder
manually, I don't remember if this code handles it). Pleco can then import the
file (on Android, swipe from the left to pull open the folder view when looking
for the file, you should be able to click on your Google Drive).

Files are encoded with UTF-8. I have observed some oddities so I don't know if
this export is completely correct yet. Definitely back up your card database
still!
