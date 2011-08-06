#!/usr/bin/python
# This module contains the main interface for DHTPlay
import gtk
import glib
import threading
import time

import dht
import defaults
import dialogs
from net import ContactInfo, Hash

name = "DHTPlay"

version = "0.1"

settings = "settings.cfg"

class Interface(gtk.Window):
  def __init__(self, opts):
    gtk.Window.__init__(self)
    self.connect("delete-event", self._cleanup)
    self.set_title("{0} {1}".format(name, version))

    self.cfg = opts
    self.server_thread = None
    self.server = None

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

    notebook = gtk.Notebook()
    vbox.pack_start(notebook, True, True)

    nodespage = gtk.VBox()
    notebook.append_page(nodespage, gtk.Label("Nodes"))

    nodeswin = gtk.ScrolledWindow()
    nodeswin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    nodespage.pack_start(nodeswin)

    self.nodeslist = gtk.ListStore(int, str, int, str, str, float, bool)
    nodestree = gtk.TreeView(self.nodeslist)
    nodestree.connect("button_press_event", self._nodestree_button_press)
    nodeswin.add(nodestree)

    bucketcolumn = gtk.TreeViewColumn("Bucket")
    bucketrenderer = gtk.CellRendererText()
    bucketcolumn.pack_start(bucketrenderer)
    bucketcolumn.set_sort_column_id(0)
    bucketcolumn.add_attribute(bucketrenderer, "text", 0)
    nodestree.append_column(bucketcolumn)

    pendingcolumn = gtk.TreeViewColumn("Pending")
    pendingrenderer = gtk.CellRendererToggle()
    pendingrenderer.set_radio(False)
    pendingrenderer.set_active(False)
    pendingcolumn.pack_start(pendingrenderer)
    pendingcolumn.set_sort_column_id(6)
    pendingcolumn.add_attribute(pendingrenderer, "active", 6)
    nodestree.append_column(pendingcolumn)

    hostcolumn = gtk.TreeViewColumn("Host")
    hostrenderer = gtk.CellRendererText()
    hostcolumn.pack_start(hostrenderer)
    hostcolumn.set_sort_column_id(1)
    hostcolumn.add_attribute(hostrenderer, "text", 1)
    nodestree.append_column(hostcolumn)

    portcolumn = gtk.TreeViewColumn("Port")
    portrenderer = gtk.CellRendererText()
    portcolumn.pack_start(portrenderer)
    portcolumn.set_sort_column_id(2)
    portcolumn.add_attribute(portrenderer, "text", 2)
    nodestree.append_column(portcolumn)

    hashcolumn = gtk.TreeViewColumn("Hash")
    hashrenderer = gtk.CellRendererText()
    hashrenderer.set_property("family", "monospace")
    hashcolumn.pack_start(hashrenderer)
    hashcolumn.set_sort_column_id(3)
    hashcolumn.add_attribute(hashrenderer, "text", 3)
    nodestree.append_column(hashcolumn)

    timecolumn = gtk.TreeViewColumn("Last Good")
    timerenderer = gtk.CellRendererText()
    timecolumn.pack_start(timerenderer)
    timecolumn.set_sort_column_id(5)
    timecolumn.add_attribute(timerenderer, "text", 4)
    nodestree.append_column(timecolumn)

    bucketspage = gtk.VBox()
    notebook.append_page(bucketspage, gtk.Label("Buckets"))

    bucketswin = gtk.ScrolledWindow()
    bucketswin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    bucketspage.pack_start(bucketswin, True, True)

    self.bucketslist = gtk.ListStore(int, float, float, int, str, float)
    bucketstree = gtk.TreeView(self.bucketslist)
    bucketstree.connect("button_press_event", self._bucketstree_button_press)
    bucketswin.add(bucketstree)

    idcolumn = gtk.TreeViewColumn("ID")
    idrenderer = gtk.CellRendererText()
    idcolumn.pack_start(idrenderer)
    idcolumn.set_sort_column_id(0)
    idcolumn.add_attribute(idrenderer, "text", 0)
    bucketstree.append_column(idcolumn)

    mincolumn = gtk.TreeViewColumn("Min")
    minrenderer = gtk.CellRendererText()
    mincolumn.pack_start(minrenderer)
    mincolumn.set_sort_column_id(1)
    mincolumn.add_attribute(minrenderer, "text", 1)
    bucketstree.append_column(mincolumn)

    maxcolumn = gtk.TreeViewColumn("Max")
    maxrenderer = gtk.CellRendererText()
    maxcolumn.pack_start(maxrenderer)
    maxcolumn.set_sort_column_id(2)
    maxcolumn.add_attribute(maxrenderer, "text", 2)
    bucketstree.append_column(maxcolumn)

    numcolumn = gtk.TreeViewColumn("Num Nodes")
    numrenderer = gtk.CellRendererText()
    numcolumn.pack_start(numrenderer)
    numcolumn.set_sort_column_id(3)
    numcolumn.add_attribute(numrenderer, "text", 3)
    bucketstree.append_column(numcolumn)

    btimecolumn = gtk.TreeViewColumn("Last Changed")
    btimerenderer = gtk.CellRendererText()
    btimecolumn.pack_start(btimerenderer)
    btimecolumn.set_sort_column_id(5)
    btimecolumn.add_attribute(btimerenderer, "text", 4)
    bucketstree.append_column(btimecolumn)

    torrentspane = gtk.VPaned()
    notebook.append_page(torrentspane, gtk.Label("Torrents"))

    torrentswin = gtk.ScrolledWindow()
    torrentswin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    torrentspane.pack1(torrentswin, True, True)

    self.torrentslist = gtk.ListStore(int, str, str, float)
    torrentstree = gtk.TreeView(self.torrentslist)
    torrentstree.connect("button_press_event", self._torrentstree_button_press)
    torrentstree.connect("cursor-changed", self._torrentstree_cursor_changed)
    torrentswin.add(torrentstree)

    tidcolumn = gtk.TreeViewColumn("ID")
    tidrenderer = gtk.CellRendererText()
    tidcolumn.pack_start(tidrenderer)
    tidcolumn.set_sort_column_id(0)
    tidcolumn.add_attribute(tidrenderer, "text", 0)
    torrentstree.append_column(tidcolumn)

    thashcolumn = gtk.TreeViewColumn("Info Hash")
    thashrenderer = gtk.CellRendererText()
    thashcolumn.pack_start(thashrenderer)
    thashcolumn.set_sort_column_id(1)
    thashcolumn.add_attribute(thashrenderer, "text", 1)
    torrentstree.append_column(thashcolumn)

    tupdatedcolumn = gtk.TreeViewColumn("Updated")
    tupdatedrenderer = gtk.CellRendererText()
    tupdatedcolumn.pack_start(tupdatedrenderer)
    tupdatedcolumn.set_sort_column_id(3)
    tupdatedcolumn.add_attribute(tupdatedrenderer, "text", 2)
    torrentstree.append_column(tupdatedcolumn)

    torrentsinfo = gtk.VBox()
    torrentspane.pack2(torrentsinfo, True, True)

    torrentsinfo.pack_start(gtk.Label("Torrent Info:"), False, False)

    torrentspeerswin = gtk.ScrolledWindow()
    torrentspeerswin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    torrentsinfo.pack_start(torrentspeerswin, True, True)

    torrentspeerstree = self._make_peers_view()
    torrentspeerstree.connect("button_press_event",
                              self._torrentspeerstree_button_press)
    torrentspeerswin.add(torrentspeerstree)

    peerspage = gtk.VBox()
    notebook.append_page(peerspage, gtk.Label("Peers"))

    peerswin = gtk.ScrolledWindow()
    peerswin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    peerspage.pack_start(peerswin, True, True)

    self.peerslist = gtk.ListStore(int, str, int, str, float)
    peerstree = self._make_peers_view()
    peerstree.set_model(self.peerslist)
    peerstree.connect("button_press_event", self._peerstree_button_press)
    peerswin.add(peerstree)

    logpage = gtk.VBox()
    notebook.append_page(logpage, gtk.Label("Log"))

    logwin = gtk.ScrolledWindow()
    logwin.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
    logpage.pack_start(logwin, True, True)

    self.logbuffer = gtk.TextBuffer()
    self.logview = gtk.TextView(self.logbuffer)
    self.logview.set_wrap_mode(gtk.WRAP_NONE)
    self.logview.set_editable(True)
    self.logview.set_cursor_visible(False)
    logwin.add(self.logview)

    self.statusbar = gtk.Statusbar()
    vbox.pack_end(self.statusbar, False, False)

    self.started_only.set_sensitive(False)

    self.torrentspeerslist = self.peerslist.filter_new()
    vis = (lambda model, iter, data:
             model.get_value(iter,0) in data)
    self.torrentspeersdata = set()
    self.torrentspeerslist.set_visible_func(vis, self.torrentspeersdata)
    torrentspeerstree.set_model(self.torrentspeerslist)

    self.show_all()
    self.hide()

    self._do_log("Application Initiated.")

  def _make_peers_view(self):
    peerstree = gtk.TreeView()

    pidcolumn = gtk.TreeViewColumn("ID")
    pidrenderer = gtk.CellRendererText()
    pidcolumn.pack_start(pidrenderer)
    pidcolumn.set_sort_column_id(0)
    pidcolumn.add_attribute(pidrenderer, "text", 0)
    peerstree.append_column(pidcolumn)

    phostcolumn = gtk.TreeViewColumn("Host")
    phostrenderer = gtk.CellRendererText()
    phostcolumn.pack_start(phostrenderer)
    phostcolumn.set_sort_column_id(1)
    phostcolumn.add_attribute(phostrenderer, "text", 1)
    peerstree.append_column(phostcolumn)

    pportcolumn = gtk.TreeViewColumn("Port")
    pportrenderer = gtk.CellRendererText()
    pportcolumn.pack_start(pportrenderer)
    pportcolumn.set_sort_column_id(2)
    pportcolumn.add_attribute(pportrenderer, "text", 2)
    peerstree.append_column(pportcolumn)

    pupdatedcolumn = gtk.TreeViewColumn("Updated")
    pupdatedrenderer = gtk.CellRendererText()
    pupdatedcolumn.pack_start(pupdatedrenderer)
    pupdatedcolumn.set_sort_column_id(4)
    pupdatedcolumn.add_attribute(pupdatedrenderer, "text", 3)
    peerstree.append_column(pupdatedcolumn)

    return peerstree

  def _cleanup(self, widget, event):
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

    dialog = dialogs.HostDialog(self, "Start Server...", host, port, hash)

    response = dialog.run()

    if response is not None:
      host, port, hash = response

      self.cfg.set("last", "server_host", host)
      self.cfg.set("last", "server_port", str(port))
      self.cfg.set("last", "server_hash", hash)

      self.server_thread = threading.Thread(target=lambda:
        self._bootstrap_server(hash, host, port))
      self.server_thread.daemon = True
      self.server_thread.start()

      self.started_only.set_sensitive(True)
      self.stopped_only.set_sensitive(False)

  def _bootstrap_server(self, hash, host, port):
    self.server = dht.DHTServer(self.cfg, hash, (host, port), self._do_log)
    self.server.routingtable.connect("node-added", self._node_added)
    self.server.routingtable.connect("node-removed", self._node_removed)
    self.server.routingtable.connect("bucket-split", self._bucket_split)
    self.server.routingtable.connect("bucket-changed", self._bucket_changed)
    self.server.routingtable.connect("node-changed", self._node_changed)
    self.server.torrents.connect("torrent-added", self._torrent_added)
    self.server.torrents.connect("peer-added", self._peer_added)
    self.server.torrents.connect("peer-changed", self._peer_changed)
    glib.idle_add(self._refresh_nodes)
    self.server.serve_forever()

  def stop_server(self, widget=None):
    self.server.shutdown()
    self.server = None
    self.server_thread = None

    self.started_only.set_sensitive(False)
    self.stopped_only.set_sensitive(True)

    self.nodeslist.clear()
    self.bucketslist.clear()

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

    if response is not None:
      host, port, hash = response

      self.cfg.set("last", "get_peers_host", host)
      self.cfg.set("last", "get_peers_port", str(port))
      self.cfg.set("last", "get_peers_hash", hash)

      self.server.send_get_peers((host, port), hash)

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

  def _refresh_nodes(self):
    self.nodeslist.clear()
    self.bucketslist.clear()
    if self.server:
       for bucket in self.server.routingtable.get_bucket_rows():
         self._add_bucket_row(bucket)
       for node in self.server.routingtable.get_node_rows():
         self._add_node_row(node)
       for torrent in self.server.torrents.get_torrent_rows():
         self._add_torrent_row(torrent)
       for peer in self.server.torrents.get_peer_rows():
         self._add_peer_row(peer)
    return False

  def _add_bucket_row(self, row):
    self.bucketslist.append((row["id"],
                             Hash(row["start"]).get_pow(),
                             Hash(row["end"]).get_pow(),
                             0,
                             row["updated"].ctime(),
                             time.mktime(row["updated"].timetuple())))

  def _update_bucket_row(self, row):
    iter = self.bucketslist.get_iter(0)
    while (iter is not None and
           self.bucketslist.get_value(iter, 0) != row["id"]):
      iter = self.bucketslist.iter_next(iter)
    if iter is not None:
      self.bucketslist.set(iter, 0, row["id"],
                           1, Hash(row["start"]).get_pow(),
                           2, Hash(row["end"]).get_pow(),
                           4, row["updated"].ctime(),
                           5, time.mktime(row["updated"].timetuple()))

  def _add_bucket_node(self, bucket, amt):
    iter = self.bucketslist.get_iter(0)
    while (iter is not None and
           self.bucketslist.get_value(iter, 0) != bucket):
      iter = self.bucketslist.iter_next(iter)
    if iter is not None:
      self.bucketslist.set(iter, 3, self.bucketslist.get(iter, 3)[0]+amt)

  def _add_node_row(self, row):
    try:
      contact = ContactInfo(row["contact"])
    except TypeError:
      pass
    self.nodeslist.append((row["bucket_id"],
                           contact.host,
                           contact.port,
                           Hash(row["hash"]).get_hex(),
                           row["updated"].ctime(),
                           time.mktime(row["updated"].timetuple()),
                           row["pending"]))
    if not row["pending"]:
      self._add_bucket_node(row["bucket_id"], +1)

  def _update_node_row(self, row):
    iter = self.nodeslist.get_iter(0)
    while (iter is not None and
           self.nodeslist.get_value(iter, 3) != Hash(row["hash"]).get_hex()):
      iter = self.nodeslist.iter_next(iter)
    if iter is not None:
      contact = ContactInfo(row["contact"])
      if not self.nodeslist.get(iter,6)[0]:
        self._add_bucket_node(self.nodeslist.get_value(iter,0), -1)
      self.nodeslist.set(iter, 0, int(row["bucket_id"]),
                         1, contact.host, 2, contact.port,
                         3, Hash(row["hash"]).get_hex(),
                         4, row["updated"].ctime(),
                         5, time.mktime(row["updated"].timetuple()),
                         6, row["pending"])
      if not row["pending"]:
        self._add_bucket_node(row["bucket_id"], +1)

  def _remove_node_row(self, hash):
    iter = self.nodeslist.get_iter(0)
    while (iter is not None and
           self.nodeslist.get_value(iter,3) != hash.get_hex()):
      iter = self.nodeslist.iter_next(iter)
    if iter is not None:
      self._add_bucket_node(self.nodeslist.get_value(iter, 0), -1)
      self.nodeslist.remove(iter)

  def _add_torrent_row(self, row):
    self.torrentslist.append((row["id"], Hash(row["hash"]).get_hex(),
                           row["updated"].ctime(),
                           time.mktime(row["updated"].timetuple())))

  def _add_peer_row(self, row):
    c=ContactInfo(row["contact"])
    self.peerslist.append((row["id"], c.host, c.port,
                           row["updated"].ctime(),
                           time.mktime(row["updated"].timetuple()))) 

  def _update_peer_row(self, row):
    iter = self.peerslist.get_iter(0)
    while (iter is not None and
           self.peerslist.get_value(iter, 0) != row["id"]):
      iter = self.peerslist.iter_next(iter)
    if iter is not None:
      contact = ContactInfo(row["contact"])
      self.peerslist.set(iter, 0, int(row["id"]),
                         1, contact.host, 2, contact.port,
                         3, row["updated"].ctime(),
                         4, time.mktime(row["updated"].timetuple()))

  def _node_added(self, router, hash):
    self._add_node_row(router.get_node_row(hash))

  def _peer_added(self, router, id):
    self._add_peer_row(router.get_peer_row(id))

  def _peer_changed(self, router, id):
    self._update_peer_row(router.get_peer_row(id))

  def _bucket_split(self, router, bucket1, bucket2):
    self._add_bucket_row(router.get_bucket_row(bucket2))
    self._update_bucket_row(router.get_bucket_row(bucket1))

  def _node_removed(self, router, hash):
    self._remove_node_row(hash)

  def _bucket_changed(self, router, bucket):
    self._update_bucket_row(router.get_bucket_row(bucket))

  def _node_changed(self, router, hash):
    self._update_node_row(router.get_node_row(hash))

  def _torrent_added(self, db, hash):
    self._add_torrent_row(db.get_torrent_row(hash))

  def _nodestree_button_press(self, treeview, event):
    if event.button == 3:
      x = int(event.x)
      y = int(event.y)
      pathinfo = treeview.get_path_at_pos(x, y)
      if pathinfo is not None:
        path, col, cellx, celly = pathinfo
        treeview.grab_focus()
        treeview.set_cursor(path, col, 0)

        iter = self.nodeslist.get_iter(path)

        menu = gtk.Menu()

        ping_act = self.started_only.get_action("ping")
        ping = ping_act.create_menu_item()
        ping.connect("activate", lambda w: (
          self.ping_node(host=self.nodeslist.get_value(iter, 1),
                         port=self.nodeslist.get_value(iter, 2))))
        menu.add(ping)
        ping_act.block_activate_from(ping)
        ping.show()

        get_peers_act = self.started_only.get_action("get_peers")
        get_peers = get_peers_act.create_menu_item()
        get_peers.connect("activate", lambda w: (
          self.get_peers(host=self.nodeslist.get_value(iter, 1),
                         port=self.nodeslist.get_value(iter, 2))))
        menu.add(get_peers)
        get_peers_act.block_activate_from(get_peers)
        get_peers.show()

        find_act = self.started_only.get_action("find")
        find = find_act.create_menu_item()
        find.connect("activate", lambda w: (
          self.find_node(host=self.nodeslist.get_value(iter, 1),
                         port=self.nodeslist.get_value(iter, 2))))
        menu.add(find)
        find_act.block_activate_from(find)
        find.show()

        menu.popup(None, None, None, event.button, event.time)

  def _bucketstree_button_press(self, treeview, event):
    pass

  def _torrentstree_button_press(self, treeview, event):
    pass

  def _torrentspeerstree_button_press(self, treeview, event):
    pass

  def _peerstree_button_press(self, treeview, event):
    pass

  def _torrentstree_cursor_changed(self, treeview):
    iter = self.torrentslist.get_iter(treeview.get_cursor()[0])
    id = self.torrentslist.get_value(iter, 0)
    self.torrentspeersdata.clear()
    if self.server:
      peers = self.server.torrents.get_torrent_peers(id)
      self.torrentspeersdata.update(p[0] for p in peers)
    self.torrentspeerslist.refilter()

  def load_torrent(self, widget):
    dialog = gtk.FileChooserDialog("Choose a torrent", self,
                                   gtk.FILE_CHOOSER_ACTION_OPEN,
                                   (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                    gtk.STOCK_OPEN, gtk.RESPONSE_OK))
    torrent_filter = gtk.FileFilter()
    torrent_filter.set_name("Torrent Metainfo File")
    torrent_filter.add_pattern("*.torrent")

    response = dialog.run()
    if response == gtk.RESPONSE_OK:
      file = dialog.get_filename()
      try:
        self.server.load_torrent(file)
      except Exception as err:
        self.error("Could not load nodes from torrent.\n\nReason:" + str(err))
    dialog.destroy()

  def error(self, message):
    dialog = gtk.MessageDialog(self,
                               gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                               gtk.MESSAGE_ERROR,
                               gtk.BUTTONS_OK,
                               message)
    dialog.run()
    dialog.destroy()

if __name__ == "__main__":
  gtk.gdk.threads_init()
  config = defaults.default_config
  config.read(settings)
  app = Interface(config)
  app.show()
  gtk.main()
  try:
    app.destroy()
  except:
    pass
  config.write(open(settings, 'w'))
