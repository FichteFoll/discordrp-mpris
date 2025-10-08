"""Handles connecting to the D-Bus session bus using jeepney."""
from jeepney.io.blocking import DBusConnection, open_dbus_connection

def open_main_connection() -> DBusConnection:
    """Connect to the D-Bus session bus and return the connection."""
    return open_dbus_connection(bus="SESSION")
