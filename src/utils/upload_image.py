import os
from dotenv import load_dotenv
from imagekitio import ImageKit
from imagekitio.models.upload_file_request_options import UploadFileRequestOptions

load_dotenv()

imagekit = ImageKit(
    private_key  = os.getenv("IMAGEKIT_PRIVATE_KEY"),
    public_key   = os.getenv("IMAGEKIT_PUBLIC_KEY"),
    url_endpoint = os.getenv("IMAGEKIT_URL_ENDPOINT")   # https://ik.imagekit.io/ClosetMindAI/
)

def upload_image(path: str) -> str:
    with open(path, "rb") as file:
        opts = UploadFileRequestOptions(
            folder="/data/test/",          # ➜ создастся автоматически
            use_unique_file_name=False     # нужно строго 1.jpg? ставим False
        )
        res = imagekit.upload_file(
            file=file,
            file_name=os.path.basename(path),
            options=opts
        )
    return res["response"]["url"]

if __name__ == "__main__":
    print(upload_image(r"data/test/1.jpg"))
