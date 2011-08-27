# This module contains the main interface for DHTPlay

import gtk
import glib
import gobject
import threading
import time
import webbrowser

from net.server import DHTServer
from net.serverwrangler import ServerWrangler
from ui import dialogs
from ui import dbview
from ui import images
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
    self.serverwrangler = ServerWrangler(self.cfg, self._do_log)
    self.serverwrangler.connect("upnp-error", self._do_upnp_error)
    self.current_server = None

    self.bound_actions = gtk.ActionGroup("bound_actions")

    vbox = gtk.VBox()
    self.add(vbox)

    # Actions

    add_server_action = gtk.Action("add_server", "Create Server",
                                   "Create a new DHT Server.",
                                   gtk.STOCK_NEW)
    add_server_action.connect("activate", self.add_server)

    quit_action = gtk.Action("quit", "Quit",
                             "Quit", gtk.STOCK_QUIT)
    quit_action.connect("activate", self.quit)

    ping_action = gtk.Action("ping", "Ping Node...",
                             "Ping a DHT Node", gtk.STOCK_REFRESH)
    ping_action.connect("activate", self.ping_node)
    self.bound_actions.add_action(ping_action)

    find_action = gtk.Action("find", "Find Node...",
                             "Find a DHT Node", gtk.STOCK_FIND)
    find_action.connect("activate", self.find_node)
    self.bound_actions.add_action(find_action)

    get_peers_action = gtk.Action("get_peers", "Get Peers...",
                                  "Get DHT Peers", gtk.STOCK_FIND)
    get_peers_action.connect("activate", self.get_peers)
    self.bound_actions.add_action(get_peers_action)

    load_action = gtk.Action("load", "Load From Torrent...",
                             "Load DHT Nodes from a torrent file",
                             gtk.STOCK_OPEN)
    load_action.connect("activate", self.load_torrent)
    self.bound_actions.add_action(load_action)

    # Menus

    menubar = gtk.MenuBar()
    vbox.pack_start(menubar, False, False)

    file_menuitem = gtk.MenuItem("File")
    menubar.add(file_menuitem)

    file_menu = gtk.Menu()
    file_menuitem.set_submenu(file_menu)

    file_menu.add(add_server_action.create_menu_item())
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

    # Main Toolbar

    toolbar = gtk.Toolbar()
    vbox.pack_start(toolbar, False, False)

    toolbar.add(add_server_action.create_tool_item())

    # Work area

    serverpane = gtk.HPaned()
    vbox.pack_start(serverpane, True, True)

    self.serverview = dbview.ServerView(self.serverwrangler)
    self.serverview.connect("cursor-changed",
                            self._do_serverview_cursor_changed)
    serverpane.pack1(self.serverview, True, True)

    server_frame = gtk.Frame()
    server_frame.set_shadow_type(gtk.SHADOW_IN)
    serverpane.pack2(server_frame, True, True)

    server_area = gtk.VBox()
    server_frame.add(server_area)

    # Server Area

    server_toolbar = gtk.Toolbar()
    server_area.pack_start(server_toolbar, False, False)

    server_toolbar.add(ping_action.create_tool_item())
    server_toolbar.add(find_action.create_tool_item())
    server_toolbar.add(get_peers_action.create_tool_item())
    server_toolbar.add(load_action.create_tool_item())

    self.notebook = gtk.Notebook()
    server_area.pack_start(self.notebook)

    self.bucketview = dbview.BucketView()

    self.nodeview = dbview.NodeView(self.bucketview)
    self.nodeview.connect("right-click", self._do_nodeview_right_click)

    self.peerview = dbview.PeerView()

    self.torrentview = dbview.TorrentView()
    self.torrentview.connect("right-click", self._do_torrentview_right_click)

    self.bucketnodeview = dbview.BucketNodeView(self.bucketview,
                                                self.nodeview)
    self.bucketnodeview.connect("right-click", self._do_nodeview_right_click)

    self.torrentpeerview = dbview.TorrentPeerView(self.torrentview,
                                                  self.peerview)
    self.peertorrentview = dbview.PeerTorrentView(self.peerview,
                                                  self.torrentview)
    self.peertorrentview.connect("right-click", self._do_torrentview_right_click)

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

    # Status Bar

    self.statusbar = gtk.Statusbar()
    vbox.pack_end(self.statusbar, False, False)

#    self.serverstatus = StatusLabel("Server:", False)
#    self.statusbar.pack_start(self.serverstatus, False, False)

#    self.statusbar.pack_start(gtk.VSeparator(), False, False)

    self.netstatus = StatusLabel("Network:")
    self.netstatus.attach_to_prop(self.serverwrangler, "incoming")
    self.statusbar.pack_start(self.netstatus, False, False)

    self.bound_actions.set_sensitive(False)

    self.show_all()
    self.hide()

    self.serverwrangler.launch_dispatch()

    self._do_log("Application Initiated.")

  def quit(self, widget=None, event=None):
    self._cleanup()

  def _cleanup(self, widget=None, event=None):
    self.serverwrangler.shutdown()
    gtk.main_iteration(False)
    gtk.main_quit()

  def add_server(self, widget=None):
    dialog = dialogs.ServerDialog(self, "Add Server...", self.cfg,
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
      if use_upnp:
        serv = None
      else:
        serv = ContactInfo(host, port)

      hash = Hash(hash)

      self.serverwrangler.add_server(hash, bind, serv, use_upnp)

  def _do_upnp_error(self, manager, bind, error):
    glib.idle_add(self.error, "UPnP Error when adding server: {0}".formaT(error))

  def ping_node(self, widget=None, host=None, port=None):
    if not self.current_server:
      self.error("Can't ping node: no server selected.")
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

      self.current_server.send_ping((host, port))

  def find_node(self, widget=None, host=None, port=None):
    if not self.current_server:
      self.error("Can't find_node, no server selected.")
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

      self.current_server.send_find_node((host, port), hash)

  def get_peers(self, widget=None, host=None, port=None):
    if not self.current_server:
      self.error("Can't get_peers, no server selected!")
      return
    if not host:
      host = self.cfg.get("last", "get_peers_host")
    if not port:
      port = self.cfg.get("last", "get_peers_port")
    else:
      port = str(port)
    hash = self.cfg.get("last", "get_peers_hash")
    scrape = self.cfg.getboolean("last", "get_peers_scrape")

    dialog = dialogs.GetPeersDialog(self, "Get Peers...", host, port,
                                    hash, scrape)

    response = dialog.run()
    dialog.destroy()
    if response is not None:
      host, port, hash, scrape = response

      self.cfg.set("last", "get_peers_host", host)
      self.cfg.set("last", "get_peers_port", str(port))
      self.cfg.set("last", "get_peers_hash", hash)
      self.cfg.set("last", "get_peers_scrape", str(scrape))

      self.current_server.send_get_peers((host, port), hash, scrape)

  def load_torrent(self, widget):
    if not self.current_server:
      self.error("Can't load a torrent without a server selected.")
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
        self.current_server.load_torrent(file)
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

    ping_act = self.bound_actions.get_action("ping")
    ping = ping_act.create_menu_item()
    ping.connect("activate", lambda w: (
      self.ping_node(host=row[1], port=row[2])))
    menu.add(ping)
    ping_act.block_activate_from(ping)
    ping.show()

    find_act = self.bound_actions.get_action("find")
    find = find_act.create_menu_item()
    find.connect("activate", lambda w: (
      self.find_node(host=row[1], port=row[2])))
    menu.add(find)
    find_act.block_activate_from(find)
    find.show()

    get_peers_act = self.bound_actions.get_action("get_peers")
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
      goto_nodes.connect("activate", self.goto_tab, treeview, 0)
      menu.add(goto_nodes)
      goto_nodes.show()

    menu.popup(None, None, None, event.button, event.time)

  def _do_torrentview_right_click(self, treeview, event, row):
    menu = gtk.Menu()

    copy_infohash = gtk.ImageMenuItem(gtk.STOCK_COPY)
    copy_infohash.set_label("Copy InfoHash")
    copy_infohash.connect("activate",
                          lambda x: gtk.Clipboard().set_text(row[1]))
    menu.add(copy_infohash)
    copy_infohash.show()

    if self.current_server is not None:
      open_magnet = gtk.ImageMenuItem()
      open_magnet.set_image(gtk.image_new_from_pixbuf(images.magnet))
      open_magnet.set_label("Open Magnet URI")
      open_magnet.connect("activate",
                      lambda x: webbrowser.open(
                        self.current_server.torrents.get_magnet(Hash(row[1]))))
      menu.add(open_magnet)
      open_magnet.show()

    if treeview is self.peertorrentview:
      sep = gtk.SeparatorMenuItem()
      menu.add(sep)
      sep.show()

      goto_torrents = gtk.MenuItem("View in Torrents Tab")
      goto_torrents.connect("activate", self.goto_tab, treeview, 2)
      menu.add(goto_torrents)
      goto_torrents.show()

    menu.popup(None, None, None, event.button, event.time)

  def _do_serverview_cursor_changed(self, treeview, row):
    server = row[3]
    self.set_current_server(server)

  def set_current_server(self, server):
    self.current_server = server
    self.bound_actions.set_sensitive(True)
    self.bucketview.bind_to(server.routingtable)
    self.nodeview.bind_to(server.routingtable)
    self.torrentview.bind_to(server.torrents)
    self.peerview.bind_to(server.torrents)

  def goto_tab(self, w, treeview, page):
    self.notebook.set_current_page(page)
    treeview.goto_parent()

  def error(self, message):
    dialog = gtk.MessageDialog(self,
                               gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                               gtk.MESSAGE_ERROR,
                               gtk.BUTTONS_OK,
                               message)
    dialog.run()
    dialog.destroy()
