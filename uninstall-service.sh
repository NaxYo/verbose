#!/bin/bash
# Uninstall Verbose systemd user service

set -e

USER_SERVICE_DIR="$HOME/.config/systemd/user"

echo "Uninstalling Verbose systemd user service..."

# Stop service if running
systemctl --user stop verbose.service 2>/dev/null || true

# Disable service
systemctl --user disable verbose.service 2>/dev/null || true

# Remove service file
rm -f "$USER_SERVICE_DIR/verbose.service"

# Reload systemd user daemon
systemctl --user daemon-reload

echo ""
echo "✓ Verbose service uninstalled successfully!"
echo ""
