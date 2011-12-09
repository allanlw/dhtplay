#!/usr/bin/python
"""Contains a function start() that starts DHTPlay."""

import gtk

from ui.interface import Interface
import defaults

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
