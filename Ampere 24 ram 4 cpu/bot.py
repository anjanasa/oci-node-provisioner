import os
import time
from dotenv import load_dotenv
import oci

load_dotenv()

# Format raw private key string to handle line breaks correctly
raw_key = os.getenv("OCI_PRIVATE_KEY", "")
formatted_key = raw_key.replace('\\n', '\n') if raw_key else None

config = {
    "user": os.getenv("OCI_USER_ID"),
    "key_content": formatted_key,
    "fingerprint": os.getenv("OCI_FINGERPRINT"),
    "tenancy": os.getenv("OCI_TENANCY_ID"),
    "region": os.getenv("OCI_REGION", "ap-singapore-1")
}

try:
    compute_client = oci.core.ComputeClient(config)
    identity_client = oci.identity.IdentityClient(config)
    print("OCI Authentication Successful.")
except Exception as e:
    print(f"Authentication Failed: {e}")
    exit(1)

# Execution parameters from environment
compartment_id = os.getenv("OCI_TENANCY_ID")
subnet_id = os.getenv("OCI_SUBNET_ID")
public_ssh_key = os.getenv("OCI_PUBLIC_SSH_KEY")

if not public_ssh_key or public_ssh_key.strip() == "":
    print("CRITICAL ERROR: OCI_PUBLIC_SSH_KEY is empty or missing!")
    exit(1)

# 1. Fetch Availability Domains dynamically for ap-singapore-1
try:
    ad_response = identity_client.list_availability_domains(compartment_id)
    ads = [ad.name for ad in ad_response.data]
    print(f"Detected Availability Domains in {config['region']}: {ads}")
except Exception as e:
    print(f"Failed to fetch Availability Domains: {e}")
    exit(1)

# 2. Auto-fetch ARM image OCID if not explicitly provided in .env
image_id = os.getenv("OCI_IMAGE_ID")
if not image_id:
    print("OCI_IMAGE_ID not set. Searching for latest Canonical Ubuntu ARM image...")
    images = compute_client.list_images(
        compartment_id=compartment_id,
        operating_system="Canonical Ubuntu",
        shape="VM.Standard.A1.Flex",
        sort_by="TIMECREATED",
        sort_order="DESC"
    ).data
    for img in images:
        if "aarch64" in img.display_name.lower():
            image_id = img.id
            break
    if not image_id and images:
        image_id = images[0].id

print(f"Using Image OCID: {image_id}")

total_attempts = 60

# 3. Instance creation loop
for i in range(1, total_attempts + 1):
    current_ad = ads[(i - 1) % len(ads)]
    print(f"[Attempt {i}/{total_attempts}] Requesting instance in {current_ad}...")

    try:
        request = oci.core.models.LaunchInstanceDetails(
            display_name="FX-Backend-Server",
            compartment_id=compartment_id,
            availability_domain=current_ad,
            shape="VM.Standard.A1.Flex",
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=4,
                memory_in_gbs=24
            ),
            source_details=oci.core.models.InstanceSourceViaImageDetails(
                source_type="image",
                image_id=image_id,
                boot_volume_size_in_gbs=100
            ),
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=subnet_id,
                assign_public_ip=True,
                assign_private_dns_record=True,
                hostname_label="forexalerts",  # Required for private DNS
                display_name="forexalertsvnic"
            ),
            metadata={
                "ssh_authorized_keys": str(public_ssh_key).strip()
            }
        )

        response = compute_client.launch_instance(request)
        if response.status == 200:
            print("SUCCESS! Server creation initialized successfully.")
            exit(0)

    except oci.exceptions.ServiceError as e:
        if "Out of host capacity" in str(e) or e.status == 500:
            print("-> Capacity Unavailable. Resting 60 seconds...")
        else:
            print(f"-> API Error: {e.message}")

    if i < total_attempts:
        time.sleep(60)
