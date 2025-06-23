import time
import urllib
import subprocess

from PIL import Image as PIL_Image
from google import genai
from google.genai import types
import matplotlib.pyplot as plt

import os

PROJECT_ID = "onaitabu"  # @param {type: "string", placeholder: "[your-project-id]", isTemplate: true}
if not PROJECT_ID or PROJECT_ID == "[your-project-id]":
    PROJECT_ID = str(os.environ.get("GOOGLE_CLOUD_PROJECT"))

LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

def show_video(gcs_uri):
    file_name = gcs_uri.split("/")[-1]
    subprocess.run(["gsutil", "cp", gcs_uri, file_name])
    print(f"Video downloaded to: {os.path.abspath(file_name)}")


def display_images(image) -> None:
    fig, axis = plt.subplots(1, 1, figsize=(12, 6))
    axis.imshow(image)
    axis.set_title("Starting Image")
    axis.axis("off")
    plt.show()

video_model = "veo-3.0-generate-preview"


image_show = PIL_Image.open(
    urllib.request.urlopen(
        "https://storage.googleapis.com/cloud-samples-data/generative-ai/image/flowers.png"
    )
)
display_images(image_show)
location = "a beautiful beach"
person_description = "human on the photo"   
prompt = f"""
    A cinematic fashion model video of {person_description} walking confidently in {location}.
    The camera follows them smoothly as they walk like a professional runway model, with elegant, rhythmic movement, maintaining strong posture and eye contact with the camera.
    The lighting is soft, natural and dramatic — golden hour sunlight or cool studio-like directional lights create beautiful shadows and highlights on the person's face and outfit.
    The person is wearing fashionable clothes that match the environment's aesthetic.
    The background is slightly out of focus to emphasize depth of field and focus on the model.
    The atmosphere is premium, high fashion — like a scene from a Vogue or Prada ad.
    There are dynamic camera angles: slow pans, close-up on details like fabric moving, mid-shots of the person walking, and wide shots to show the stunning location.
    No strange artifacts, no jerky motion, all movements are natural and fluid.
    No logos or brands unless fashion-related.
    No distortion. No weird face morphing. Realistic human proportions.
"""

image_gcs = (
    "https://storage.googleapis.com/onaitabu.firebasestorage.app/bb013fdc-56bf-4414-ad2e-9b0365dd2179.png"  # @param {type: 'string'}
)
output_gcs = "gs://"  # @param {type: 'string'}
enhance_prompt = True  # @param {type: 'boolean'}
generate_audio = True  # @param {type: 'boolean'}


operation = client.models.generate_videos(
    model=video_model,
    prompt=prompt,
    image=types.Image(
        gcs_uri=image_gcs,
        mime_type="image/png",
    ),
    config=types.GenerateVideosConfig(
        aspect_ratio="16:9",
        output_gcs_uri=output_gcs,
        number_of_videos=1,
        duration_seconds=10,
        person_generation="allow_adult",
        enhance_prompt=enhance_prompt,
        generate_audio=generate_audio,
    ),
)

while not operation.done:
    time.sleep(15)
    operation = client.operations.get(operation)
    print(operation)

if operation.response:
    show_video(operation.result.generated_videos[0].video.uri)



