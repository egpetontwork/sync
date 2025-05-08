from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim
import ssl
import json
from datetime import datetime
import os
from processors.data_processor import VM


class VCenterConnector:
    def __init__(self, host, user, password, limit = None):
        self.host = host
        self.user = user
        self.password = password
        self.si = None
        self.limit = limit

    def connect(self):
        print(f"Connecting to vCenter at {self.host}...")
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        self.si = SmartConnect(host=self.host,
                               user=self.user,
                               pwd=self.password,
                               sslContext=context)
        print("Connected to vCenter.")

    def disconnect(self):
        if self.si:
            print("Disconnecting from vCenter...")
            Disconnect(self.si)
            print("Disconnected from vCenter.")

    def get_vm_info(self):
        print("Retrieving VM information...")
        content = self.si.RetrieveContent()
        container = content.rootFolder
        view_type = [vim.VirtualMachine]
        recursive = True

        container_view = content.viewManager.CreateContainerView(
            container, view_type, recursive)

        vm_list = container_view.view
        vm_info_list = []

        for vm in vm_list:
            if self.limit is not None and len(vm_info_list) >= self.limit:
                break
            try:
                vm_info = self.retrieve_vm_details(vm)
                if vm_info:
                    vm_info_list.append(vm_info)
                    print(f"Retrieved information for VM: {vm.name}")
            except AttributeError as e:
                print(f"Error retrieving information for VM {vm.name}: {e}")
                continue
        return vm_info_list

    def retrieve_vm_details(self, vm):
        if vm.config is None:
            print(f"Skipping VM {vm.name} due to missing configuration.")
            return None

        if vm.runtime.host is None:
            print(f"Skipping VM {vm.name} due to missing host information.")
            return None

        ipv6_addresses = self.get_ipv6_addresses(vm)
        if vm.runtime.host and vm.runtime.host.parent and vm.runtime.host.parent.parent:
            site = vm.runtime.host.parent.parent.name
            cluster = vm.runtime.host.parent.name
        else:
            site = "Unknown"
            cluster = "Unknown"
        platform = vm.config.guestFullName if vm.config.guestFullName else "Unknown"
        vm_id = vm.config.uuid if vm.config.uuid else vm.moId

        ip_address = vm.guest.ipAddress if vm.guest and vm.guest.ipAddress else "Unknown"

        created = vm.config.createDate.strftime('%Y-%m-%d %H:%M:%S') if vm.config.createDate else "Unknown"
        change_version = vm.config.changeVersion if vm.config.changeVersion else "Unknown"

        vm_info = VM(
            vm_id=vm_id,
            name=vm.name,
            status=vm.runtime.powerState,
            site=site,
            cluster=cluster,
            vcpus=vm.config.hardware.numCPU,
            memory_mb=vm.config.hardware.memoryMB ,
            disk=int(sum(disk.capacityInKB / 1024 for disk in vm.config.hardware.device if isinstance(disk, vim.vm.device.VirtualDisk))),
            ip_address=ip_address,
            created=created,
            ipv6=', '.join(ipv6_addresses) if ipv6_addresses else "Unknown",
            comments=vm.config.annotation if vm.config.annotation else "No comments",
            platform=platform,
            last_update=change_version,
            last_checked=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        return vm_info

    def get_ipv6_addresses(self, vm):
        ipv6_addresses = []
        if vm.guest and vm.guest.net:
            for net in vm.guest.net:
                if net.ipAddress:
                    for ip_address in net.ipAddress:
                        if ':' in ip_address:  # IPv6 addresses contain colons
                            ipv6_addresses.append(ip_address)
        return ipv6_addresses

    def save_to_json(self, data, filename, append=False):
        data_dicts = [vm.to_dict() for vm in data]
        if append and os.path.exists(filename):
            print(f"Appending VM information to {filename}...")
            existing_data = self.read_json(filename)
            updated_data = self.update_existing_data(existing_data, data_dicts)
            self.write_json(filename, updated_data)
            print(f"VM information updated in {filename}.")
        else:
            print(f"Saving VM information to {filename}...")
            self.write_json(filename, data_dicts)
            print(f"VM information saved to {os.path.abspath(filename)}.")

    def read_json(self, filename):
        with open(filename, 'r') as f:
            return json.load(f)

    def write_json(self, filename, data):
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

    def update_existing_data(self, existing_data, new_data):
        existing_vm_dict = {vm['vm_id']: vm for vm in existing_data}
        for vm_dict in new_data:
            vm_id = vm_dict['vm_id']
            if vm_id in existing_vm_dict:
                existing_vm_dict[vm_id].update(vm_dict)
            else:
                existing_vm_dict[vm_id] = vm_dict
        return list(existing_vm_dict.values())

    def get_all_clusters(self):
        print("Retrieving all clusters from vCenter...")
        content = self.si.RetrieveContent()
        view_type = [vim.ClusterComputeResource]
        recursive = True
        container_view = content.viewManager.CreateContainerView(
            content.rootFolder, view_type, recursive)
        clusters = [cluster.name for cluster in container_view.view]
        container_view.Destroy()
        print(f"Retrieved {len(clusters)} clusters.")
        return clusters