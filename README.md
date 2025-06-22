# flrig-external-utils
Python utilities for sending remote commands to flrig.

# AntennaPortForBand.py
It runs, in my case, presently, on a different computer than the one that connects with my Yaesu FTdx3000 Ham Radio Transceiver, but it
wouldn't *have* to. For you see, flrig can be set up to bind to localhost, or a specific IP, or to 0.0.0.0.

![image](https://github.com/user-attachments/assets/c66ce5e9-f545-42ab-9d0a-5f5751a8df7c)

Here's the backstory... I leave my station monitoring FT8 24x7, unless I feel the urge to fiddle around with something different for a 
time (which is rare, lately). My radio has 2 antennas connected to it. The DX Commander handles every band that the transceiver does,
except for 160m and 60m. But by some magical circumstance, the rain gutter and downspout on the back of my house (along with a long
counterpoise running through the grass to the far NE corner of my lot) tunes up almost perfectly on 160m, and significantly better than
the DX Commander does on 60m.

The radio itself will remember which antenna port I'd last used on each band. So if I change bands using the buttons on the radio, it
would switch to ANT 2 when I hit the "1.8" button.

WSJT-x-Improved via flrig does not remember the antenna ports. So the Band Hopping 24x7 all-bands FT8 monitor is crippled on two bands.
How do we fix this?

Step one was, as pictured a few paragraphs up, to switch flrig from 127.0.0.1 instead to 0.0.0.0.

Step two (which I'd already done almost a year prior) is to set up "Commands" buttons to select ANT 1 or ANT 2.

![image](https://github.com/user-attachments/assets/cb538cf1-f659-43c1-a3a2-6d6f4230635c)

Then, on a different computer (optionally), run this python script. At the top of every minute, plus 750ms, it polls flrig to see what
frequency is set, then selects the antenna port by activating the 1st or 2nd user-defined Command button.

This worked, but I didn't care for the non-useful noise cluttering up the terminal window. And so...

# AntennaPortForBandGUI.py

It's the same thing, plus a simple GUI...

![image](https://github.com/user-attachments/assets/7483cd61-a6f8-400c-aa4e-6a4f7332c5d8)

...that shows the Current Frequency, the Current Antenna Port, and the Last Change Timestamp.

I launch it thusly...

```$ python3 ./AntennaPortForBandGUI.py >/dev/null &```

...so that the terminal window isn't cluttered with "Unexpected response:" over and over again.

These scripts are not here because I think you'll find them particularly useful. Rather, they are here as a little example of how you
might be able to solve some problem. If you can make a "Commands" button in flrig do a thing you want, then you can make it do that thing
even from a different computer, running a different OS.
