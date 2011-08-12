# This module contains the main interface for DHTPlay

import gtk
import glib
import gobject
import threading
import time

from net.server import DHTServer
from ui import dialogs
from ui import dbview
from net.contactinfo import ContactInfo
from net.sha1hash import Hash
from ui.statuslabel import StatusLabel
from version import name, version
from net import upnp

class Interface(gtk.Window):
  def __init__(self, opts):
    gtk.Window.__init__(self)
    self.connect("delete-event", self._cleanup)
    self.set_title("{0} {1}".format(name, version))

    self.cfg = opts
    self.server_thread = None
    self.server = None
    self.upnp = None

    self.started_only = gtk.ActionGroup("started_only")
    self.stopped_only = gtk.ActionGroup("stopped_only")

    vbox = gtk.VBox()
    self.add(vbox)

    # Actions

    start_action = gtk.Action("start", "Start Server...",
                              "Start the DHT Server", gtk.STOCK_CONNECT)
    start_action.connect("activate", self.start_server)
    self.stopped_only.add_action(start_action)

    stop_action = gtk.Action("stop", "Stop Server",
                             "Stop the DHT Server", gtk.STOCK_DISCONNECT)
    stop_action.connect("activate", self.stop_server)
    self.started_only.add_action(stop_action)

    quit_action = gtk.Action("quit", "Quit",
                             "Quit", gtk.STOCK_QUIT)
    quit_action.connect("activate", self.quit)

    ping_action = gtk.Action("ping", "Ping Node...",
                             "Ping a DHT Node", gtk.STOCK_REFRESH)
    ping_action.connect("activate", self.ping_node)
    self.started_only.add_action(ping_action)

    find_action = gtk.Action("find", "Find Node...",
                             "Find a DHT Node", gtk.STOCK_FIND)
    find_action.connect("activate", self.find_node)
    self.started_only.add_action(find_action)

    get_peers_action = gtk.Action("get_peers", "Get Peers...",
                                  "Get DHT Peers", gtk.STOCK_FIND)
    get_peers_action.connect("activate", self.get_peers)
    self.started_only.add_action(get_peers_action)

    load_action = gtk.Action("load", "Load From Torrent...",
                             "Load DHT Nodes from a torrent file",
                             gtk.STOCK_OPEN)
    load_action.connect("activate", self.load_torrent)
    self.started_only.add_action(load_action)

    # Menus

    menubar = gtk.MenuBar()
    vbox.pack_start(menubar, False, False)

    file_menuitem = gtk.MenuItem("File")
    menubar.add(file_menuitem)

    file_menu = gtk.Menu()
    file_menuitem.set_submenu(file_menu)

    file_menu.add(start_action.create_menu_item())
    file_menu.add(stop_action.create_menu_item())
    file_menu.add(gtk.SeparatorMenuItem())
    file_menu.add(quit_action.create_menu_item())

    tools_menuitem = gtk.MenuItem("Tools")
    menubar.add(tools_menuitem)

    tools_menu = gtk.Menu()
    tools_menuitem.set_submenu(tools_menu)

    tools_menu.add(ping_action.create_menu_item())
    tools_menu.add(find_action.create_menu_item())
    tools_menu.add(get_peers_action.create_menu_item())
    tools_menu.add(load_action.create_menu_item())

    # Toolbar

    toolbar = gtk.Toolbar()
    vbox.pack_start(toolbar, False, False)

    toolbar.add(start_action.create_tool_item())
    toolbar.add(stop_action.create_tool_item())
    toolbar.add(ping_action.create_tool_item())
    toolbar.add(find_action.create_tool_item())
    toolbar.add(get_peers_action.create_tool_item())
    toolbar.add(load_action.create_tool_item())

    # Work area

    self.notebook = gtk.Notebook()
    vbox.pack_start(self.notebook, True, True)

    self.bucketview = dbview.BucketView()

    self.nodeview = dbview.NodeView(self.bucketview)
    self.nodeview.connect("right-click", self._do_nodeview_right_click)

    self.peerview = dbview.PeerView()

    self.torrentview = dbview.TorrentView()

    self.bucketnodeview = dbview.BucketNodeView(self.bucketview,
                                                self.nodeview)
    self.bucketnodeview.connect("right-click", self._do_nodeview_right_click)

    self.torrentpeerview = dbview.TorrentPeerView(self.torrentview,
                                                  self.peerview)
    self.peertorrentview = dbview.PeerTorrentView(self.peerview,
                                                  self.torrentview)

    self.notebook.append_page(self.nodeview, gtk.Label("Nodes"))

    bucketspane = gtk.VPaned()
    self.notebook.append_page(bucketspane, gtk.Label("Buckets"))

    bucketspane.pack1(self.bucketview, True, True)
    bucketspane.pack2(self.bucketnodeview, True, True)

    torrentspane = gtk.VPaned()
    self.notebook.append_page(torrentspane, gtk.Label("Torrents"))

    torrentspane.pack1(self.torrentview, True, True)
    torrentspane.pack2(self.torrentpeerview, True, True)

    peerspane = gtk.VPaned()
    self.notebook.append_page(peerspane, gtk.Label("Peers"))

    peerspane.pack1(self.peerview, True, True)
    peerspane.pack2(self.peertorrentview, True, True)

    logwin = gtk.ScrolledWindow()
    logwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    self.notebook.append_page(logwin, gtk.Label("Log"))

    self.logbuffer = gtk.TextBuffer()
    self.logview = gtk.TextView(self.logbuffer)
    self.logview.set_wrap_mode(gtk.WRAP_NONE)
    self.logview.set_editable(True)
    self.logview.set_cursor_visible(False)
    logwin.add(self.logview)

    self.statusbar = gtk.Statusbar()
    vbox.pack_end(self.statusbar, False, False)

    self.serverstatus = StatusLabel("Server:", False)
    self.statusbar.pack_start(self.serverstatus, False, False)

    self.statusbar.pack_start(gtk.VSeparator(), False, False)

    self.netstatus = StatusLabel("Network:")
    self.statusbar.pack_start(self.netstatus, False, False)

    self.started_only.set_sensitive(False)

    self.show_all()
    self.hide()

    self._do_log("Application Initiated.")

  def quit(self, widget=None, event=None):
    self._cleanup()

  def _cleanup(self, widget=None, event=None):
    if self.server:
      self.stop_server()
    if self.upnp:
      self.upnp.shutdown()
    gtk.main_iteration(False)
    gtk.main_quit()

  def startstop_server(self, widget=None):
    if self.server == None:
      self.start_server()
    else:
      self.stop_server()

  def start_server(self, widget=None):
    host = self.cfg.get("last", "server_host")
    port = self.cfg.get("last", "server_port")
    hash = self.cfg.get("last", "server_hash")

    dialog = dialogs.ServerDialog(self, "Start Server...", self.cfg,
                                  upnp.HAVE_UPNP)

    response = dialog.run()
    dialog.destroy()
    if response is not None:
      bind_addr, bind_port, hash, use_upnp, host, port = response

      self.cfg.set("last", "server_host", host)
      self.cfg.set("last", "server_port", str(port))
      self.cfg.set("last", "server_hash", hash)
      self.cfg.set("last", "server_bind_addr", bind_addr)
      self.cfg.set("last", "server_bind_port", str(bind_port))
      self.cfg.set("last", "server_upnp", str(use_upnp))

      bind = ContactInfo(bind_addr, bind_port)
      serv = ContactInfo(host, port)

      if use_upnp:
        self.upnp = upnp.UPNPManager()
        self.upnp.connect("port-added", lambda w,x,y:
          self._do_port_added(w,x,y,hash))
        self.upnp.connect("add-port-error", self._do_add_port_error)
        self.upnp.add_udp_port(bind)
        self.set_sensitive(False)
      else:
        self._start_server(bind, serv, hash)
  def _do_add_port_error(self, manager, error):
    # see comment in _do_port_added
    with gtk.gdk.lock:
      self.set_sensitive(True)
      mdialog = gtk.MessageDialog(self,
                                  gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                                  gtk.MESSAGE_ERROR,
                                  gtk.BUTTONS_OK,
                                  "Error forwarding UPnP port: {0}".format(error))
      mdialog.run()
      mdialog.destroy()
      self.upnp.shutdown()
      self.upnp = None
      glib.idle_add(self.start_server)
  def _do_port_added(self, manager, external, internal, hash):
    # I am going to be completely honest and admit that I have
    # ABSOLUTELY NO IDEA why I need to grab the gtk.gdk thread lock here
    # but it will hang if I do not.
    # Hypothesis: gupnp.igd.Simple is not using the same GMainContext as I am?
    with gtk.gdk.lock:
      self.set_sensitive(True)
      if self.server is not None:
        return
      mdialog = gtk.MessageDialog(self,
                                  gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                                  gtk.MESSAGE_QUESTION,
                                  gtk.BUTTONS_OK_CANCEL,
                                  "UPnP forwarded succesfully. Start server on {0:s} bound to {1:s}?".format(external, internal))
      response = mdialog.run()
      mdialog.destroy()
      if response == gtk.RESPONSE_OK:
        self._start_server(internal, external, hash)
  def _start_server(self, internal, external, hash):
    self.server_thread = threading.Thread(target=lambda:
      self._bootstrap_server(hash, internal, external))
    self.server_thread.daemon = True
    self.server_thread.start()

    self.started_only.set_sensitive(True)
    self.stopped_only.set_sensitive(False)

  def _bootstrap_server(self, hash, internal, external):
    self.server = DHTServer(self.cfg, hash, internal, external, self._do_log)
    self.bucketview.bind_to(self.server.routingtable)
    self.nodeview.bind_to(self.server.routingtable)
    self.torrentview.bind_to(self.server.torrents)
    self.peerview.bind_to(self.server.torrents)
    glib.idle_add(self.netstatus.attach_to_prop, self.server, "got_incoming")
    glib.idle_add(self.serverstatus.set_status, True)

    self.server.serve_forever()
  def stop_server(self, widget=None):
    self.server.shutdown()

    self.netstatus.detach_prop()
    self.nodeview.unbind()
    self.bucketview.unbind()
    self.torrentview.unbind()
    self.peerview.unbind()

    self.server = None
    self.server_thread = None

    self.started_only.set_sensitive(False)
    self.stopped_only.set_sensitive(True)

    self.serverstatus.set_status(False)

    if self.upnp is not None:
      self.upnp.shutdown()
      self.upnp = None

  def ping_node(self, widget=None, host=None, port=None):
    if not self.server:
      self.error("Server not started!")
      return
    if not host:
      host = self.cfg.get("last", "ping_host")
    if not port:
      port = self.cfg.get("last", "ping_port")
    else:
      port = str(port)

    dialog = dialogs.HostDialog(self, "Ping Node...", host, port)

    response = dialog.run()
    dialog.destroy()
    if response is not None:
      host, port = response

      self.cfg.set("last", "ping_host", host)
      self.cfg.set("last", "ping_port", str(port))

      self.server.send_ping((host, port))

  def find_node(self, widget=None, host=None, port=None):
    if not self.server:
      self.error("Server not started!")
      return
    if not host:
      host = self.cfg.get("last", "find_host")
    if not port:
      port = self.cfg.get("last", "find_port")
    else:
      port = str(port)
    hash = self.cfg.get("last", "find_hash")

    dialog = dialogs.HostDialog(self, "Find Node...", host, port, hash)

    response = dialog.run()
    dialog.destroy()
    if response is not None:
      host, port, hash = response

      self.cfg.set("last", "find_host", host)
      self.cfg.set("last", "find_port", str(port))
      self.cfg.set("last", "find_hash", hash)

      self.server.send_find_node((host, port), hash)

  def get_peers(self, widget=None, host=None, port=None):
    if not self.server:
      self.error("Server not started!")
      return
    if not host:
      host = self.cfg.get("last", "get_peers_host")
    if not port:
      port = self.cfg.get("last", "get_peers_port")
    else:
      port = str(port)
    hash = self.cfg.get("last", "get_peers_hash")

    dialog = dialogs.HostDialog(self, "Get Peers...", host, port, hash)

    response = dialog.run()
    dialog.destroy()
    if response is not None:
      host, port, hash = response

      self.cfg.set("last", "get_peers_host", host)
      self.cfg.set("last", "get_peers_port", str(port))
      self.cfg.set("last", "get_peers_hash", hash)

      self.server.send_get_peers((host, port), hash)

  def load_torrent(self, widget):
    dialog = gtk.FileChooserDialog("Choose a torrent", self,
                                   gtk.FILE_CHOOSER_ACTION_OPEN,
                                   (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                    gtk.STOCK_OPEN, gtk.RESPONSE_OK))
    torrent_filter = gtk.FileFilter()
    torrent_filter.set_name("Torrent Metainfo File")
    torrent_filter.add_pattern("*.torrent")
    dialog.add_filter(torrent_filter)

    response = dialog.run()
    if response == gtk.RESPONSE_OK:
      file = dialog.get_filename()
      try:
        self.server.load_torrent(file)
      except Exception as err:
        self.error("Could not load nodes from torrent.\n\nReason:" + str(err))
    dialog.destroy()

  def _do_log(self, message):
    glib.idle_add(self.log, message)

  def log(self,message):
    message = str(message)

    cid = self.statusbar.get_context_id("log")
    self.statusbar.pop(cid)
    self.statusbar.push(cid, message)
    self.logbuffer.insert(self.logbuffer.get_bounds()[1], message + "\n")
    vadj = self.logview.parent.get_vadjustment()
    vadj.value = vadj.upper

    return False

  def _do_nodeview_right_click(self, treeview, event, row):
    menu = gtk.Menu()

    ping_act = self.started_only.get_action("ping")
    ping = ping_act.create_menu_item()
    ping.connect("activate", lambda w: (
      self.ping_node(host=row[1], port=row[2])))
    menu.add(ping)
    ping_act.block_activate_from(ping)
    ping.show()

    find_act = self.started_only.get_action("find")
    find = find_act.create_menu_item()
    find.connect("activate", lambda w: (
      self.find_node(host=row[1], port=row[2])))
    menu.add(find)
    find_act.block_activate_from(find)
    find.show()

    get_peers_act = self.started_only.get_action("get_peers")
    get_peers = get_peers_act.create_menu_item()
    get_peers.connect("activate", lambda w: (
      self.get_peers(host=row[1], port=row[2])))
    menu.add(get_peers)
    get_peers_act.block_activate_from(get_peers)
    get_peers.show()

    if treeview is self.bucketnodeview:
      sep = gtk.SeparatorMenuItem()
      menu.add(sep)
      sep.show()

      goto_nodes = gtk.MenuItem("View in Nodes Tab")
      goto_nodes.connect("activate", self.goto_nodes_tab, treeview)
      menu.add(goto_nodes)
      goto_nodes.show()

    menu.popup(None, None, None, event.button, event.time)

  def goto_nodes_tab(self, w, treeview):
    self.notebook.set_current_page(0)
    treeview.goto_parent()

  def error(self, message):
    dialog = gtk.MessageDialog(self,
                               gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                               gtk.MESSAGE_ERROR,
                               gtk.BUTTONS_OK,
                               message)
    dialog.run()
    dialog.destroy()
