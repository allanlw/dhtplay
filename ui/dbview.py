import gtk
import gobject
import time
import urllib

from net.sha1hash import Hash
from net.contactinfo import ContactInfo

class BaseDBView(gtk.ScrolledWindow):
  """Base class for convenient database views."""
  __gsignals__ = {
    "right-click" : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
      (gtk.gdk.Event, gobject.TYPE_PYOBJECT)),
    "cursor-changed": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
      (gobject.TYPE_PYOBJECT,))
  }
  def __init__(self, schema, cols):
    gtk.ScrolledWindow.__init__(self)
    self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

    self._schema = schema
    self._cols = cols

    self._data = gtk.ListStore(*tuple(schema))
    self._view = gtk.TreeView(self._data)
    self._view.connect("button_press_event", self._do_button_press_event)
    self._view.connect("cursor-changed", self.__do_cursor_changed)
    self.add(self._view)

    for col in cols:
      col_widget = gtk.TreeViewColumn(col[0])
      if self._data.get_column_type(col[1]) == gobject.TYPE_BOOLEAN:
        renderer = gtk.CellRendererToggle()
        renderer.set_radio(False)
        renderer.set_active(False)
      else:
        renderer = gtk.CellRendererText()
        if len(col) > 3 and col[3]:
          renderer.set_property("family", "MonoSpace")
      col_widget.pack_start(renderer)
      col_widget.set_sort_column_id(col[2])
      if self._data.get_column_type(col[1]) == gobject.TYPE_BOOLEAN:
        attribute = "active"
      else:
        attribute = "text"
      col_widget.add_attribute(renderer, attribute, col[1])
      self._view.append_column(col_widget)
  def _do_button_press_event(self, widget, event):
    if event.button == 3:
      x = int(event.x)
      y = int(event.y)
      pathinfo = widget.get_path_at_pos(x, y)
      if pathinfo is not None:
        path, col, cellx, celly = pathinfo
        self.set_cursor(path, col)
        self.grab_focus()
        self.emit("right-click", event, self._data[path])
  def __do_cursor_changed(self, widget):
    pathinfo = widget.get_cursor()[0]
    self.emit("cursor-changed", self._data[pathinfo])
  def set_cursor(self, path, focus_column=None):
    self._view.set_cursor(path, focus_column)
  def get_cursor(self):
    path = self._view.get_cursor()[0]
    try:
      return self._data[path]
    except TypeError:
      return None
  def _find_row(self, col, value):
    iter = self._data.get_iter(0)
    while (iter is not None and
           self._data.get_value(iter, col) != value):
      iter = self._data.iter_next(iter)
    return iter

class DBView(BaseDBView):
  """Base class for database views that mirror the data."""
  def __init__(self, schema, cols, signals):
    BaseDBView.__init__(self, schema, cols)
    self._signals = signals
    self._handles = []
  def bind_to(self, ob):
    self._db = ob
    for signal,func in self._signals.iteritems():
      self._do_bind(ob, signal, func)
    self.clear()
    self._hard_update()
  def _do_bind(self, ob, signal, func):
    handle = ob.connect(signal, func)
    self._handles.append((ob, handle))
  def unbind(self):
    self._db = None
    for handle in self._handles:
      handle[0].disconnect(handle[1])
    self._handles = []
    self.clear()
  def clear(self):
    self._data.clear()
  def _hard_update(self):
    """Do a hard update.

    This is a virtual function to be overriden by subclassess
    that should insert all the rows that the db has to offer
    into the data store."""
    pass

class FilterDBView(BaseDBView):
  """Class for DB Views that filter other DBViews."""
  def __init__(self, parent, func):
    cols = [(x[0], x[1], -1) for x in parent._cols]
    BaseDBView.__init__(self, parent._schema, cols)
    self._parent = parent
    self._data = self._parent._data.filter_new()
    self._view.set_model(self._data)
    self.set_filter(func)
  def set_filter(self, func):
    self._data.set_visible_func(func)
  def refresh(self):
    self._data.refilter()
  def goto_parent(self):
    path = self._view.get_cursor()[0]
    newpath = self._data.convert_path_to_child_path(path)
    self._parent.set_cursor(newpath)
class SetFilterDBView(FilterDBView):
  """Filter by forcing a checking a column against a set."""
  def __init__(self, view, col):
    self._allowed = set()
    self._col = col
    FilterDBView.__init__(self, view, self._do_filter)
  def _do_filter(self, model, iter):
    return model.get_value(iter, self._col) in self._allowed
  def _clear_allowed(self):
    self._allowed.clear()
  def _add_allowed(self, iter):
    self._allowed.update(iter)

class BucketView(DBView):
  schema = (int, float, float, int, str, float)
  cols = (
    ("ID", 0, 0),
    ("Min", 1, 1),
    ("Max", 2, 2),
    ("Num Nodes", 3, 3),
    ("Last Changed", 4, 5),
  )
  def __init__(self, routingtable=None):
    signals = {
      "bucket-split": self._do_bucket_split,
      "bucket-changed": self._do_bucket_changed
    }
    DBView.__init__(self, self.schema, self.cols, signals)
    if routingtable is not None:
      self.bind_to(routingtable)
  def _hard_update(self):
    for bucket in self._db.get_bucket_rows():
      self._add_bucket_row(bucket)
  def _do_bucket_split(self, router, bucket1, bucket2):
    self._add_bucket_row(router.get_bucket_row(bucket2))
    self._update_bucket_row(router.get_bucket_row(bucket1))
  def _do_bucket_changed(self, router, bucket):
    self._update_bucket_row(router.get_bucket_row(bucket))
  def _add_bucket_row(self, row):
    self._data.append((row["id"],
                       row["start"].get_pow(),
                       row["end"].get_pow(),
                       0,
                       row["updated"].ctime(),
                       time.mktime(row["updated"].timetuple())))
  def _update_bucket_row(self, row):
    iter = self._find_row(0, row["id"])
    if iter is not None:
      self._data.set(iter, 0, row["id"],
                     1, row["start"].get_pow(),
                     2, row["end"].get_pow(),
                     4, row["updated"].ctime(),
                     5, time.mktime(row["updated"].timetuple()))
  def _mod_bucket_row(self, id, amt):
    iter = self._find_row(0, id)
    if iter is not None:
      self._data.set(iter, 3, self._data.get_value(iter, 3)+amt)

class NodeView(DBView):
  schema = (int, str, int, str, str, float, bool, str, int)
  cols = (
    ("Bucket", 0, 0),
    ("Pending", 6, 6),
    ("Host", 1, 1),
    ("Port", 2, 2),
    ("Hash", 3, 3, True),
    ("Version", 7, 7),
    ("Received", 8, 8),
    ("Last Good", 4, 5),
  )
  def __init__(self, bucketview, routingtable=None):
    signals = {
      "node-added": self._do_node_added,
      "node-removed": self._do_node_removed,
      "node-changed": self._do_node_changed
    }

    DBView.__init__(self, self.schema, self.cols, signals)

    self.bucketview = bucketview
    if routingtable is not None:
      self.bind_to(routingtable)
  def _hard_update(self):
    for node in self._db.get_node_rows():
      self._add_node_row(node)
  def _add_node_row(self, row):
    version = row["version"]
    if version is not None:
      version = urllib.quote(str(version))
    self._data.append((row["bucket_id"],
                       row["contact"].host, row["contact"].port,
                       row["hash"].get_hex(),
                       row["updated"].ctime(),
                       time.mktime(row["updated"].timetuple()),
                       row["pending"], version,
                       row["received"]))
    if not row["pending"]:
      self.bucketview._mod_bucket_row(row["bucket_id"], +1)
  def _update_node_row(self, row):
    iter = self._find_row(3, Hash(row["hash"]).get_hex())
    if iter is not None:
      if not self._data.get_value(iter, 6):
        self.bucketview._mod_bucket_row(self._data.get_value(iter, 0), -1)
      version = row["version"]
      if version is not None:
        version = urllib.quote(str(version))
      self._data.set(iter, 0, row["bucket_id"],
                     1, row["contact"].host, 2, row["contact"].port,
                     3, row["hash"].get_hex(),
                     4, row["updated"].ctime(),
                     5, time.mktime(row["updated"].timetuple()),
                     6, row["pending"], 7, version,
                     8, row["received"])
      if not row["pending"]:
        self.bucketview._mod_bucket_row(row["bucket_id"], +1)
  def _remove_node_row(self, hash):
    iter = self._find_row(3, Hash(hash).get_hex())
    if iter is not None:
      self.bucketview._mod_bucket_row(self._data.get_value(iter, 0), -1)
      self._data.remove(iter)
  def _do_node_added(self, router, hash):
    self._add_node_row(router.get_node_row(hash))
  def _do_node_removed(self, router, hash):
    self._remove_node_row(hash)
  def _do_node_changed(self, router, hash):
    self._update_node_row(router.get_node_row(hash))

class TorrentView(DBView):
  schema = (int, str, str, float, float, float)
  cols = (
    ("ID", 0, 0),
    ("Info Hash", 1, 1, True),
    ("Num Seeds", 4, 4),
    ("Num Peers", 5, 5),
    ("Updated", 2, 3)
  )
  def __init__(self, db = None):
    signals = {
      "torrent-added": self._do_torrent_added,
      "torrent-changed": self._do_torrent_changed
    }
    DBView.__init__(self, self.schema, self.cols, signals)
    if db is not None:
      self.bind_to(db)
  def _hard_update(self):
    for torrent in self._db.get_torrent_rows():
      self._add_torrent_row(torrent)
  def _add_torrent_row(self, row):
    self._data.append((row["id"], row["hash"].get_hex(),
                       row["updated"].ctime(),
                       time.mktime(row["updated"].timetuple()),
                       row["seeds"].get_estimate(),
                       row["peers"].get_estimate()))
  def _update_torrent_row(self, row):
    iter = self._find_row(0, row["id"])
    if iter is not None:
      self._data.set(iter, 0, row["id"], 1, row["hash"].get_hex(),
                        2, row["updated"].ctime(),
                        3, time.mktime(row["updated"].timetuple()),
                        4, row["seeds"].get_estimate(),
                        5, row["peers"].get_estimate())
  def _do_torrent_added(self, db, hash):
    self._add_torrent_row(db.get_torrent_row(hash))
  def _do_torrent_changed(self, db, hash):
    self._update_torrent_row(db.get_torrent_row(hash))

class PeerView(DBView):
  schema = (int, str, int, str, float)
  cols = (
    ("ID", 0, 0),
    ("Host", 1, 1),
    ("Port", 2, 2),
    ("Updated", 3, 4)
  )
  def __init__(self, db=None):
    signals = {
      "peer-added": self._do_peer_added,
      "peer-changed": self._do_peer_changed
    }
    DBView.__init__(self, self.schema, self.cols, signals)
    if db is not None:
      self.bind_to(db)
  def _hard_update(self):
    for peer in self._db.get_peer_rows():
      self._add_peer_row(peer)
  def _add_peer_row(self, row):
    self._data.append((row["id"], row["contact"].host, row["contact"].port,
                       row["updated"].ctime(),
                       time.mktime(row["updated"].timetuple())))
  def _update_peer_row(self, row):
    iter = self._find_row(0, row["id"])
    if iter is not None:
      self._data.set(iter, 0, row["id"],
                     1, row["contact"].host, 2, row["contact"].port,
                     3, row["updated"].ctime(),
                     4, time.mktime(row["updated"].timetuple()))
  def _do_peer_added(self, db, peer):
    self._add_peer_row(db.get_peer_row(peer))
  def _do_peer_changed(self, db, peer):
    self._update_peer_row(db.get_peer_row(peer))

class ServerView(DBView):
  schema = (str, str, int, gobject.TYPE_PYOBJECT)
  cols = (
    ("Hash", 0, 0, True),
    ("Bind Host", 1, 1),
    ("Bind Port", 2, 2)
  )
  def __init__(self, wrangler=None):
    signals = {
      "server-added": self._do_server_added
    }
    DBView.__init__(self, self.schema, self.cols, signals)
    if wrangler is not None:
      self.bind_to(wrangler)
  def _hard_update(self):
    for server in self._db.servers:
      self._add_server_row(server)
  def _do_server_added(self, wrangler, server):
    self._add_server_row(server)
  def _add_server_row(self, server):
    self._data.append((server.id.get_hex(), server.bind.host,
                       server.bind.port, server))

class TorrentPeerView(SetFilterDBView):
  def __init__(self, torrentview, peerview):
    SetFilterDBView.__init__(self, peerview, 0)
    self.torrentview = torrentview
    self.torrentview.connect("cursor-changed", self._do_cursor_changed)

    peerview._data.connect("row-changed", self._refresh_allowed)
    peerview._data.connect("row-deleted", self._refresh_allowed)
    peerview._data.connect("row-inserted", self._refresh_allowed)
  def _do_cursor_changed(self, view, row=None):
    if row is None:
      row = view.get_cursor()
    if row is None:
      return
    t_id = row[0]
    self._clear_allowed()
    if self.torrentview._db is not None:
      try:
        peers = self.torrentview._db.get_torrent_peers(t_id)
      except RuntimeError: # sql connection closed, server shut down
        return
      self._add_allowed(p[0] for p in peers)
    self.refresh()
  def _refresh_allowed(self, treemodel=None, path=None, iter=None):
    self._do_cursor_changed(self.torrentview)

class PeerTorrentView(SetFilterDBView):
  def __init__(self, peerview, torrentview):
    SetFilterDBView.__init__(self, torrentview, 0)
    self.peerview = peerview
    self.peerview.connect("cursor-changed", self._do_cursor_changed)

    torrentview._data.connect("row-changed", self._refresh_allowed)
    torrentview._data.connect("row-deleted", self._refresh_allowed)
    torrentview._data.connect("row-inserted", self._refresh_allowed)
  def _do_cursor_changed(self, view, row=None):
    if row == None:
      row = view.get_cursor()
    if row is None:
      return
    p_id = row[0]
    self._clear_allowed()
    if self.peerview._db is not None:
      try:
        torrents = self.peerview._db.get_peer_torrents(p_id)
      except RuntimeError: # sql connection has closed, server shut down
        return
      self._add_allowed(t[0] for t in torrents)
    self.refresh()
  def _refresh_allowed(self, treemodel=None, path=None, iter=None):
    self._do_cursor_changed(self.peerview)

class BucketNodeView(SetFilterDBView):
  def __init__(self, bucketview, nodeview):
    SetFilterDBView.__init__(self, nodeview, 0)
    self.bucketview = bucketview
    self.bucketview.connect("cursor-changed", self._do_cursor_changed)
  def _do_cursor_changed(self, view, row):
    b_id = row[0]
    self._clear_allowed()
    self._add_allowed([b_id])
    self.refresh()
