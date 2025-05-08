import pynetbox
import logging
import re
import os
import json
from datetime import datetime, timedelta
import warnings
from urllib3.exceptions import InsecureRequestWarning

# Suppress only the insecure request warning
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def slugify(text):
    # Remove special characters and replace spaces with hyphens
    slug = re.sub(r'[^\w\s-]', '', text).strip().lower()
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug

class NetBoxConnector:
    def __init__(self, url, token, vcenter_clusters, tags_to_exclude = None):
        self.url = url
        self.token = token
        self.netbox = pynetbox.api(url, token=token)
        self.netbox.http_session.verify = False
        print(f"Netbox version is {self.netbox.version}")
        self.cluster_mapping = self.build_cluster_mapping(vcenter_clusters)
        self.tags_to_exclude = tags_to_exclude

    def get_or_create_cluster_type(self, name):
        cluster_types = self.netbox.virtualization.cluster_types.filter(name=name)
        if cluster_types:
            return cluster_types[0].id
        else:
            # Create the cluster type
            new_cluster_type = self.netbox.virtualization.cluster_types.create(
                name=name,
                slug=slugify(name)
            )
            logging.info(f"Created new cluster type: {new_cluster_type.name} with ID {new_cluster_type.id}")
            return new_cluster_type.id

    def build_cluster_mapping(self, vcenter_clusters):
        netbox_clusters = self.netbox.virtualization.clusters.all()
        cluster_map = {}
        for cluster in netbox_clusters:
            if cluster.name in vcenter_clusters:
                if cluster.site:
                    cluster_map[cluster.name] = {
                        "netbox_cluster_id": cluster.id,
                        "netbox_site_id": cluster.site.id
                    }
                    logging.info(f"Mapped vCenter cluster '{cluster.name}' to NetBox cluster ID {cluster.id} and site ID {cluster.site.id}.")
                else:
                    # Assign to "Unknown" site
                    unknown_site = self.netbox.dcim.sites.get(name="Unknown")
                    if not unknown_site:
                        # Create "Unknown" site
                        unknown_site = self.netbox.dcim.sites.create(
                            name="Unknown",
                            slug="unknown"
                        )
                        logging.info(f"Created 'Unknown' site with ID {unknown_site.id}.")
                    cluster_map[cluster.name] = {
                        "netbox_cluster_id": cluster.id,
                        "netbox_site_id": unknown_site.id
                    }
                    logging.warning(f"Cluster '{cluster.name}' has no site assigned. Assigned to 'Unknown' site with ID {unknown_site.id}.")
        # Handle unknown clusters
        unknown_cluster = self.netbox.virtualization.clusters.get(name="Unknown")
        if not unknown_cluster:
            # Get or create "Unknown" cluster type
            unknown_cluster_type_id = self.get_or_create_cluster_type("Unknown")
            # Create "Unknown" cluster
            unknown_site = self.netbox.dcim.sites.get(name="Unknown")
            if not unknown_site:
                unknown_site = self.netbox.dcim.sites.create(
                    name="Unknown",
                    slug="unknown"
                )
                logging.info(f"Created 'Unknown' site with ID {unknown_site.id}.")
            unknown_cluster = self.netbox.virtualization.clusters.create(
                name="Unknown",
                type=unknown_cluster_type_id,
                site=unknown_site.id
            )
            logging.info(f"Created 'Unknown' cluster with ID {unknown_cluster.id} under site ID {unknown_site.id}.")
        unknown_site = self.netbox.dcim.sites.get(name="Unknown")
        cluster_map["Unknown"] = {
            "netbox_cluster_id": unknown_cluster.id,
            "netbox_site_id": unknown_site.id
        }
        logging.info(f"Mapped 'Unknown' cluster to ID {unknown_cluster.id} and site ID {unknown_site.id}.")
        return cluster_map


    def get_vms(self):
        tags_to_exclude = self.tags_to_exclude
        """
        Retrieve VMs that do NOT have any of the specified tags.

        :param tags_to_exclude: List of tag names to exclude
        :return: Dictionary mapping VM names to VM objects that do not have the specified tags
        """
        vms_netbox = self.netbox.virtualization.virtual_machines.all()
        vm_mapping = {}
        
        if tags_to_exclude:
            tags_to_exclude_set = set(tags_to_exclude)
            for vm_nb in vms_netbox:
                vm_tags = {tag.name for tag in vm_nb.tags}
                if not vm_tags.intersection(tags_to_exclude_set):
                    vm_mapping[vm_nb.name.lower()] = vm_nb  # Store the NetBox API VM object
        else:
            for vm_nb in vms_netbox:
                vm_mapping[vm_nb.name.lower()] = vm_nb  # Store the NetBox API VM object
        
        return vm_mapping