import pynetbox
import json
from datetime import datetime
import logging
import re
import os
from datetime import datetime, timedelta
import ipaddress

def slugify(text):
    # Remove special characters and replace spaces with hyphens
    slug = re.sub(r'[^\w\s-]', '', text).strip().lower()
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug


class VM:
    def __init__(self, vm_id, name, status, site, cluster, vcpus, memory_mb, disk, ip_address, created, ipv6, comments, platform, last_update, last_checked, tags=None, tenant_id=None, role_id=None):
        self.vm_id = vm_id
        self.name = name
        self.status = status
        self.site = site
        self.cluster = cluster
        self.vcpus = vcpus
        self.memory_mb = memory_mb
        self.disk = disk
        self.ip_address = ip_address
        self.created = created
        self.ipv6 = ipv6
        self.comments = comments
        self.platform = platform
        self.last_update = last_update
        self.last_checked = last_checked
        self.tags = tags if tags is not None else []
        self.tenant_id = tenant_id
        self.role_id = role_id

    @classmethod
    def from_dict(cls, vm_dict):
        vm_dict_lower = {k.lower(): v for k, v in vm_dict.items()}
        tags = vm_dict_lower.get("tags", [])
        tenant_id = vm_dict_lower.get("tenant_id", None)
        role_id = vm_dict_lower.get("role_id", None)
        return cls(
            vm_id=vm_dict_lower.get("vm_id", None),
            name=vm_dict_lower.get("name", "Unknown"),
            status=vm_dict_lower.get("status", "Unknown"),
            site=vm_dict_lower.get("site", "Unknown"),
            cluster=vm_dict_lower.get("cluster", "Unknown"),
            vcpus=vm_dict_lower.get("vcpus", 0),
            memory_mb=vm_dict_lower.get("memory_mb", 0),
            disk=vm_dict_lower.get("disk", 0),
            ip_address=vm_dict_lower.get("ip_address", "Unknown"),
            created=vm_dict_lower.get("created", "Unknown"),
            ipv6=vm_dict_lower.get("ipv6", "Unknown"),
            comments=vm_dict_lower.get("comments", ""),
            platform=vm_dict_lower.get("platform", "Unknown"),
            last_update=vm_dict_lower.get("last_update", "Unknown"),
            last_checked=vm_dict_lower.get("last_checked", "Unknown"),
            tags=tags,
            tenant_id=tenant_id,
            role_id=role_id
        )

    def to_dict(self):
        return {
            'vm_id': self.vm_id,
            'name': self.name,
            'status': self.status,
            'site': self.site,
            'cluster': self.cluster,
            'vcpus': self.vcpus,
            'memory_mb': self.memory_mb,
            'disk': self.disk,
            'ip_address': self.ip_address,
            'created': self.created,
            'ipv6': self.ipv6,
            'comments': self.comments,
            'platform': self.platform,
            'last_update': self.last_update,
            'last_checked': self.last_checked,
            'tags': self.tags,
            'tenant_id': self.tenant_id,
            'role_id': self.role_id
        }

    def set_status_failed(self, reason):
        self.status = 'failed'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        new_comment = f"\nUpdated on {timestamp}: {reason}"
        self.comments += new_comment
    
    def parse_dates(self):
        for attr in ['created', 'last_update', 'last_checked']:
            date_str = getattr(self, attr)
            if date_str != "Unknown":
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    setattr(self, attr, date_obj)
                except ValueError:
                    setattr(self, attr, None)
            else:
                setattr(self, attr, None)    


logging.basicConfig(level=logging.INFO)



class DataProcessor:
    def __init__(self, netbox_api, cluster_mapping, vcenter_connector, json_file=None):
        self.netbox = netbox_api
        self.cluster_mapping = cluster_mapping
        self.vcenter_connector = vcenter_connector
        self.json_file = json_file
        self.SYNC_TAG = "SYNC_FROM_VCENTER"
        self.ORPHANED_TAG = "ORPHANED_FROM_SYNC"
        self.status_mapping = {
            'poweredOn': 'active',
            'poweredOff': 'offline',
            # Add more mappings as necessary
        }
        logging.info(f"JSON file set to: {self.json_file}")
        try:
            self.custom_fields = self.get_custom_fields()
            self.cf_names = [cf.name for cf in self.custom_fields]
            logging.info(f"Custom fields names: {self.cf_names}")
        except Exception as e:
            logging.error(f"Error initializing custom fields: {e}")
            self.cf_names = []
        
        
    def get_custom_fields(self):
        return self.netbox.extras.custom_fields.all()    

    def add_tag_to_vm(self, vm_netbox, new_tag_name):
        # Define the two specific tags
        tag_sync = self.SYNC_TAG
        tag_orphaned = self.ORPHANED_TAG

        # Retrieve existing tags
        existing_tags = {tag.name: tag for tag in vm_netbox.tags}

        # If new_tag_name is already present, do nothing
        if new_tag_name in existing_tags:
            logging.info(f"VM '{vm_netbox.name}' already has tag '{new_tag_name}'. No action needed.")
            return

        # Check if any of the specific tags is present and not the new tag
        for tag_name in [tag_sync, tag_orphaned]:
            if tag_name in existing_tags and tag_name != new_tag_name:
                # Remove the old specific tag
                vm_netbox.tags.remove(existing_tags[tag_name])
                logging.info(f"Removed tag '{tag_name}' from VM '{vm_netbox.name}'.")

        # Add the new tag
        # Check if the new tag exists in NetBox
        try:
            tag = self.netbox.extras.tags.get(name=new_tag_name)
        except Exception as e:
            tag = None
            logging.warning(f"Failed to retrieve tag '{new_tag_name}': {e}")
        if not tag:
            # Create the new tag if it doesn't exist
            tag = self.netbox.extras.tags.create(name=new_tag_name)
            logging.info(f"Created new tag '{new_tag_name}'.")
        vm_netbox.tags.append(tag)
        logging.info(f"Added new tag '{new_tag_name}' to VM '{vm_netbox.name}'.")

        # Save the updated VM
        vm_netbox.save()
        logging.info(f"Saved updated tags for VM '{vm_netbox.name}'.")



    def _set_vm_attributes(self, vm_netbox, vm, custom_fields_data, cluster, site, comments=None):
        if cluster and site:
            # Check if the cluster's site matches the VM's site
            if cluster.site.id != site.id:
                logging.error(f"Cluster {cluster.name} is not assigned to site {site.name}. Skipping cluster assignment for VM {vm_netbox.name}.")
                vm_netbox.cluster = None  # Remove cluster assignment to prevent the 400 error
            else:
                # Proceed with setting the cluster if it's assigned to the correct site
                vm_netbox.cluster = cluster
        elif cluster:
            # If site is None, log a warning
            logging.warning(f"Site is not set for VM {vm_netbox.name}. Cannot set cluster.")
        elif site:
            # If cluster is None, decide whether to assign a default cluster or skip
            logging.warning(f"Cluster is not set for VM {vm_netbox.name}.")
        else:
            # Both cluster and site are None, log an error
            logging.error(f"Neither cluster nor site is set for VM {vm_netbox.name}. Cannot update VM attributes.")

        # Set other VM attributes
        vm_netbox.status = self.status_mapping.get(vm.status, 'active')
        vm_netbox.platform = self.get_platform_id(vm.platform)
        vm_netbox.vcpus = vm.vcpus
        vm_netbox.memory = vm.memory_mb
        vm_netbox.disk = vm.disk

        vm_netbox.custom_fields = custom_fields_data
        if comments:
            vm_netbox.comments = comments
        else:
            vm_netbox.comments = vm.comments

        # Save the VM object
        vm_netbox.save()
    def _set_vm_tags(self, vm_netbox, tags):
        existing_tags = {tag.name for tag in vm_netbox.tags}
        for tag_name in tags:
            if tag_name not in existing_tags:
                tag = self.netbox.extras.tags.get(name=tag_name)
                if not tag:
                    tag = self.netbox.extras.tags.create(name=tag_name)
                vm_netbox.tags.append(tag)
        vm_netbox.save()

    def _handle_interfaces(self, vm_netbox, ip_address, is_update=False):
        if is_update:
            # During update, do not create a new interface if it doesn't exist
            interface = self.get_or_create_interface(vm_netbox, create_if_not_exists=True)
            if interface:
                self.assign_ip_to_interface(interface, ip_address)
                # Compare and update VM status
            else:
                logging.warning(f"Interface 'ens192' not found for VM {vm_netbox.name}. No IP assigned.")
        else:
            # During creation, create the interface if it doesn't exist
            interface = self.get_or_create_interface(vm_netbox)
            self.assign_ip_to_interface(interface, ip_address)
            # Compare and update VM status
            #self.compare_and_update_vm_status(vm_netbox, ip_address)

    def create_vm_in_netbox(self, vm, netbox_cluster_id, netbox_site_id):
        status = self.status_mapping.get(vm.status, 'active')
        platform_id = self.get_platform_id(vm.platform)
        ip_addresses = [vm.ip_address] if vm.ip_address != "Unknown" else []

        custom_fields_data = {}
        if 'created' in self.cf_names and vm.created:
            custom_fields_data['created'] = vm.created.isoformat()
        if 'last_update' in self.cf_names and vm.last_update:
            custom_fields_data['last_update'] = vm.last_update.isoformat()
        if 'last_checked' in self.cf_names and vm.last_checked:
            custom_fields_data['last_checked'] = vm.last_checked.isoformat()

        comments = vm.comments

        tag_names = vm.tags
        tag_ids = []
        for tag_name in tag_names:
            tag = self.netbox.extras.tags.get(name=tag_name)
            if tag:
                tag_ids.append(tag.id)
            else:
                tag = self.netbox.extras.tags.create(name=tag_name)
                tag_ids.append(tag.id)

        # Retrieve the site object from NetBox
        site = self.netbox.dcim.sites.get(netbox_site_id)
        if not site:
            logging.error(f"Site with ID {netbox_site_id} not found in NetBox. Cannot create VM {vm.name}.")
            return

        # Retrieve the cluster object from NetBox
        cluster = self.netbox.virtualization.clusters.get(netbox_cluster_id)
        if not cluster:
            logging.error(f"Cluster with ID {netbox_cluster_id} not found in NetBox. Cannot create VM {vm.name}.")
            return

        try:
            vm_netbox = self.netbox.virtualization.virtual_machines.create(
                name=vm.name,
                status=status,
                cluster=netbox_cluster_id,
                site=site.id,
                vcpus=vm.vcpus,
                memory=vm.memory_mb,
                disk=vm.disk,
                platform=platform_id,
                comments=comments,
                custom_fields=custom_fields_data,
                tenant=vm.tenant_id,
                role=vm.role_id,
                tags=tag_ids
            )
            if vm_netbox:
                # Pass cluster and site to _set_vm_attributes
                self._set_vm_attributes(vm_netbox, vm, custom_fields_data, cluster, site)
                self._handle_interfaces(vm_netbox, vm.ip_address)
                self.add_tag_to_vm(vm_netbox, self.SYNC_TAG)
                logging.info(f"VM {vm.name} created in NetBox.")
            else:
                logging.error(f"Failed to create VM {vm.name} in NetBox.")
        except Exception as e:
            logging.error(f"An error occurred while creating VM {vm.name}: {e}")


    def _update_vm_cluster_and_site(self, vm, vm_netbox):
        # Get expected cluster and site IDs from vCenter data
        expected_cluster_name = vm.cluster
        cluster_map = self.cluster_mapping.get(expected_cluster_name, self.cluster_mapping.get("Unknown", {}))
        expected_cluster_id = cluster_map.get("netbox_cluster_id")
        expected_site_id = cluster_map.get("netbox_site_id")

        # Retrieve the cluster object from NetBox
        if expected_cluster_id:
            cluster = self.netbox.virtualization.clusters.get(id=expected_cluster_id)
            if not cluster:
                # Fallback to "Unknown" cluster
                unknown_cluster_map = self.cluster_mapping.get("Unknown", {})
                unknown_cluster_id = unknown_cluster_map.get("netbox_cluster_id")
                if unknown_cluster_id:
                    cluster = self.netbox.virtualization.clusters.get(id=unknown_cluster_id)
                    if cluster:
                        logging.warning(f"Expected cluster with ID {expected_cluster_id} not found. Assigning VM {vm_netbox.name} to 'Unknown' cluster.")
                    else:
                        logging.error(f"Unknown cluster with ID {unknown_cluster_id} not found in NetBox. Cannot update VM {vm_netbox.name}.")
                        return None, None
                else:
                    logging.error(f"No 'Unknown' cluster mapped. Cannot update VM {vm_netbox.name}.")
                    return None, None
        else:
            # Use "Unknown" cluster if no cluster ID is available
            unknown_cluster_map = self.cluster_mapping.get("Unknown", {})
            unknown_cluster_id = unknown_cluster_map.get("netbox_cluster_id")
            if unknown_cluster_id:
                cluster = self.netbox.virtualization.clusters.get(id=unknown_cluster_id)
                if not cluster:
                    logging.error(f"Unknown cluster with ID {unknown_cluster_id} not found in NetBox. Cannot update VM {vm_netbox.name}.")
                    return None, None
                else:
                    logging.warning(f"No cluster ID found for VM {vm_netbox.name}. Assigning to 'Unknown' cluster.")
            else:
                logging.error(f"No cluster ID found and no 'Unknown' cluster mapped for VM {vm_netbox.name}.")
                return None, None

        # Retrieve the site object from NetBox
        if expected_site_id:
            site = self.netbox.dcim.sites.get(id=expected_site_id)
            if not site:
                logging.error(f"Site with ID {expected_site_id} not found in NetBox. Cannot update VM {vm_netbox.name}.")
                return cluster, None
        else:
            logging.error(f"No expected Site ID for VM {vm_netbox.name}.")
            return cluster, None

        # Check if cluster and site need to be updated
        if vm_netbox.cluster != cluster or vm_netbox.site != site:
            vm_netbox.cluster = cluster
            vm_netbox.site = site
            vm_netbox.save()
            logging.info(f"Updated cluster and site for VM {vm_netbox.name} to cluster {cluster.name} and site {site.name}.")

        return cluster, site

    def update_vm_in_netbox(self, vm, vm_netbox):
        # Update cluster and site if necessary
        cluster, site = self._update_vm_cluster_and_site(vm, vm_netbox)
        if not cluster or not site:
            logging.error(f"Unable to retrieve cluster or site for VM {vm_netbox.name}. Skipping attribute update.")
            return

        # Prepare custom fields data
        custom_fields_data = {}
        if 'created' in self.cf_names and vm.created:
            custom_fields_data['created'] = vm.created.isoformat()
        if 'last_update' in self.cf_names and vm.last_update:
            custom_fields_data['last_update'] = vm.last_update.isoformat()
        if 'last_checked' in self.cf_names and vm.last_checked:
            custom_fields_data['last_checked'] = vm.last_checked.isoformat()

        # Update other VM attributes
        self._set_vm_attributes(vm_netbox, vm, custom_fields_data, cluster, site)
        self._handle_interfaces(vm_netbox, vm.ip_address, is_update=True)
        #self.compare_and_update_vm_status(vm_netbox, vm.ip_address)
        self.add_tag_to_vm(vm_netbox, self.SYNC_TAG)
        logging.info(f"VM {vm.name} updated in NetBox.")


    def get_netbox_cluster_id_from_vcenter_vm(self, vm):
        vcenter_cluster_name = vm.cluster_name
        netbox_cluster_id = self.cluster_mapping.get(vcenter_cluster_name)
        if netbox_cluster_id:
            return netbox_cluster_id
        else:
            logging.warning(f"No NetBox cluster ID found for vCenter cluster: {vcenter_cluster_name}")
            return None

    def get_netbox_site_id_from_vcenter_vm(self, vm):
        vcenter_site_name = vm.datacenter
        netbox_site_id = self.site_mapping.get(vcenter_site_name)
        if netbox_site_id:
            return netbox_site_id
        else:
            logging.warning(f"No NetBox site ID found for vCenter site: {vcenter_site_name}")
            return None
  def get_or_create_interface(self, vm, create_if_not_exists=True):
        interface_name = 'ens192'
        vm_id = vm.id if isinstance(vm.id, int) else int(vm.id)
        interface = self.netbox.virtualization.interfaces.get(virtual_machine_id=vm_id, name=interface_name)
        if interface:
            logging.info(f"Interface {interface_name} already exists for VM {vm.name}.")
            return interface
        else:
            if create_if_not_exists:
                logging.info(f"Creating interface {interface_name} for VM {vm.name} with ID {vm_id}")
                interface = self.netbox.virtualization.interfaces.create(
                    virtual_machine=vm_id,
                    name=interface_name,
                    enabled=True
                )
                # Re-fetch the interface to ensure it's fully populated
                interface = self.netbox.virtualization.interfaces.get(id=interface.id)
                return interface
            else:
                logging.warning(f"Interface {interface_name} does not exist for VM {vm.name}.")
                return None

    def find_existing_ip(self, ip_address):
        try:
            ips = self.netbox.ipam.ip_addresses.filter(address=ip_address)
            return list(ips)
        except pynetbox.RequestError as e:
            logging.error(f"Failed to find IP address {ip_address}: {e}")
            return []

    def assign_ip_to_interface(self, interface, ip_address):
        if ip_address and ip_address != "Unknown":
            try:
                ip = ipaddress.ip_address(ip_address)
            except ValueError:
                logging.error(f"Invalid IP address: {ip_address}")
                return

            existing_ips = self.find_existing_ip(ip_address)
            if len(existing_ips) > 1:
                logging.warning(f"Multiple IP addresses found for {ip_address}. Assigning the first one.")
                existing_ip = existing_ips[0]
            elif len(existing_ips) == 1:
                existing_ip = existing_ips[0]
            else:
                existing_ip = None

            vm = interface.virtual_machine  # Retrieve the VM associated with the interface

            # Determine if the VM already has a primary IP
            if ip.version == 4:
                current_primary_ip = vm.primary_ip4
            else:
                current_primary_ip = vm.primary_ip6

            if existing_ip:
                if existing_ip.assigned_object and existing_ip.assigned_object.id != interface.id:
                    logging.warning(f"IP address {ip_address} is already assigned to another interface.")
                else:
                    try:
                        existing_ip.assigned_object_type = 'virtualization.vminterface'
                        existing_ip.assigned_object_id = interface.id
                        existing_ip.save()

                        # Set as primary if the VM doesn't have one
                        if not current_primary_ip:
                            if ip.version == 4:
                                vm.primary_ip4 = existing_ip
                            else:
                                vm.primary_ip6 = existing_ip
                            vm.save()
                            logging.info(f"Set IP address {ip_address} as primary for VM {vm.name}.")
                    except pynetbox.RequestError as e:
                        if 'Duplicate IP address' in str(e):
                            logging.error(f"Duplicate IP address detected: {ip_address}. Skipping assignment.")
                        else:
                            logging.error(f"Failed to assign IP address {ip_address} to interface {interface.name}: {e}")
            else:
                try:
                    new_ip = self.netbox.ipam.ip_addresses.create(
                        address=ip_address,
                        assigned_object_type='virtualization.vminterface',
                        assigned_object_id=interface.id
                    )

                    # Set as primary if the VM doesn't have one
                    if not current_primary_ip:
                        if ip.version == 4:
                            vm.primary_ip4 = new_ip
                        else:
                            vm.primary_ip6 = new_ip
                        vm.save()
                        logging.info(f"Set IP address {ip_address} as primary for VM {vm.name}.")

                    logging.info(f"Assigned IP address {ip_address} to interface {interface.name} of VM {vm.name}.")
                except pynetbox.RequestError as e:
                    if 'Duplicate IP address' in str(e):
                        logging.error(f"Duplicate IP address detected: {ip_address}. Skipping assignment.")
                    else:
                        logging.error(f"Failed to create IP address {ip_address}: {e}")
        else:
            logging.info(f"No IP address to assign for VM {interface.virtual_machine.name}")

    def compare_and_update_vm_status(self, vm, desired_ip_address):
        if desired_ip_address and desired_ip_address != "Unknown":
            try:
                desired_ip = ipaddress.ip_address(desired_ip_address)
            except ValueError:
                logging.error(f"Invalid IP address: {desired_ip_address}")
                return

            current_primary_ip = vm.primary_ip4

            # Check if the current primary IP matches the desired IP
            if current_primary_ip:
                current_primary_address = current_primary_ip.address.split('/')[0]
                if current_primary_address != str(desired_ip):
                    # IPs don't match, update comments and status
                    comment = f"Mismatched IP address detected. Expected: {desired_ip}, Found: {current_primary_address}"
                    if vm.comments:
                        vm.comments += f"\n{comment}"
                    else:
                        vm.comments = comment
                    # Set status to 'Failed'
                    vm.status = 'failed'
                    vm.save()
                    logging.warning(f"VM {vm.name} status set to 'Failed' due to IP mismatch.")
                else:
                    logging.info(f"IP addresses match for VM {vm.name}. No action needed.")
            else:
                # No primary IP set, update comments and set status to 'Failed'
                comment = f"Primary IP address not set. Expected: {desired_ip}"
                if vm.comments:
                    vm.comments += f"\n{comment}"
                else:
                    vm.comments = comment
                # Set status to 'Failed'
                vm.status = 'failed'
                vm.save()
                logging.warning(f"VM {vm.name} status set to 'Failed' due to missing primary IP.")
        else:
            logging.info(f"No IP address to compare for VM {vm.name}.")

    def load_vms_from_json(self):
        with open(self.json_file, 'r') as f:
            vms_data = json.load(f)
        vms = [VM.from_dict(vm_dict) for vm_dict in vms_data]
        for vm in vms:
            vm.parse_dates()
        return vms

    def get_platform_id(self, platform_name):
        cleaned_name = platform_name.strip()
        slug = slugify(platform_name)
        # Check if platform with this slug exists
        platforms = list(self.netbox.dcim.platforms.filter(slug=slug))
        if platforms:
            return platforms[0].id
        else:
            platform_id = self.create_platform(cleaned_name)
            if platform_id:
                return platform_id
            else:
                logging.error(f"Unable to create platform {platform_name}. Using default platform ID.")
                return 1  # Replace with a default platform ID

    def create_platform(self, platform_name):
        try:
            cleaned_name = platform_name.strip()
            slug = slugify(platform_name)
            # Check if platform with this slug already exists
            existing_platforms = list(self.netbox.dcim.platforms.filter(slug=slug))
            if existing_platforms:
                logging.info(f"Platform with slug {slug} already exists. Using existing platform ID {existing_platforms[0].id}.")
                return existing_platforms[0].id
            # If not, create a new platform
            new_platform = self.netbox.dcim.platforms.create(
                name=cleaned_name,
                slug=slug,
                manufacturer=1  # Ensure this is a valid manufacturer ID in NetBox
            )
            logging.info(f"Created new platform: {new_platform.name}")
            return new_platform.id
        except Exception as e:
            logging.error(f"Failed to create platform {platform_name}: {e}")
            return None
            
    def should_update_vms(self):
        if self.json_file:
            if not os.path.exists(self.json_file):
                return True
            last_modified = datetime.fromtimestamp(os.path.getmtime(self.json_file))
            return datetime.now() - last_modified > timedelta(days=1)
        else:
            return True  # or handle accordingly
    def process_vms(self):
        if self.should_update_vms():
            self.vcenter_connector.connect()
            vms = self.vcenter_connector.get_vm_info()
            self.vcenter_connector.save_to_json(vms, self.json_file)
            self.vcenter_connector.disconnect()
        else:
            vms = self.load_vms_from_json()

        # Fetch all VMs from NetBox and group them by name and cluster
        netbox_vms = self.netbox.virtualization.virtual_machines.all()
        vm_mapping = {}
        for vm in netbox_vms:
            key = (vm.name.lower(), vm.cluster.id if vm.cluster else None)
            vm_mapping.setdefault(key, []).append(vm)

        for vcenter_vm in vms:
            vcenter_cluster_name = vcenter_vm.cluster
            cluster_map = self.cluster_mapping.get(vcenter_cluster_name, self.cluster_mapping.get("Unknown", {}))
            target_cluster_id = cluster_map.get("netbox_cluster_id")
            target_site_id = cluster_map.get("netbox_site_id")

            # Validate cluster and site IDs
            if not self.netbox.virtualization.clusters.get(target_cluster_id):
                logging.error(f"Invalid cluster ID {target_cluster_id} for VM {vcenter_vm.name}. Skipping.")
                continue
            if not self.netbox.dcim.sites.get(target_site_id):
                logging.error(f"Invalid site ID {target_site_id} for VM {vcenter_vm.name}. Skipping.")
                continue

            # Normalize vCenter VM name for comparison
            normalized_vcenter_vm_name = vcenter_vm.name.lower()

            # Check if VM already exists with the correct cluster and site
            existing_vms = vm_mapping.get((normalized_vcenter_vm_name, target_cluster_id), [])
            if existing_vms:
                existing_vm = existing_vms[0]
                self.update_vm_in_netbox(vcenter_vm, existing_vm)
                logging.info(f"VM {vcenter_vm.name} updated in NetBox.")
            else:
                # Check if VM exists with the same name but different cluster/site
                for (name, cluster_id), vms_list in vm_mapping.items():
                    if name == normalized_vcenter_vm_name and cluster_id != target_cluster_id:
                        for vm in vms_list:
                            # Update cluster and site
                            self._update_vm_cluster_and_site(vcenter_vm, vm)
                            # Update other attributes
                            self.update_vm_in_netbox(vcenter_vm, vm)
                            logging.info(f"VM {vm.name} updated with new cluster and site.")
                # If no existing VM with the correct cluster, create a new one
                if not existing_vms:
                    self.create_vm_in_netbox(vcenter_vm, target_cluster_id, target_site_id)
                    logging.info(f"VM {vcenter_vm.name} created in NetBox.")





    def tag_and_fail_old_vm(self, old_vm):
        self.add_tag_to_vm(old_vm, self.ORPHANED_TAG)
        old_vm.status = 'failed'
        old_vm.save()
        logging.info(f"VM {old_vm.name} tagged as 'ORPHANED_FROM_SYNC' and set to 'failed'.")
