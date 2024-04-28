import time
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import mysql.connector
import cv2
from imutils.video import VideoStream
import face_recognition
import imutils
import pickle

# Initialize 'currentname' to trigger only when a new person is identified.
currentname = "unknown"
# Determine faces from encodings.pickle file model created from train_model.py
encodingsP = "encodings.pickle"

# Load the known faces and embeddings along with OpenCV's Haar
# cascade for face detection
print("[INFO] loading encodings + face detector...")
data = pickle.loads(open(encodingsP, "rb").read())

# Initialize the video stream and allow the camera sensor to warm up
vs = VideoStream(src=0, framerate=30).start()
time.sleep(2.0)

# Connect to MySQL database
db = mysql.connector.connect(
    host="localhost",
    user="admin",
    passwd="rudra",
    database="attendancesystem"
)
cursor = db.cursor()

# Initialize RFID reader
reader = SimpleMFRC522()

try:
    print("Tap your card to get access")
    id, _ = reader.read()

    if str(id) == "220761663128":  # If RFID tag matches
        print("RFID tag detected. Performing facial recognition...")

        while True:
            # Grab the frame from the threaded video stream and resize it
            frame = vs.read()
            frame = imutils.resize(frame, width=500)

            # Detect the face boxes
            boxes = face_recognition.face_locations(frame)

            # Compute the facial embeddings for each face bounding box
            encodings = face_recognition.face_encodings(frame, boxes)
            names = []

            # Loop over the facial embeddings
            for encoding in encodings:
                # Attempt to match each face in the input image to our known encodings
                matches = face_recognition.compare_faces(data["encodings"], encoding)
                name = "Unknown"  # If face is not recognized, then print Unknown

                # Check to see if we have found a match
                if True in matches:
                    # Find the indexes of all matched faces then initialize a dictionary to count the total number of times each face was matched
                    matchedIdxs = [i for (i, b) in enumerate(matches) if b]
                    counts = {}

                    # Loop over the matched indexes and maintain a count for each recognized face face
                    for i in matchedIdxs:
                        name = data["names"][i]
                        counts[name] = counts.get(name, 0) + 1

                    # Determine the recognized face with the largest number of votes
                    name = max(counts, key=counts.get)

                    # If someone in your dataset is identified, print their name on the screen
                    if currentname != name:
                        currentname = name
                        print(currentname)

                # Update the list of names
                names.append(name)

            # Loop over the recognized faces
            for ((top, right, bottom, left), name) in zip(boxes, names):
                # Draw the predicted face name on the image - color is in BGR
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 225), 2)
                y = top - 15 if top - 15 > 15 else top + 15
                cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX, .8, (0, 255, 255), 2)

                # If Rudra is detected, display "Access Granted"
                if name == "Rudra":
                    cv2.putText(frame, "Access Granted", (left, bottom + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Display the image to our screen
            cv2.imshow("Facial Recognition is Running", frame)
            key = cv2.waitKey(1) & 0xFF 

            # Record attendance in the database
            if "Rudra" in names:
                print("Access recorded for Rudra")


            # Check if the 'q' key is pressed to exit the loop
            if key == ord("q"):
                break

    else:
        print("RFID tag does not match")

finally:
    GPIO.cleanup()
    cv2.destroyAllWindows()
    vs.stop()
