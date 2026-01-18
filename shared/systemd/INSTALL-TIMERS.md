# Installing Database Timers

Run these commands with sudo to install the automated timers:

```bash
# Copy service files
sudo cp /opt/leveredge/shared/systemd/db-backup.service /etc/systemd/system/
sudo cp /opt/leveredge/shared/systemd/db-backup.timer /etc/systemd/system/
sudo cp /opt/leveredge/shared/systemd/db-health.service /etc/systemd/system/
sudo cp /opt/leveredge/shared/systemd/db-health.timer /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start timers
sudo systemctl enable db-backup.timer db-health.timer
sudo systemctl start db-backup.timer db-health.timer

# Verify
systemctl list-timers | grep db-
```

## Manual Testing

```bash
# Test backup manually
sudo systemctl start db-backup.service
journalctl -u db-backup.service -n 20

# Test health check manually
sudo systemctl start db-health.service
journalctl -u db-health.service -n 20

# Check logs
tail -f /opt/leveredge/logs/db-backup.log
tail -f /opt/leveredge/logs/db-health.log
```

## Timer Schedule

- **db-backup**: Daily at 2:00 AM
- **db-health**: Every hour at :00
