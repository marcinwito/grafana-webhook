import logging
import json
from klein import Klein
# We need Request from Twisted for typing and response manipulation
from twisted.web.server import Request, Site
import time
import subprocess # Import subprocess module
# Import reactor to run blocking calls in threads
from twisted.internet import reactor, threads

# --- Configuration ---
HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 5001       # Port the server will listen on
LOG_FILE = 'webhook.log' # File to write webhook logs
ACCESS_LOG_FILE = 'access.log' # File to write access logs
LOG_JSON_BODY = True # Control logging of the full JSON body

# Command configuration
SYSTEM_COMMAND = ['dir'] # The base command to execute (list of strings)
SYSTEM_COMMAND_ARGS_ORDER = ['phoneNumbers', 'message'] # Order of args to append: 'phoneNumbers', 'message'
# Example: SYSTEM_COMMAND = ['/path/to/script.sh']
# Example: SYSTEM_COMMAND_ARGS_ORDER = ['message', 'phoneNumbers']

# --- End Configuration ---

# --- Main Logging Configuration (Webhooks) ---
webhook_logger = logging.getLogger('webhook')
webhook_logger.setLevel(logging.INFO)
webhook_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Handler for webhook.log file
webhook_file_handler = logging.FileHandler(LOG_FILE)
webhook_file_handler.setFormatter(webhook_formatter)
webhook_logger.addHandler(webhook_file_handler)

# Console handler (optional, if you want to see webhook logs in the console)
# webhook_stream_handler = logging.StreamHandler()
# webhook_stream_handler.setFormatter(webhook_formatter)
# webhook_logger.addHandler(webhook_stream_handler)
# --- End Main Logging Configuration ---


# --- Access Logging Configuration ---
access_logger = logging.getLogger('access')
access_logger.setLevel(logging.INFO)
access_formatter = logging.Formatter('%(asctime)s - %(message)s') # Simpler format for access logs

# Handler for access.log file
access_file_handler = logging.FileHandler(ACCESS_LOG_FILE)
access_file_handler.setFormatter(access_formatter)
access_logger.addHandler(access_file_handler)

# Optional: Console handler for access logs
access_stream_handler = logging.StreamHandler()
access_stream_handler.setFormatter(access_formatter)
access_logger.addHandler(access_stream_handler)
# --- End Access Logging Configuration ---

# Function to run the command in a separate thread for a single phone number
def run_system_command(phone_number, message_content, alert_name):
    """Runs the configured system command in a thread for a single phone number."""
    try:
        # Build the command dynamically based on configuration
        command_base = list(SYSTEM_COMMAND) # Start with a copy of the base command
        # Map now uses the single phone_number argument
        args_map = {
            'phoneNumbers': phone_number, # Use the single number passed
            'message': message_content
        }

        final_command = command_base
        for arg_key in SYSTEM_COMMAND_ARGS_ORDER:
            if arg_key in args_map:
                # Ensure the argument is converted to string
                final_command.append(str(args_map[arg_key]))
            else:
                webhook_logger.warning(f"[Thread] Configured argument key '{arg_key}' not found in available data for alert '{alert_name}'. Skipping.")

        webhook_logger.info(f"[Thread] Running command for alert '{alert_name}' (Number: {phone_number}): {final_command}")
        result = subprocess.run(final_command, capture_output=True, text=True, check=False, shell=False)

        webhook_logger.info(f"[Thread] Command for alert '{alert_name}' (Number: {phone_number}) finished with exit code: {result.returncode}")
        if result.stdout:
            webhook_logger.info(f"[Thread] Command stdout:\n{result.stdout.strip()}")
        if result.stderr:
            webhook_logger.warning(f"[Thread] Command stderr:\n{result.stderr.strip()}")

    except FileNotFoundError:
            webhook_logger.error(f"[Thread] Error running command for alert '{alert_name}': Command '{SYSTEM_COMMAND[0]}' not found. Make sure it's in the system PATH.")
    except Exception as cmd_err:
        webhook_logger.error(f"[Thread] Error executing command for alert '{alert_name}' (Number: {phone_number}): {cmd_err}")

# Initialize Klein application
app = Klein()

@app.route('/', methods=['POST']) # Methods should be strings
def grafana_webhook(request: Request):
    """Receives a webhook from Grafana, logs its content, checks for specific labels, runs a command, and logs access."""
    start_time = time.monotonic() # Record start time here
    status_code = 500 # Default error code
    response_body = {"status": "error", "message": "Internal server error"} # Default response

    try:
        webhook_logger.info("Received webhook...")

        content_type = request.getHeader('content-type')
        is_json = content_type and 'application/json' in content_type.lower()

        if is_json:
            try:
                # Read content and parse JSON
                raw_body = request.content.read()
                data = json.loads(raw_body)
                webhook_logger.info("Webhook content (JSON):")
                # Conditionally log the full JSON body based on the config flag
                if LOG_JSON_BODY:
                    webhook_logger.info(json.dumps(data, indent=4))
                else:
                    webhook_logger.info("(Full JSON body logging is disabled)")

                # --- Check alerts for labels and run command ---
                if 'alerts' in data and isinstance(data['alerts'], list):
                    for i, alert in enumerate(data['alerts']):
                        alert_name = alert.get('labels', {}).get('alertname', f'alert_{i+1}')
                        labels = alert.get('labels', {})
                        annotations = alert.get('annotations', {})

                        phone_numbers_val = labels.get('phoneNumbers')
                        message_content = annotations.get('message')

                        # Check if both base values exist
                        if phone_numbers_val is not None and message_content:
                            # Ensure phone_numbers_val is a list
                            if not isinstance(phone_numbers_val, list):
                                phone_numbers_list = [phone_numbers_val]
                            else:
                                phone_numbers_list = phone_numbers_val

                            webhook_logger.info(f"Alert '{alert_name}': Found phoneNumbers (label: {phone_numbers_list}) and message (annotation). Scheduling command execution for each number.")

                            # Iterate through each phone number and schedule a command
                            for single_phone_number in phone_numbers_list:
                                webhook_logger.info(f"  - Scheduling for number: {single_phone_number}")
                                d = threads.deferToThread(run_system_command, single_phone_number, message_content, alert_name)
                                d.addErrback(lambda f, num=single_phone_number: webhook_logger.error(f"Error in thread execution for number {num}: {f.value}"))
                        else:
                            missing = []
                            if phone_numbers_val is None: # Check for None explicitly
                                missing.append('phoneNumbers label')
                            if not message_content:
                                missing.append('message annotation')
                            webhook_logger.info(f"Alert '{alert_name}': Missing required fields: {', '.join(missing)}. Skipping command execution.")
                else:
                    webhook_logger.info("Webhook JSON does not contain an 'alerts' list.")
                # --- End Check alerts ---

                status_code = 200
                response_body = {"status": "success", "message": "Webhook received and processing scheduled"}

            except json.JSONDecodeError as e:
                webhook_logger.error(f"JSON parsing error: {e}")
                webhook_logger.error(f"Raw data: {raw_body.decode('utf-8', errors='ignore')}")
                status_code = 400
                response_body = {"status": "error", "message": "Invalid JSON received"}
        else:
            # If not JSON, log raw data
            raw_data = request.content.read().decode('utf-8', errors='ignore')
            webhook_logger.warning("Received non-JSON data:")
            webhook_logger.warning(raw_data)
            status_code = 400
            response_body = {"status": "error", "message": "Request content type was not JSON"}

    except Exception as e:
        webhook_logger.error(f"Unexpected error processing webhook: {e}", exc_info=True)
        # Error logging already happened, status_code and response_body are default
        try:
             # Try to log raw data even on other errors
             request.content.seek(0) # Reset read pointer if already read
             raw_data_on_error = request.content.read().decode('utf-8', errors='ignore')
             webhook_logger.error(f"Raw data on error: {raw_data_on_error}")
        except Exception as data_err:
             webhook_logger.error(f"Could not get raw data on error: {data_err}")

    finally:
        # --- Access Logging (always executed at the end) ---
        duration_ms = (time.monotonic() - start_time) * 1000
        remote_addr = request.client.host
        method = request.method.decode('utf-8')
        path = request.path.decode('utf-8')
        protocol = request.clientproto.decode('utf-8')

        log_message = f"{remote_addr} - \"{method} {path} {protocol}\" {status_code} - {duration_ms:.2f} ms"
        if status_code >= 400:
             access_logger.warning(log_message)
        else:
             access_logger.info(log_message)
        # --- End Access Logging ---

        # Set response in Klein
        request.setResponseCode(status_code)
        request.setHeader('Content-Type', 'application/json')
        return json.dumps(response_body).encode('utf-8')

if __name__ == '__main__':
    access_logger.info(f"Starting webhook server (Klein) on {HOST}:{PORT} with TCP Keepalives enabled")
    webhook_logger.info(f"Server configured to listen on {HOST}:{PORT}, webhook logs in {LOG_FILE}")
    webhook_logger.info(f"Log full JSON body: {LOG_JSON_BODY}")
    webhook_logger.info(f"System command configured: {SYSTEM_COMMAND} with args order: {SYSTEM_COMMAND_ARGS_ORDER}") # Log command config

    # Get the Klein app resource
    resource = app.resource()
    # Create a Site object wrapping the Klein resource
    factory = Site(resource)

    # Start listening with TCP Keepalives enabled, passing the Site factory
    endpoint = reactor.listenTCP(PORT, factory, interface=HOST)
    # Note: The actual socket option SO_KEEPALIVE is set by Twisted/OS
    # based on the underlying socket implementation when using listenTCP.
    # We don't need to manually set socket options here.

    access_logger.info(f"Server listening on {HOST}:{PORT}...")

    # Run the Twisted reactor
    reactor.run()
    # Remove the old app.run(HOST, PORT) 