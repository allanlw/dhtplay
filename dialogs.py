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

    self.host_label = gtk.Label("Host:")
    table.attach(self.host_label, 0, 1, 0, 1, 0)

    self.host_entry = gtk.Entry()
    self.host_entry.set_text(host)
    table.attach(self.host_entry, 1, 2, 0, 1)

    self.port_label = gtk.Label("Port:")
    table.attach(self.port_label, 0, 1, 1, 2, 0)

    self.port_entry = gtk.Entry(6)
    self.port_entry.set_text(port)
    table.attach(self.port_entry, 1, 2, 1, 2)

    if hash is not None:
      table.resize(3, 2)
      self.hash_label = gtk.Label("Hash:")
      table.attach(self.hash_label, 0, 1, 2, 3, 0)

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

class ServerDialog(HostDialog):
  def __init__(self, parent, title, config, upnp):
    HostDialog.__init__(self, parent, title,
                        config.get("last", "server_bind_addr"),
                        config.get("last", "server_bind_port"),
                        config.get("last", "server_hash"))
    table = self.vbox.get_children()[0]
    table.resize(5, 2)

    self.host_label.set_text("Bind Address:")
    self.port_label.set_text("Bind Port:")

    self.upnp_label = gtk.Label("UPnP (IGD)")
    table.attach(self.upnp_label, 0, 1, 3, 4, 0)

    self.upnp_check = gtk.CheckButton()
    if upnp:
      self.upnp_check.set_active(config.getboolean("last", "server_upnp"))
    else:
      self.upnp_check.set_active(False)
      self.upnp_check.set_sensitive(False)
      self.upnp_label.set_sensitive(False)
    self.upnp_check.connect("toggled", self._update_host)
    table.attach(self.upnp_check, 1, 2, 3, 4)

    self.host_label2 = gtk.Label("Host (external):")
    table.attach(self.host_label2, 0, 1, 4, 5, 0)

    self.host_entry2 = gtk.Entry()
    self.host_entry2.set_text(config.get("last", "server_host"))
    table.attach(self.host_entry2, 1, 2, 4, 5)

    self.port_label2 = gtk.Label("Port (external):")
    table.attach(self.port_label2, 0, 1, 5, 6, 0)

    self.port_entry2 = gtk.Entry()
    self.port_entry2.set_text(config.get("last", "server_port"))
    table.attach(self.port_entry2, 1, 2, 5, 6)

    self._update_host()
    self.vbox.show_all()

  def _update_host(self, button=None):
    self.host_label2.set_sensitive(not self.upnp_check.get_active())
    self.host_entry2.set_sensitive(not self.upnp_check.get_active())
    self.port_label2.set_sensitive(not self.upnp_check.get_active())
    self.port_entry2.set_sensitive(not self.upnp_check.get_active())

  def run(self):
    response = gtk.Dialog.run(self)

    if response == gtk.RESPONSE_OK:
      result = (self.host_entry.get_text(),
                int(self.port_entry.get_text()),
                self.hash_entry.get_text(),
                self.upnp_check.get_active(),
                self.host_entry2.get_text(),
                int(self.port_entry2.get_text()))
    else:
      result = None
    self.destroy()
    return result
