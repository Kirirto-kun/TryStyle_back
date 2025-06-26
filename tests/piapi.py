import http.client
import json
import base64
import os

# Function to encode image to base64
def image_to_base64(filepath):
    with open(filepath, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')

conn = http.client.HTTPSConnection("api.piapi.ai")

# Using os.path.expanduser to be more portable than a hardcoded home directory.
home_dir = os.path.expanduser("~")
target_image_path = os.path.join(home_dir, "Downloads", "squid_face.jpg")
swap_image_path = os.path.join(home_dir, "Downloads", "swap.jpeg")

if not os.path.exists(target_image_path):
    print(f"Error: Target image not found at {target_image_path}")
    exit()
if not os.path.exists(swap_image_path):
    print(f"Error: Swap image not found at {swap_image_path}")
    exit()

# Convert images to base64 strings
target_image_b64 = image_to_base64(target_image_path)
swap_image_b64 = image_to_base64(swap_image_path)

# Construct the payload according to the new API spec
payload_dict = {
  "model": "Qubico/image-toolkit",
  "task_type": "face-swap",
  "input": {
    "target_image": target_image_b64,
    "swap_image": swap_image_b64
  }
}
payload = json.dumps(payload_dict)

headers = {
    'x-api-key': "{{43285f5b751e342f8a2eb8db843397ff2842a5a7863f3b1a1d6a26467ad14fe9}}",
    'Content-Type': "application/json",
    'Accept': "application/json"
}

# Use the new endpoint from the OpenAPI spec
conn.request("POST", "/api/v1/task", payload, headers)

res = conn.getresponse()
data = res.read()

print(f"Status: {res.status} {res.reason}")
print("Response body:")
print(data.decode("utf-8"))
