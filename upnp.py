try:
  from gupnp import igd
except ImportError:
  HAVE_UPNP = False
else:
  HAVE_UPNP = True

import gobject
import glib

from contactinfo import ContactInfo
import version

class UPNPManager(gobject.GObject):
  __gsignals__ = {
    "port-added": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
      (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT)),
    "add-port-error": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
      (str,))
  }
  lease_description = "UPNP port forwarded by "+version.full
  lease_duration = 5*60 # Five minute lease time - tread lightly
  def __init__(self):
    gobject.GObject.__init__(self)
    self.igd = igd.Simple()
    self.igd.connect("mapped-external-port", self._do_mapped_external_port)
    self.igd.connect("error-mapping-port", self._do_error_mapping_port)
  def add_udp_port(self, target):
    self.igd.add_port("UDP", target.port, target.host, target.port,
                      self.lease_duration, self.lease_description)
  def _do_mapped_external_port(self, igd, proto, external_ip,
                               replaces_external_ip, external_port, local_ip,
                               local_port, description):
    external = ContactInfo(external_ip, external_port)
    internal = ContactInfo(local_ip, local_port)
    glib.idle_add(self.emit, "port-added", external, internal)
  def _do_error_mapping_port(self, igd, error, proto, external_port, local_ip,
                             local_port, description):
    if isinstance(error, gobject.GPointer):
      # god I feel awful about this. THIS IS THE DEFINITION OF A HACK
      try:
        import ctypes
        p = int(str(error)[13:-1], 16)
        m = ctypes.cast(p, ctypes.POINTER(ctypes.c_char_p))
        m2 = ctypes.cast(p, ctypes.POINTER(ctypes.c_int))
        e = str(m[2])
        code = m2[1]
        if code == 725: #only permanent leases supported
          # try a permanent motherfucking lease
          self.igd.add_port(proto, external_port, local_ip, local_port, 0,
                            description)
          return
      except Exception as err:
        e = ""
    elif isinstance(error, gobject.GError):
      e = error.message
    else:
      e = ""
    glib.idle_add(self.emit, "add-port-error", e)
  def shutdown(self):
    self.igd.delete_all_mappings()
