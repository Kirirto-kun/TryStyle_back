import replicate
import os
from dotenv import load_dotenv

load_dotenv()

input = {
    "garm_img": "https://ss.sport-express.ru/userfiles/materials/4/45138/large.jpg",
    "human_img": "https://replicate.delivery/pbxt/KgwTlhCMvDagRrcVzZJbuozNJ8esPqiNAIJS3eMgHrYuHmW4/KakaoTalk_Photo_2024-04-04-21-44-45.png",
    "garment_des": ""
}

output = replicate.run(
    "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985",
    input=input
)
with open("output.jpg", "wb") as file:
    file.write(output.read())
#=> output.jpg written to disk

