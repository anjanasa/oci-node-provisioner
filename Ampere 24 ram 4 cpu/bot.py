import os
import time
from dotenv import load_dotenv
import oci

load_dotenv()

# --- 1. STATIC CONFIGURATION & DEFAULTS ---
USER_OCID = os.getenv("OCI_USER_ID", "ocid1.user.oc1..aaaaaaaa25mmvfcullr5hxqdbod46m2ld7xxiphvn3g2synnl6hezevaihna")
FINGERPRINT = os.getenv("OCI_FINGERPRINT", "38:40:96:75:6a:78:34:29:e9:ca:63:4f:fc:ad:d7:bb")
TENANCY_OCID = os.getenv("OCI_TENANCY_ID", "ocid1.tenancy.oc1..aaaaaaaa2kym4idkoemo6nbmsnagzuyl3yvkiaekfxw4i3yx3ahvbeidw6ea")
REGION = os.getenv("OCI_REGION", "ap-singapore-1")

KEY_FILE = os.getenv("OCI_KEY_FILE", "path/to/private_key.pem")
RAW_KEY_CONTENT = os.getenv("OCI_PRIVATE_KEY")

config = {
    "user": USER_OCID,
    "fingerprint": FINGERPRINT,
    "tenancy": TENANCY_OCID,
    "region": REGION
}

# Resolve private key from file path or raw environment string
if RAW_KEY_CONTENT:
    config["key_content"] = RAW_KEY_CONTENT.replace('\\n', '\n')
elif KEY_FILE and os.path.exists(KEY_FILE):
    config["key_file"] = KEY_FILE
else:
    # Fallback to key file path if specified directly
    config["key_file"] = KEY_FILE

# --- 2. RESOURCE DEFAULTS ---
SUBNET_ID = os.getenv(
    "OCI_SUBNET_ID", 
    "ocid1.subnet.oc1.ap-singapore-1.aaaaaaaafwgvzvekwtlijdwtfpoub72wghthj26iojdo42fenbnswxbw6zda"
)
IMAGE_ID = os.getenv(
    "OCI_IMAGE_ID", 
    "ocid1.image.oc1.ap-singapore-1.aaaaaaaawntxufyor65yjvl744hj5p3fbu77jdafnqlpxayley2braeynp5q"
)
PUBLIC_SSH_KEY = os.getenv(
    "OCI_PUBLIC_SSH_KEY", 
    "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDDhR/ATZS0I7WTmgzipcNNuMJy4itfBgieuPGXXkWKDEWJat/8aAW9r1u+stN3Hyvspk8NayARFmSslxT7cH5oQIRvmbl4IhJ7IfL6QvRQhkaK2Qg0Zwe8M8329J3alayfNUpyygO0wLu8iXhF3PlsRvzxL+Y9ShLK/XNZ2pN8MvnB3JnKFoVtbf5e/3vi/skofOjIws1EziDAyLyIKAxsEVjsy5fY0qbOHLNDu+fALY3u7/ZfV8jA1IjvPkSgM70GD8/kv/5DmqRDcUYg9x3IU1bzfYC0TVGTmBa051h8IBJq2dC39Cxx2lsYA5iHlqEJjeULv1O/gvBfzknlS9kT ssh-key-2026-08-26"
)

# Static Availability Domain targets for Singapore (ap-singapore-1)
OVERRIDE_AD = os.getenv("OCI_AVAILABILITY_DOMAIN")
if OVERRIDE_AD:
    ads = [OVERRIDE_AD]
else:
    # Standard Singapore AD string variants matching tenancy prefix 'uufj'
    ads = [
        "uufj:AP-SINGAPORE-1-AD-1"
    ]

# Initialize Client
try:
    compute_client = oci.core.ComputeClient(config)
    print("OCI Authentication Initialized.")
except Exception as e:
    print(f"Authentication Error: {e}")
    exit(1)

print("\n" + "=" * 55)
print(" RUNTIME CONFIGURATION (STATIC) ")
print("=" * 55)
print(f"Region:               {config['region']}")
print(f"Tenancy OCID:         {config['tenancy']}")
print(f"User OCID:            {config['user']}")
print(f"Fingerprint:          {config['fingerprint']}")
print(f"Subnet OCID:          {SUBNET_ID}")
print(f"Image OCID:           {IMAGE_ID}")
print(f"Target AD List:       {ads}")
print("=" * 55 + "\n")

total_attempts = 60

# --- 3. EXECUTION LOOP ---
for i in range(1, total_attempts + 1):
    current_ad = ads[(i - 1) % len(ads)]
    print(f"[Attempt {i}/{total_attempts}] Requesting instance in {current_ad}...")

    try:
        request = oci.core.models.LaunchInstanceDetails(
            display_name="FX-Backend-Server",
            compartment_id=TENANCY_OCID,
            availability_domain=current_ad,
            shape="VM.Standard.A1.Flex",
            shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
                ocpus=4,
                memory_in_gbs=24
            ),
            source_details=oci.core.models.InstanceSourceViaImageDetails(
                source_type="image",
                image_id=IMAGE_ID,
                boot_volume_size_in_gbs=100
            ),
            create_vnic_details=oci.core.models.CreateVnicDetails(
                subnet_id=SUBNET_ID,
                assign_public_ip=True,
                assign_private_dns_record=True,
                hostname_label="forexalerts",
                display_name="forexalertsvnic"
            ),
            metadata={
                "ssh_authorized_keys": str(PUBLIC_SSH_KEY).strip()
            }
        )

        response = compute_client.launch_instance(request)
        if response.status in (200, 202):
            print("SUCCESS! Server creation initialized successfully.")
            exit(0)

    except oci.exceptions.ServiceError as e:
        if "Out of host capacity" in str(e) or e.status == 500:
            print("-> Capacity Unavailable. Resting 60 seconds...")
        else:
            print(f"-> API Error: {e.message}")

    if i < total_attempts:
        time.sleep(60)
