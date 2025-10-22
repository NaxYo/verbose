#!/bin/bash
# Install Verbose as a systemd user service for auto-start on boot

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/verbose.service"
USER_SERVICE_DIR="$HOME/.config/systemd/user"

echo "Installing Verbose systemd user service..."

# Create user systemd directory if it doesn't exist
mkdir -p "$USER_SERVICE_DIR"

# Copy service file
cp "$SERVICE_FILE" "$USER_SERVICE_DIR/verbose.service"

# Reload systemd user daemon
systemctl --user daemon-reload

# Enable service to start on boot
systemctl --user enable verbose.service

# Start service now
systemctl --user start verbose.service

echo ""
echo "✓ Verbose service installed successfully!"
echo ""
echo "Useful commands:"
echo "  systemctl --user status verbose    # Check status"
echo "  systemctl --user stop verbose      # Stop service"
echo "  systemctl --user restart verbose   # Restart service"
echo "  systemctl --user disable verbose   # Disable auto-start"
echo "  journalctl --user -u verbose -f    # View logs"
echo ""
