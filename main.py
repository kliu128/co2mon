from ctypes import ArgumentError
from PIL import Image
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import OperationStatusCodes
from msrest.authentication import CognitiveServicesCredentials
import cv2
import os
import time
import string
import re
import tempfile
from dotenv import load_dotenv

load_dotenv()

region = os.environ['ACCOUNT_REGION']
key = os.environ['ACCOUNT_KEY']

credentials = CognitiveServicesCredentials(key)
client = ComputerVisionClient(
    endpoint="https://" + region + ".api.cognitive.microsoft.com/",
    credentials=credentials
)


def read_text(path: str):
    '''
    OCR: Read File using the Read API, extract text - remote
    This example will extract text in an image, then print results, line by line.
    This API call can also extract handwriting style text (not shown).
    '''
    print("===== Read File - remote =====")
    # Call API with URL and raw response (allows you to get the operation location)
    read_response = client.read_in_stream(
        open(path, "rb"), raw=True, language="en")
    # Get the operation location (URL with an ID at the end) from the response
    read_operation_location = read_response.headers["Operation-Location"]
    # Grab the ID from the URL
    operation_id = read_operation_location.split("/")[-1]

    # Call the "GET" API and wait for it to retrieve the results
    while True:
        read_result = client.get_read_result(operation_id)
        if read_result.status not in ['notStarted', 'running']:
            break
        time.sleep(1)

    # Print the detected text, line by line
    if read_result.status == OperationStatusCodes.succeeded:
        for text_result in read_result.analyze_result.read_results:
            for line in text_result.lines:
                line = line.text
                cleaned_line = line.translate(
                    str.maketrans('', '', string.whitespace)).replace("-", "")
                print("Detected:", cleaned_line)
                matches = re.search("^([0-9]+).*$", cleaned_line)
                if matches is not None:
                    return int(matches.group(1))

        raise ValueError("Failed to decode OCR - no groups matched")


def capture_frame() -> Image:
    # define a video capture object
    vid = cv2.VideoCapture(0)

    vid.set(cv2.CAP_PROP_AUTOFOCUS, 1)

    vid.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    vid.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # Capture the video frame
    # by frame
    ret, frame = vid.read()

    # Display the resulting frame
    # OpenCV follows BGR, while PIL follows RGB
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # After the loop release the cap object
    vid.release()
    # Destroy all the windows
    cv2.destroyAllWindows()

    im_pil = Image.fromarray(frame)

    return im_pil


def record_co2_level():
    with tempfile.NamedTemporaryFile() as tmpfile:
        frame = capture_frame()
        frame.save("./frame.jpg", format='PNG')

        level = read_text("./frame.jpg")
        if level >= 5000 or level < 300:
            raise ValueError("Bad co2 level " + str(level))
        print("CO2 level:", level)
        log.write("{0},{1}\n".format(
            time.strftime("%Y-%m-%d %H:%M:%S"), str(level)))
        log.flush()


with open("co2.csv", "a") as log:
    while True:
        try:
            record_co2_level()
        except Exception as e:
            print(e)
        # Every 10 minutes, log co2 level
        time.sleep(10 * 60)
