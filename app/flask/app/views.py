# ANCHOR - Top
import os
from app import app
from flask import  render_template, send_from_directory, jsonify

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import atexit
import re
import json

hostname = os.getenv('VMWARE_HOST')
username = os.getenv('VMWARE_USER')
password = os.getenv('VMWARE_PASSWORD')


def connect_to_host(hostname, username, password, port=443):
    context = None
    if hasattr(ssl, '_create_unverified_context'):
        context = ssl._create_unverified_context()
    si = SmartConnect(host=hostname, user=username, pwd=password, port=port, sslContext=context)
    atexit.register(Disconnect, si)
    return si


def start_vm(si, vm_name):
    content = si.RetrieveContent()
    vm = None
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    for managed_object_ref in container.view:
        if managed_object_ref.name == vm_name:
            vm = managed_object_ref
            break
    container.Destroy()
    if vm:
        if vm.runtime.powerState != vim.VirtualMachinePowerState.poweredOn:
            task = vm.PowerOnVM_Task()
            return "success"
        else:
            return "failed, already running"
    else:
        return "failed, not found"


def pause_vm(si, vm_name):
    content = si.RetrieveContent()
    vm = None
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    for managed_object_ref in container.view:
        if managed_object_ref.name == vm_name:
            vm = managed_object_ref
            break
    container.Destroy()
    if vm:
        if vm.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
            task = vm.SuspendVM_Task()
            return "success"
        elif vm.runtime.powerState == vim.VirtualMachinePowerState.suspended:
            return "failed, already paused"
        else:
            print(f"VM {vm_name} is not in a state that can be paused.")
    else:
        return "failed, not found"

def get_all_vms(si):
    vm_list = []
    content = si.RetrieveContent()
    container = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    for vm in container.view:
        vm_list.append(vm)
    container.Destroy()
    return vm_list

def get_onefs_vms(vms):
    r = []
    for vm in vms:
        if re.search(r"OneFS-", vm.name):
            r.append(vm)
    return r

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

##############################################################################
# ANCHOR - Static Routes

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
 
##############################################################################
# ANCHOR - UI Routes
@app.route("/")
def index():
    onefs_vms = []
    si = connect_to_host(hostname, username, password)
    vms = get_all_vms(si)
    vms = get_onefs_vms(vms)
    index, vms = get_index(vms)
    simulators = get_simulators()
    print(os.getcwd)
    return render_template("index.html", vms=vms, index=index, simulators=simulators)

@app.route("/start/<name>")
def start(name):
    si = connect_to_host(hostname, username, password)
    start_vm(si, name)
    return render_template("start.html", name=name)

@app.route("/stop/<name>")
def stop(name):
    si = connect_to_host(hostname, username, password)
    pause_vm(si, name)
    return render_template("stop.html", name=name)

@app.route("/status/<name>")
def status(name):
    si = connect_to_host(hostname, username, password)
    vms = get_all_vms(si)
    for vm in vms:
        if vm.name == name: 
            return jsonify({ "state":vm.runtime.powerState})
    return jsonify("error")