# main.py
import os
import json
from datetime import datetime, timedelta
from connectors.netbox_connector import NetBoxConnector
from connectors.vcenter_connector import VCenterConnector
from processors.data_processor import DataProcessor
import logging
from flask import Flask, render_template, request, flash
from flask_wtf import CSRFProtect, FlaskForm
from wtforms import SubmitField
import threading
import time
from dotenv import load_dotenv




# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filename='/var/log/sync_vcenter_netbox.log',
                    filemode='a')

app = Flask(__name__)
csrf = CSRFProtect(app)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a secure random key

status = {
    'last_run': 'N/A',
    'status': 'Idle',
    'is_running': False
}
log_content = 'No log available.'

# Lock to prevent concurrent synchronization
sync_lock = threading.Lock()

def synchronize():
    global status, log_content
    with sync_lock:
        if status['is_running']:
            return
        status['is_running'] = True
        status['status'] = 'Running'
        try:
            # Configuration
            netbox_url = os.getenv("NETBOX_URL")
            netbox_token = os.getenv("NETBOX_TOKEN")
            vcenter_host = os.getenv("VCENTER_HOST")
            vcenter_user = os.getenv("VCENTER_USER")
            vcenter_password = os.getenv("VCENTER_PASSWORD")
            output_file = os.getenv("OUTPUT_FILE")
            append_mode = os.getenv("APPEND_MODE", "False").lower() == "true"
            vm_limit = os.getenv("VM_LIMIT", None )

            # Connect to vCenter and get all clusters
            vcenter_connector = VCenterConnector(vcenter_host, vcenter_user, vcenter_password, vm_limit)
            vcenter_connector.connect()
            vcenter_clusters = vcenter_connector.get_all_clusters()
            vcenter_connector.disconnect()

            # Connect to NetBox and build cluster mapping
            netbox_connector = NetBoxConnector(netbox_url, netbox_token, vcenter_clusters)

            # Initialize DataProcessor
            data_processor = DataProcessor(netbox_connector.netbox, netbox_connector.cluster_mapping, vcenter_connector, output_file)

            # Process VMs
            data_processor.process_vms()

            # Update status
            status['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            status['status'] = 'Success'
        except Exception as e:
            logging.error(f"Synchronization failed: {e}")
            status['status'] = f'Failed: {e}'
        finally:
            status['is_running'] = False
            # Read log file
            try:
                with open('/var/log/sync_vcenter_netbox.log', 'r') as f:
                    log_content = f.read()
            except:
                log_content = 'No log available.'

class SyncForm(FlaskForm):
    submit = SubmitField('Trigger Synchronization')

@app.route('/', methods=['GET', 'POST'])
def index():
    form = SyncForm()
    if form.validate_on_submit():
        if not sync_lock.locked():
            threading.Thread(target=synchronize).start()
        else:
            flash('Synchronization already in progress.', 'warning')
    return render_template('index.html', status=status, log=log_content, form=form)

@app.route('/trigger_sync', methods=['POST'])
@csrf.exempt  # Remove this if using CSRF protection here
def trigger_sync():
    if not sync_lock.locked():
        threading.Thread(target=synchronize).start()
        return 'Synchronization started.'
    else:
        return 'Synchronization already in progress.', 409

def scheduled_synchronize():
    while True:
        now = datetime.now()
        if now.hour == 23 and now.minute == 0:
            synchronize()
            # Sleep for a minute to avoid immediate retrigger
            time.sleep(60)
        time.sleep(60)

if __name__ == "__main__":
    # Start scheduled synchronization in a separate thread
    scheduled_thread = threading.Thread(target=scheduled_synchronize)
    scheduled_thread.daemon = True
    scheduled_thread.start()
    
    # Run the Flask app
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 8080)),
        debug=os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    )