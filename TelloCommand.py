import time, queue, socket, sqlite3, datetime, threading, rpc, sys, cv2, struct, math, numpy
from djitellopy import tello as Tello2
from flask import Flask, render_template
import time, cv2
from djitellopy import Tello	
import email, smtplib, ssl
from providers import PROVIDERS

tello = Tello2.Tello()

time.sleep(5)
tello.connect()


def videoRecorder():
    keepRecording = True
    tello.streamon()
    frame_read = tello.get_frame_read()
    print("recording video")
    height, width, _ = frame_read.frame.shape
    fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
    video = cv2.VideoWriter('static/video.mp4', fourcc, 30, (width, height))
    count = 0
    while keepRecording:
        video.write(frame_read.frame)
        time.sleep(1 / 30)
        count += 1
        print(count)
        if count > 100:
            print("stream complete")
            video.release()
            tello.streamoff()
            break

# Auto flight variables
travelDistance = 100
distance_x = 0
distance_y = 0
angle = 0
snake = False
command_run = 1
threadRun = True
# Openmv variables
interface = rpc.rpc_network_master(slave_ip="10.0.0.17", my_ip="", port=0x1DBA)

def rth(x, y, ang, heat):
    print("X: ", x, ", Y: ", y, ", Angle: ", ang)
    hyp = math.sqrt(x*x + y*y)
    print(hyp)
    ccw_rot = math.sin(x / hyp) * 100
    print("Need to rotate: ", ccw_rot)
    if heat:
        if ang == 90:
            totalRot = int(ccw_rot + 180)
            tello.rotate_counter_clockwise(totalRot)
        elif ang == 180:
            tello.rotate_clockwise(int(ccw_rot))
    else:
        tello.rotate_counter_clockwise(int(ccw_rot))
    sleep()
    tello.move_forward(int(hyp))
    sleep()
    tello.rotate_clockwise(int(ccw_rot))
    tello.rotate_clockwise(90)
    tello.land()

def sleep():
    time.sleep(1)

def reset():
    global interface
    interface = rpc.rpc_network_master(slave_ip="10.0.0.17", my_ip="", port=0x1DBA)

def forward():
    tello.move_forward(travelDistance)

def autonomousFlight():
    global command_run
    global snake
    global distance_x
    global distance_y
    global travelDistance
    global angle
    global threadRun
    if command_run == 1:
        tello.takeoff()
        time.sleep(3)
    while(threadRun):
        forward()
        if snake:
            tello.rotate_counter_clockwise(90)
            sleep()
            angle -= 90
            if(angle == 0):
                distance_y += travelDistance
            elif(angle == 90):
                distance_x -= travelDistance
            elif(angle == -90):
                distance_x += travelDistance
                rth(distance_x, distance_y, angle, False)
        else:
            tello.rotate_clockwise(90)
            sleep()
            angle += 90
            if(angle == 90):
                distance_x += travelDistance
            elif(angle == 180):
                distance_y += travelDistance
                snake = True
            elif(angle == 270):
                distance_x -= travelDistance
            elif(angle == 360):
                angle = 0
                distance_y -= travelDistance

        command_run  += 1
        print("Command Run: ", command_run, ", x_pos: ", distance_x, ", y_pos: ", distance_y, ", angle: ",  angle)
def send_sms_via_email(
    number: str,
    message: str,
    provider: str,
    sender_credentials: tuple,
    subject: str = "sent using etext",
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 465,
):
    sender_email, email_password = sender_credentials
    receiver_email = f'{number}@{PROVIDERS.get(provider).get("sms")}'

    email_message = f"Subject:{subject}\nTo:{receiver_email}\n{message}"

    with smtplib.SMTP_SSL(
        smtp_server, smtp_port, context=ssl.create_default_context()
    ) as email:
        email.login(sender_email, email_password)
        email.sendmail(sender_email, receiver_email, email_message)

def send_sms_via_email(
    number: str,
    message: str,
    provider: str,
    sender_credentials: tuple,
    subject: str = "Heat Anomaly Detectected",
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 465,
):
    print("sent text message")
    sender_email, email_password = sender_credentials
    receiver_email = f'{number}@{PROVIDERS.get(provider).get("sms")}'

    email_message = f"Subject:{subject}\nTo:{receiver_email}\n{message}"

    with smtplib.SMTP_SSL(
        smtp_server, smtp_port, context=ssl.create_default_context()
    ) as email:
        email.login(sender_email, email_password)
        email.sendmail(sender_email, receiver_email, email_message)


def sendMessage():
    number = "5743397212"
    message = "Please visit: http://127.0.0.1:5000"
    provider = "Verizon"

    sender_credentials = ("comcastremotefacility@gmail.com", "omfavkyhhiivujyh")

    # SMS
    send_sms_via_email(number, message, provider, sender_credentials)

app = Flask(__name__, static_folder='static')

@app.route('/')
def index():
    return render_template('index.html')

def inspectObject():
    global distance_x
    global distance_y
    global angle
    global keepRecording
    recorder = threading.Thread(target=videoRecorder)
    recorder.start()
    tello.move_up(50)
    tello.move_down(100)
    # Maybe do the cirlce here
    time.sleep(5)
    tello.move_up(50)
    keepRecording = False
    recorder.join()
    rth(distance_x, distance_y, angle, True)
    app.run()
    sendMessage()

def openMVLoop():
    global threadRun
    while(True):
        print("test")
        sys.stdout.flush()
        result = interface.call("heatcheck", "sensor.RGB565,sensor.QQVGA")
        if result is not None:
            print("heat detected")
            threadRun = False
            inspectObject()
            reset()


#Threads
thread1 = threading.Thread(target=autonomousFlight)
thread2 = threading.Thread(target=openMVLoop)

def main():

    thread1.start()

    thread2.start()

main()