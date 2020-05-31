DHTPlay
=======

**NOTE: This python code is from ~2011 and is not maintained. It might be of interest to some, but use at your own risk.**

DHTPlay is an application for walking/exploring the Bittorrent DHT. 
Simply clone and run ./dhtplay to try it out.

Note this program only lets you browse the bittorrent DHT, which only contains *info hashes* of torrents. There is no way to browse the bittorrent DHT in such a way that you can actually retrieve the information about the torrents, unless you also implement the actual bittorrent protocol including the extension for transmitting torrents in-band. Right now you can get a magnet link only.

Running
-------
To run DHTPlay, you will need the python gtk2 (pygtk) 
library and the python gupnp idg library. In debian/ubuntu, these are 
available as python-gtk2 and python-gupnp-igd, respectively.

The "new server" button creates a new DHT Server. If you install python-gupnp-igd (this is the name of the package in debian/ubuntu at least) the UPnP check box will be available and this will be a lot easier for you.

Alternatively, if you want to forward the port manually, I believe the correct settings are:

    Bind Address: 0.0.0.0
    Bind Port: 12345
    Hash: <whatever>
    External Addr: <your external IP>
    External Port: 12345

Essentially, the external address+port are used to tell other DHT nodes what your address is. The bind address+bind port are used locally to create the listening port on your own computer. When you're behind a NAT (like you are) the external address and the bind address have to be different. "0.0.0.0" essentially says - listen on all interfaces.

After you make a server, you need to connect to the dht network by adding peers. From there, you can look around.


Notes on design
---------------
  As of the time of writing this, DHTPlay uses three threads of control at any
given time. The first is the main thread of control that is started by the
python interpreter which enters a gtk main loop after doing a bit of
initialization. The second is a thread that is bootstrapped by the main thread
that I call the 'server wrangler'. This thread polls the server sockets and 
notifies the server threads when they have received new packets. It also
spawns the new server threads that are created for each DHT server. There is
also a thread that is used for dispatching queries to the SQLite Database.
Some of the methods of this thread are for syncronous access and some are for
async access. This thread is used because sqlite connections cannot be shared
across threads and because I wasn't interested in making an implimentation that
used locks. In order for the server threads/server wrangler thread to
communicate with the gui thread the glib.idle_add function is used. When the
GUI thread needs to communicate with the server thread a special udp message
is sent to the server.

To recap - Threads:
  - 1 Main Thread (GTK/GDK ui thread (can be locked using gtk.gdk.lock))
  - 1 Server Wrangler thread (polls file descriptors to check for packets)
  - 1 SQLite Thread (holds sqlite cursor and connection, has query functions)
  - x DHT Server threads (one for each server)

Documents that this program aims to impliment:
  - BEP_0005 (DHT Protocol): http://www.bittorrent.org/beps/bep_0005.html
  - BEP_0033 (DHT Scrapes): http://www.bittorrent.org/beps/bep_0033.html
  - "Minor Extensions to the Bitorrent DHT": http://www.pps.jussieu.fr/~jch/software/bittorrent/bep-dht-minor-extensions.html
  - The undocumented 'v' version extension that uTorrent and rTorrent impliment in addition to other clients. Note: there is a bit about the version key here - http://www.rasterbar.com/products/libtorrent/dht_extensions.html

Contact
-------
For bug reports, patches, questions, etc. feel free to send me an email 
at allan@allanwirth.com.

Copyright notes
--------------
The file util/bencode.py is not under the same license as the other 
files. It was previously released in 2011 as FreeBencode and is licensed 
under the MIT/Expat license.

The Magnet Icon is sourced from 
http://commons.wikimedia.org/wiki/File:Magnet-icon.gif. It is listed as 
No Rights Reserved.

All other files are licensed under the GPLv3+. See COPYING for license 
details.
