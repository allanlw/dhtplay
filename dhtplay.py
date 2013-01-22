#!/usr/bin/python
# Copyright (c) 2011-2013 Allan Wirth <allan@allanwirth.com>
#
# This file is part of DHTPlay.
#
# DHTPlay is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Contains a function start() that starts DHTPlay."""

import gtk

from ui.interface import Interface
from util import defaults

settings = "settings.cfg"

def start():
  """Start DHTPlay."""
  config = defaults.DEFAULT_CONFIG
  config.read(settings)

  gtk.gdk.threads_init()
  app = Interface(config)
  app.show()
  gtk.main()

  try:
    app.destroy()
  except:
    pass

  config.write(open(settings, 'w'))

if __name__ == "__main__":
  start()
