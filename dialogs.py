"""This module contains some classes for reusing dialog paradigms"""

import gtk

class HostDialog(gtk.Dialog):
  def __init__(self, parent, title, host, port, hash=None):
    gtk.Dialog.__init__(self, title, parent,
        gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
         gtk.STOCK_OK, gtk.RESPONSE_OK))

    table = gtk.Table(2, 2)
    self.vbox.pack_start(table, True, True)

    host_label = gtk.Label("Host:")
    table.attach(host_label, 0, 1, 0, 1, 0)

    self.host_entry = gtk.Entry()
    self.host_entry.set_text(host)
    table.attach(self.host_entry, 1, 2, 0, 1)

    port_label = gtk.Label("Port:")
    table.attach(port_label, 0, 1, 1, 2, 0)

    self.port_entry = gtk.Entry(6)
    self.port_entry.set_text(port)
    table.attach(self.port_entry, 1, 2, 1, 2)

    if hash is not None:
      table.resize(3, 2)
      hash_label = gtk.Label("Hash:")
      table.attach(hash_label, 0, 1, 2, 3, 0)

      self.hash_entry = gtk.Entry(40)
      self.hash_entry.set_text(hash)
      table.attach(self.hash_entry, 1, 2, 2, 3)
    else:
      self.hash_entry = None

    self.vbox.show_all()
  def run(self):
    response = gtk.Dialog.run(self)

    if response == gtk.RESPONSE_OK:
      if self.hash_entry is not None:
        result = (self.host_entry.get_text(),
                  int(self.port_entry.get_text()),
                  self.hash_entry.get_text())
      else:
        result = (self.host_entry.get_text(),
                  int(self.port_entry.get_text()))
    else:
      result = None
    self.destroy()
    return result
