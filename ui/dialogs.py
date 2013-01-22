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

"""This module contains some classes for reusing dialog paradigms"""

import gtk

class HostDialog(gtk.Dialog):
  def __init__(self, parent, title, host, port, hash=None):
    gtk.Dialog.__init__(self, title, parent,
        gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
         gtk.STOCK_OK, gtk.RESPONSE_OK))

    self.table = gtk.Table(2, 2)
    self.vbox.pack_start(self.table, True, True)

    self.host_label = gtk.Label("Host:")
    self.table.attach(self.host_label, 0, 1, 0, 1, 0)

    self.host_entry = gtk.Entry()
    self.host_entry.set_text(host)
    self.table.attach(self.host_entry, 1, 2, 0, 1)

    self.port_label = gtk.Label("Port:")
    self.table.attach(self.port_label, 0, 1, 1, 2, 0)

    self.port_entry = gtk.Entry(6)
    self.port_entry.set_text(port)
    self.table.attach(self.port_entry, 1, 2, 1, 2)

    if hash is not None:
      self.table.resize(3, 2)
      self.hash_label = gtk.Label("Hash:")
      self.table.attach(self.hash_label, 0, 1, 2, 3, 0)

      self.hash_entry = gtk.Entry(40)
      self.hash_entry.set_text(hash)
      self.table.attach(self.hash_entry, 1, 2, 2, 3)
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
    return result

class ServerDialog(HostDialog):
  def __init__(self, parent, title, config, upnp):
    HostDialog.__init__(self, parent, title,
                        config.get("last", "server_bind_addr"),
                        config.get("last", "server_bind_port"),
                        config.get("last", "server_hash"))
    self.table.resize(6, 2)

    self.host_label.set_text("Bind Address:")
    self.port_label.set_text("Bind Port:")

    self.upnp_label = gtk.Label("UPnP (IGD)")
    self.table.attach(self.upnp_label, 0, 1, 3, 4, 0)

    self.upnp_check = gtk.CheckButton()
    if upnp:
      self.upnp_check.set_active(config.getboolean("last", "server_upnp"))
    else:
      self.upnp_check.set_active(False)
      self.upnp_check.set_sensitive(False)
      self.upnp_label.set_sensitive(False)
    self.upnp_check.connect("toggled", self._update_host)
    self.table.attach(self.upnp_check, 1, 2, 3, 4)

    self.host_label2 = gtk.Label("Host (external):")
    self.table.attach(self.host_label2, 0, 1, 4, 5, 0)

    self.host_entry2 = gtk.Entry()
    self.host_entry2.set_text(config.get("last", "server_host"))
    self.table.attach(self.host_entry2, 1, 2, 4, 5)

    self.port_label2 = gtk.Label("Port (external):")
    self.table.attach(self.port_label2, 0, 1, 5, 6, 0)

    self.port_entry2 = gtk.Entry()
    self.port_entry2.set_text(config.get("last", "server_port"))
    self.table.attach(self.port_entry2, 1, 2, 5, 6)

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
    return result

class GetPeersDialog(HostDialog):
  def __init__(self, parent, title, host, port, hash, scrape):
    HostDialog.__init__(self, parent, title, host, port, hash)

    self.table.resize(4, 2)

    scrape_label = gtk.Label("Scrape:")
    self.table.attach(scrape_label, 0, 1, 3, 4, 0)

    self.scrape_check = gtk.CheckButton()
    self.scrape_check.set_active(scrape)
    self.table.attach(self.scrape_check, 1, 2, 3, 4)

    self.vbox.show_all()
  def run(self):
    response = gtk.Dialog.run(self)

    if response == gtk.RESPONSE_OK:
      result = (self.host_entry.get_text(),
                int(self.port_entry.get_text()),
                self.hash_entry.get_text(),
                self.scrape_check.get_active())
    else:
      result = None
    return result

class MultipleServersDialog(gtk.Dialog):
  def __init__(self, parent, config):
    gtk.Dialog.__init__(self, "Create Multiple Servers...", parent,
        gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
        (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
         gtk.STOCK_OK, gtk.RESPONSE_OK))

    self.table = gtk.Table(6, 2)
    self.vbox.pack_start(self.table, True, True)

    self.host_label = gtk.Label("Bind Address:")
    self.table.attach(self.host_label, 0, 1, 0, 1, 0)

    self.host_entry = gtk.Entry()
    self.host_entry.set_text(config.get("last", "multiple_servers_bind_addr"))
    self.table.attach(self.host_entry, 1, 2, 0, 1)

    self.min_port_label = gtk.Label("Min Port:")
    self.table.attach(self.min_port_label, 0, 1, 1, 2, 0)

    self.min_port_entry = gtk.Entry(6)
    self.min_port_entry.set_text(config.get("last", "multiple_servers_min_port"))
    self.table.attach(self.min_port_entry, 1, 2, 1, 2)

    self.max_port_label = gtk.Label("Max Port:")
    self.table.attach(self.max_port_label, 0, 1, 2, 3, 0)

    self.max_port_entry = gtk.Entry(6)
    self.max_port_entry.set_text(config.get("last", "multiple_servers_max_port"))
    self.table.attach(self.max_port_entry, 1, 2, 2, 3)

    self.uniform_label = gtk.Label("Uniform:")
    self.table.attach(self.uniform_label, 0, 1, 3, 4)

    self.uniform_check = gtk.CheckButton()
    self.uniform_check.set_active(config.getboolean("last",
                                                    "multiple_servers_uniform"))
    self.table.attach(self.uniform_check, 1, 2, 3, 4)

    self.upnp_label = gtk.Label("UPnP (IGD):")
    self.table.attach(self.upnp_label, 0, 1, 4, 5)

    self.upnp_check = gtk.CheckButton()
    self.upnp_check.set_active(config.getboolean("last",
                                                 "multiple_servers_upnp"))
    self.upnp_check.connect("toggled", self._update_host)
    self.table.attach(self.upnp_check, 1, 2, 4, 5)

    self.serv_label = gtk.Label("Host Address:")
    self.table.attach(self.serv_label, 0, 1, 5, 6)

    self.serv_entry = gtk.Entry()
    self.serv_entry.set_text(config.get("last", "multiple_servers_serv_addr"))
    self.table.attach(self.serv_entry, 1, 2, 5, 6)

    self._update_host()
    self.vbox.show_all()

  def _update_host(self, button=None):
    self.serv_label.set_sensitive(not self.upnp_check.get_active())
    self.serv_entry.set_sensitive(not self.upnp_check.get_active())

  def run(self):
    response = gtk.Dialog.run(self)

    if response == gtk.RESPONSE_OK:
      result = (self.host_entry.get_text(),
                int(self.min_port_entry.get_text()),
                int(self.max_port_entry.get_text()),
                self.uniform_check.get_active(),
                self.upnp_check.get_active(),
                self.serv_entry.get_text())
    else:
      result = None
    return result

