# ANCHOR - Top
import os
from app import app
from flask import  render_template, send_from_directory, jsonify

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import atexit
import re

hostname = ''
username = ''
password = ''


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
    for vm in vms:
        if re.search(r"OneFS-", vm.name):
            onefs_vms.append(vm)
    print(onefs_vms)
    sorted_versions = sorted(onefs_vms, key=lambda x: tuple(map(int, x.split('-')[1].split('.'))), reverse=True)
    return render_template("index.html", vms=sorted_versions)

@app.route("/start/<name>")
def start(name):
    si = connect_to_host(hostname, username, password)
    start_vm(si, name)
    return render_template("wait.html", target="poweredOn")

@app.route("/stop/<name>")
def stop(name):
    si = connect_to_host(hostname, username, password)
    pause_vm(si, name)
    return render_template("wait.html", target="suspended")

@app.route("/status/<name>")
def status(name):
    si = connect_to_host(hostname, username, password)
    vms = get_all_vms(si)
    for vm in vms:
        if vm.name == name: 
            return jsonify(vm.runtime.powerState)
        else:
            return jsonify("error")