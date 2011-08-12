import gtk
import glib
import gobject

class StatusLabel(gtk.Frame):
  status = gobject.property(type=bool, default=False)

  def __init__(self, text=None, status=None):
    gtk.Frame.__init__(self)
    self.set_shadow_type(gtk.SHADOW_NONE)

    self._prop_handle = None

    self.hbox = gtk.HBox()
    self.hbox.set_spacing(5)
    self.add(self.hbox)

    self.label = gtk.Label(text)
    self.hbox.pack_start(self.label, True, True)

    self.image = gtk.Image()
    self.hbox.pack_end(self.image, False, True)

    self.connect("notify::status", self._do_notify_status)

    self.set_status(status)

    self.label.show()
    self.image.show()

    if status is None:
      self.set_sensitive(False)

  def set_status(self, status):
    self.status = status

  def get_status(self):
    return self.status

  def _do_notify_status(self, widget, pspec):
    self.set_sensitive(True)
    if self.status:
      self.image.set_from_stock(gtk.STOCK_YES, gtk.ICON_SIZE_SMALL_TOOLBAR)
    else:
      self.image.set_from_stock(gtk.STOCK_NO, gtk.ICON_SIZE_SMALL_TOOLBAR)

  def attach_to_prop(self, obj, prop):
    self.detach_prop()
    h = obj.connect("notify::{0:s}".format(prop), self._do_notified)
    self._prop_handle = (obj, h)
    self.set_status(obj.get_property(prop))

  def detach_prop(self):
    self.set_sensitive(False)
    if self._prop_handle is not None:
      self._prop_handle[0].disconnect(self._prop_handle[1])
      self._prop_handle = None

  def _do_notified(self, obj, spec):
    self.set_status(obj.get_property(spec.name))
