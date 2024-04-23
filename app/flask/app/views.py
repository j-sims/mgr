import os
import ssl
import atexit
import signal
import json
import re
from flask import Flask, render_template, send_from_directory, jsonify
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim

app = Flask(__name__)

hostname = os.getenv('VMWARE_HOST')
username = os.getenv('VMWARE_USER')
password = os.getenv('VMWARE_PASSWORD')

class TimeoutException(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutException()

def create_ssl_context():
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.verify_mode = ssl.CERT_NONE
    context.check_hostname = False
    return context

def connect_to_host(hostname, username, password, port=443, timeout=10):
    context = create_ssl_context()
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    try:
        si = SmartConnect(host=hostname, user=username, pwd=password, port=port, sslContext=context)
        atexit.register(Disconnect, si)
        signal.alarm(0)  # Reset the alarm
        return si
    except TimeoutException:
        print("Connection attempt timed out.")
        return None
    except Exception as e:
        print(f"Failed to connect: {e}")
        return None

@app.route("/")
def index():
    si = connect_to_host(hostname, username, password)
    if si is None:
        return "Failed to connect to ESX host", 500
    vms = get_all_vms(si)
    vms = get_onefs_vms(vms)
    index, vms_dict = get_index(vms)
    simulators = get_simulators()
    return render_template("index.html", vms=vms_dict, index=index, simulators=simulators)

@app.route("/start/<name>")
def start(name):
    si = connect_to_host(hostname, username, password)
    if si is None:
        return render_template("error.html", error="Failed to connect to ESX host"), 500
    result = start_vm(si, name)
    return render_template("start.html", name=name, result=result)

@app.route("/stop/<name>")
def stop(name):
    si = connect_to_host(hostname, username, password)
    if si is None:
        return render_template("error.html", error="Failed to connect to ESX host"), 500
    result = pause_vm(si, name)
    return render_template("stop.html", name=name, result=result)

@app.route("/status/<name>")
def status(name):
    si = connect_to_host(hostname, username, password)
    if si is None:
        return jsonify("Failed to connect to ESX host"), 500
    vms = get_all_vms(si)
    for vm in vms:
        if vm.name == name:
            return jsonify({ "state": vm.runtime.powerState})
    return jsonify("error")

def get_all_vms(si):
    vm_list = []
    content = si.RetrieveContent()
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    for vm in container.view:
        vm_list.append(vm)
    container.Destroy()
    return vm_list

def get_onefs_vms(vms):
    return [vm for vm in vms if re.search(r"OneFS-", vm.name)]

def get_index(vms):
    index = []
    vmdict = {}
    for vm in vms:
        vmdict[vm.name] = { "name": vm.name, "state": vm.runtime.powerState}
        index.append(vm.name)
    sorted_index = sorted(index, key=lambda x: tuple(map(int, x.split('-')[1].split('.'))), reverse=True)
    return sorted_index, vmdict

def get_simulators():
    with open('app/simulators.json') as f:
        return json.load(f)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/startstop.gif')
def startstopgif():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'start-stop.gif', mimetype='image/gif')

if __name__ == '__main__':
    app.run(debug=True)
