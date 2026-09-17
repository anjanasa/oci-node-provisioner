import oci

# Use your exact config
config = {
    "user": "ocid1.user.oc1..aaaaaaaa25mmvfcullr5hxqdbod46m2ld7xxiphvn3g2synnl6hezevaihna",
    "fingerprint": "38:40:96:75:6a:78:34:29:e9:ca:63:4f:fc:ad:d7:bb",
    "tenancy": "ocid1.tenancy.oc1..aaaaaaaa2kym4idkoemo6nbmsnagzuyl3yvkiaekfxw4i3yx3ahvbeidw6ea",
    "region": "ap-singapore-1",
    "key_file": "path/to/private_key.pem"  # Update with your .pem file path
}

identity = oci.identity.IdentityClient(config)
network = oci.core.VirtualNetworkClient(config)

# 1. Fetch exact AD string
ads = identity.list_availability_domains(config["tenancy"]).data
print("=== EXACT AVAILABILITY DOMAINS FOR YOUR TENANCY ===")
for ad in ads:
    print(f"  Exact AD Name: '{ad.name}'")

# 2. Check Subnet Public IP permission
subnet_id = "ocid1.subnet.oc1.ap-singapore-1.aaaaaaaafwgvzvekwtlijdwtfpoub72wghthj26iojdo42fenbnswxbw6zda"
subnet = network.get_subnet(subnet_id).data
print("\n=== SUBNET DETAILS ===")
print(f"Subnet Name: {subnet.display_name}")
print(f"Prohibit Public IP: {subnet.prohibit_public_ip_on_vnic}")