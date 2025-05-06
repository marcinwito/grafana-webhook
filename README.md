# Grafana Webhook Listener

A lightweight and configurable webhook server for Grafana alerts that can execute system commands upon receiving notifications. Perfect for integrating with notification systems (e.g., SMS).

## Features

- Receives and processes Grafana alert webhooks
- Executes configured system commands for each alert
- Phone number filtering (blacklist)
- Message prefixing with alert status (`[FIRING]`, `[RESOLVED]`, etc.)
- Detailed logging (access and webhook logs)
- Asynchronous processing in threads
- Support for multiple phone numbers per alert
- TCP Keepalive support for stable connections

## Configuration

Edit `grafana_webhook_listener.py` to customize:

```python
# Server Configuration
HOST = '127.0.0.1'            # Listening interface
PORT = 9123                   # Server port
LOG_FILE = 'webhook.log'      # Webhook log file
ACCESS_LOG_FILE = 'access.log' # Access log file
LOG_JSON_BODY = True          # Log full JSON body

# Command Configuration
SYSTEM_COMMAND = ['echo']     # Base command to execute
SYSTEM_COMMAND_ARGS_ORDER = ['phoneNumbers', 'message'] # Argument order

# Blacklist Configuration
BLACKLISTED_NUMBERS = ["999888777", "555555555"]
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/marcinwito/grafana-webhook.git
cd grafana-webhook
```

2. Install dependencies:
```bash
pip install klein twisted
```

## Usage

1. Start the server:
```bash
python grafana_webhook_listener.py
```

2. Configure Grafana alerts to send webhooks to `http://your-server:9123/`

## Grafana Alert Configuration

Add the following labels and annotations to your Grafana alert rules:

- Label `phoneNumbers`: Phone number(s) for notifications (comma-separated)
- Annotation `message`: Notification message content

Example Grafana alert rule:
```yaml
groups:
  - name: example
    rules:
      - alert: HighCPUUsage
        expr: cpu_usage > 80
        for: 5m
        labels:
          phoneNumbers: "123456789,987654321"
        annotations:
          message: "High CPU usage detected: {{ $value }}%"
```

## Logging

The server maintains two types of logs:

1. `webhook.log`: Contains detailed webhook processing information
2. `access.log`: Contains HTTP access logs with timing information

## Requirements

- Python 3.6+
- Klein
- Twisted

## Security Considerations

- The server listens on localhost by default (`127.0.0.1`)
- Consider implementing additional security measures for production use:
  - Authentication
  - HTTPS
  - IP whitelisting
  - Rate limiting

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is licensed under the MIT License - see the LICENSE file for details. 