import sqlite3
import threading
import Queue

class SQLiteThread(threading.Thread):
  _SCRIPT = -2
  _NO_RESULT = -1
  daemon = True
  def __init__(self, db):
    threading.Thread.__init__(self)
    self.stmts = Queue.Queue()
    self.results = Queue.Queue()
    self.last_id = 0
    self.id_lock = threading.Lock()
    self.db = db
    self._stopped = False
  def run(self):
    conn = sqlite3.connect(self.db,
                        detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES,
                        check_same_thread=True,
                        isolation_level=None)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    while 1:
      try:
        stmt = self.stmts.get(False)
      except Queue.Empty:
        if self._stopped:
          conn.commit()
          conn.close()
          return
        else:
          continue
      try:
        if stmt[0] == self._SCRIPT:
          cursor.executescript(stmt[1])
        elif stmt[2] is not None:
          cursor.execute(stmt[1], stmt[2])
        else:
          cursor.execute(stmt[1])
      except (sqlite3.OperationalError, sqlite3.ProgrammingError) as e:
        raise ValueError("Invalid SQL Statement - {0} ({1})".format(stmt, e))
      if stmt[0] >= 0:
        self.results.put((stmt[0], cursor.fetchall(), cursor.lastrowid))
  def execute(self, stmt, params=None):
    self._execute(self._NO_RESULT, stmt, params)
  def executescript(self, stmt):
    self._execute(self._SCRIPT, stmt, None)
  def _execute(self, id, stmt, params):
    if self._stopped:
      raise RuntimeError("Connection closed.")
    self.stmts.put((id, stmt, params))
  def _get_id(self):
    with self.id_lock:
      self.last_id += 1
      return self.last_id
  def select(self, stmt, params=None):
    id = self._get_id()
    self._execute(id, stmt, params)
    return self._wait_for_result(id)[1]
  def select_one(self, stmt, params=None):
    rows = self.select(stmt, params)
    if len(rows):
      return rows[0]
    else:
      return None
  def insert(self, stmt, params=None):
    id = self._get_id()
    self._execute(id, stmt, params)
    return self._wait_for_result(id)[2]
  def _wait_for_result(self, id):
    while True:
      res = self.results.get(True, None) # block forever
      if res[0] != id:
        self.results.put(res) # oops
      else:
        return res
  def close(self):
    self._stopped = True
