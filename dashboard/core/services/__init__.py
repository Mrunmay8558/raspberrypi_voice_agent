"""Dashboard service layer.

Service modules encapsulate host-specific operations such as shell command
execution, NetworkManager interaction, Bluetooth control, and systemd status
inspection. Controllers call this layer to keep transport-specific details out
of the API routes.
"""
