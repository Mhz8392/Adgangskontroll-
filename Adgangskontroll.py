#!/usr/bin/python3
import tkinter as tk
import serial
import time
from picamera import PiCamera
import os
import glob
import PIL as p
import telegram
from telegram import Bot
from telegram.ext import Updater, CommandHandler
# from guizero import App,PushButton, Box, Text, Picture
from pygame import mixer
import _thread
import threading
from datetime import datetime
from subprocess import call
import zipfile
#defefinisjon av fonter og farger
LARGE_FONT_STYLE = ("Arial", 40, "bold")
SMALL_FONT_STYLE = ("Arial", 16)
DIGITS_FONT_STYLE = ("Arial", 24, "bold")
DEFAULT_FONT_STYLE = ("Arial", 20)
OFF_WHITE = "#F8FAFF"
WHITE = "#c18ea4"
LIGHT_BLUE = "#CCEDFF"
LIGHT_GRAY = "#F5F5F5"
LABEL_COLOR = "#25265E"
green= "#abf7b1"
red = "#ff6242"

# spiller lyd 
mixer.init() 
mixer.music.set_volume(0.9)


#variabler
last_time_button_pressed = time.time()
button_pressed_delay= 5.0 #second
i=0
bilde_fil=[None]*5
open_door_request = False
handling_door = False
flag = 0

#sjekker om kan oprette serial kommunikasjon med Arduino via USB porten
while True:
    try:
        ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1.0)
        print("Kommunikasjon med serial opprettet")
        time.sleep(3)
        break 
    
        
    except serial.SerialException:
        print("Problemer med kommunikasjonen...prøver igjen")
        time.sleep(1)
        

#lager GUI på HMI skjermen 
class HMI:
    def __init__(self):
        self.flag = 0
        self.window = tk.Tk()
        self.window.geometry("800x480")
        self.window.resizable(0, 0)
        self.window.title("welcome")
        self.total_expression = ""
        self.current_expression = ""
        self.display_frame = self.create_display_frame()
        self.label = self.create_display_labels()
        self.digits = {
            7: (1, 1), 8: (1, 2), 9: (1, 3),
            4: (2, 1), 5: (2, 2), 6: (2, 3),
            1: (3, 1), 2: (3, 2), 3: (3, 3),
            0: (4, 2), 
        }
        self.buttons_frame = self.create_buttons_frame()
        self.buttons_frame.rowconfigure(0, weight=1)
        for x in range(1, 4):
            self.buttons_frame.rowconfigure(x, weight=1)
            self.buttons_frame.columnconfigure(x, weight=1)
        self.create_digit_buttons()
        self.create_special_buttons()
        self.bind_keys()
        self.window.attributes('-fullscreen', True)
            
    def bind_keys(self):
        for key in self.digits:
            self.window.bind(str(key), lambda event, digit=key: self.add_to_expression(digit))


    def create_special_buttons(self):
        self.create_clear_button()
        self.create_call_button()
        self.create_ok_button()
    def create_display_labels(self):
        label = tk.Label(self.display_frame, text=self.current_expression, anchor=tk.E,
                         fg=LABEL_COLOR, font=LARGE_FONT_STYLE)
        label.pack(expand= True)
        return label
    def create_display_frame(self):
        frame = tk.Frame(self.window, height=10,bg=LIGHT_GRAY)
        frame.pack()
        return frame
    def add_to_expression(self, value):
        self.current_expression += str(value)
        self.update_label()
    def create_digit_buttons(self):
        for digit, grid_value in self.digits.items():
            button = tk.Button(self.buttons_frame
                               , text=str(digit), bg=WHITE, fg=LABEL_COLOR, font=DIGITS_FONT_STYLE,
                               borderwidth=0, command=lambda x=digit: self.add_to_expression(x))
            button.grid(row=grid_value[0], column=grid_value[1], sticky=tk.NSEW)
    def clear(self):
        self.current_expression = ""
        self.total_expression = ""
        self.update_label()
    def create_clear_button(self):
        button = tk.Button(self.buttons_frame, text="Clear", bg=red, fg=LABEL_COLOR, font=DEFAULT_FONT_STYLE,
                           borderwidth=0, command=self.clear)
        button.grid(row=4, column=3, sticky=tk.NSEW)
        
#call back funksjon når ok trykkes
    def ok(self):
        global flag, oppdater
        print(self.current_expression)
        if self.current_expression == '123': #riktig kode er definert 123
            print("the code is correct")
            self.clear()
            flag= 10
            open_door_handler(oppdater, 0)          
        else:
            flag =10        
            print("the code is incorrect")
            send_arduino("print_text:invalid code")
            self.current_expression = 'invalid code'
            time.sleep(3)
            deny_access_handler(oppdater,0)
            self.clear()
#call back funksjon når call knapp trykkes            
    def calling(self):
        global oppdater, new_bot,flag
        send_arduino("print_text:behandler")
        send_arduino("someone_is_waiting.")
    def create_call_button(self):
        button = tk.Button(self.buttons_frame, text="call", bg=green, fg=LABEL_COLOR, font=DEFAULT_FONT_STYLE,
                           borderwidth=0, command= self.calling)
        button.grid(row=0, column=1, columnspan=3, sticky=tk.NSEW)
                                      
        
    def create_ok_button(self):
        button = tk.Button(self.buttons_frame, text="ok", bg=green, fg=LABEL_COLOR, font=DEFAULT_FONT_STYLE,
                           borderwidth=0, command= self.ok)
        button.grid(row=4, column=1, columnspan=1, sticky=tk.NSEW)
    def create_buttons_frame(self):
        frame = tk.Frame(self.window)                             
        frame.pack(expand = True, fill = "both")
        return frame

    def update_label(self):
        self.label.config(text=self.current_expression[:11])

    def run(self):
       self.window.mainloop()



#når en handling er ferdig restart funskjonen er kalles opp 
def restart():
    global open_door_request 
    global handling_door 
    send_arduino("print_text:Ring pa")
    send_arduino("set_led:000,000,255")
    open_door_request = False
    handling_door = False
    flag = 0
#når det bestemmes at dåren skal åpnes    
def open_door_handler (update, context):
    global open_door_request, flag
    global handling_door  # denne variabelen blokkerer programet mens dåren skal åpnes for å ikke skjer flere handlinger samtidig
    if flag==10: #flag brukes når kommanen kommer fra gui ikke fra Arduino
        open_door_request =True 
    if open_door_request and not handling_door: #åpner dåra kunn når noen spurt om det 
        print("Døren åpnes")
        handling_door = True
        send_arduino("open_door")
        send_arduino("print_text:velkommen!")
        mixer.music.load('welcome2.wav')
        mixer.music.play()
        time.sleep(1)
        mixer.music.load('welcome.wav')
        mixer.music.play()
        send_arduino("play_buzzer:3000,3000")
        for i in range(10):
#             RGB blinker grønn
            send_arduino("set_led:000,255,000")
            time.sleep(0.5)
            send_arduino("set_led:000,000,000")
            time.sleep(0.5) 
        print("Døren låses igjen")
        send_arduino("close_door")
        flag=0
        restart()
    
       
def deny_access_handler (oppdater, context):
    global open_door_request 
    global handling_door, chat_id, flag
    if flag==10:
        open_door_request =True
    if open_door_request and not handling_door :
        handling_door = True
        send_arduino("print_text:Tilgang avvist")
        mixer.music.load('inncorrect.wav')
        mixer.music.play()
        time.sleep(1)
        send_arduino("play_buzzer:600,2000")
        new_bot.send_message(chat_id=chat_id, text ="denying accsess...")
        for i in range(5):
            send_arduino("set_led:255,000,000")
            time.sleep(0.5)
            send_arduino("set_led:000,000,000")
            time.sleep(0.5)        
    restart()
    flag=0

    
    
# sender kommand til arduino
def send_arduino(text):
    send = text.rstrip() + "\n" #rstrip remove any \n or space from the message 
    ser.write(send.encode('utf-8'))        


    
# oppsett av Camera
print("Starter camera")
cam = PiCamera()
cam.resolution = (1920, 1080)
cam.rotation = 180
bilde_mappe = "/home/pi/Pictures"
if not os.path.exists(bilde_mappe):
    os.mkdir(bilde_mappe)
print("Foto klar")   


def take_pic(update, context):
     global i
     tid = datetime.today()
     #lagrer bildenavn med dato
     bilde_fil = bilde_mappe + "/pic"+str(i)+"_"+ str(tid) + ".jpg"
     cam.capture(bilde_fil)
     new_bot.send_message(chat_id=chat_id,text="Noen er ved inngangsdøren!")
     with open(bilde_fil,'rb') as bilde:#send the pic via telelgam
        new_bot.send_photo(chat_id=chat_id, photo=bilde)
     i=i+1
     #sletter alle bilder når overstiger 5 bilder
     if (i>5):
         i=0
         files= glob.glob('/home/pi/Pictures/*')
         for f in files:
             os.remove(f)
def rec_video(update, context):
    global i
    tid = datetime.today()
    video_fil = bilde_mappe + '/video'+str(i)+str(tid)+'.h264'
    cam.start_recording(video_fil)
    new_bot.send_message(chat_id=chat_id,text="Recording...")
    cam.wait_recording(5)
    cam.stop_recording()
    
    with open(video_fil,'rb') as vid:#send the video via telelgam
        new_bot.send_video(chat_id=chat_id, video=vid, supports_streaming= True)
       
def send_folder(update, context):
    bilde_mappe= "/home/pi/Pictures"
    file_paths = []
    for root, directories, files in os.walk(bilde_mappe):
        for filename in files:
            filepath= os.path.join(root, filename)
            file_paths.append(filepath)
    
    with zipfile.ZipFile('/home/pi/bilder.zip', 'w') as z:
         for file in file_paths:
             z.write(file, compress_type= zipfile.ZIP_DEFLATED)
    
    with open('/home/pi/bilder.zip','rb') as zip1:#send the zip via telelgam
        new_bot.send_document(chat_id=chat_id, document=zip1)

       
    
  
# oppsett av  Telegram bot
print("Starter Telegram")
chat_id = "-752610473"
with open ("/home/pi/.local/share/.telegram_bot_token","r") as f:
    telegram_token = f.read().rstrip()
new_bot = Bot(token=telegram_token)
oppdater = Updater(token=telegram_token) #create an object
dispatcher = oppdater.dispatcher #attribute in the Updater class
dispatcher.add_handler(CommandHandler('ta_bilde',take_pic)) #with writing start in telegram, call function start_handler
dispatcher.add_handler(CommandHandler('godta',open_door_handler, run_async = True)) #with writing godta in telegram, call function open dor, multiple call back at the same time in different trade handler
dispatcher.add_handler(CommandHandler('avvis',deny_access_handler, run_async = True))
dispatcher.add_handler(CommandHandler('video',rec_video, run_async = True))
dispatcher.add_handler(CommandHandler('Send_folder',send_folder, run_async = True))
time.sleep(3)


# Ventemodus
print("Venter i 3 sekunder...")
time.sleep(3)
ser.reset_input_buffer()
oppdater.start_polling() # after 3s, we wait to serial communication becomes correctly initilaized
send_arduino("print_text:Ring pa\n")
send_arduino("set_led:000,000,255")

#tråd 1 til å kjøre gui-en
def disp():
     global flag
     if __name__ == "__main__":
         hmi = HMI()
         hmi.run()

# tråd2 skjekker serial kommunikasjon
def serial_check():
    
    global last_time_button_pressed, open_door_request, handling_door, flag, oppdater, context
    global i
    try:
        while True:
            
            time.sleep(0.01) #run the loop at 100Hz
            if ser.in_waiting> 0 :
                print("detect")
                meld = ser.readline().decode('utf-8').rstrip()
                print(meld)
                if meld == "Ringer":
                    time_now = time.time()
                    if (time_now - last_time_button_pressed > button_pressed_delay) and ( not open_door_request ) and ( not handling_door ):# til å unngå  sende for mange bilder
                        #vi mottar en varsel for hver gjest og ikke flere, hver 5 sec
                       
                        open_door_request = True #blokkerer programmet opptil behandlingen blir ferdig
                        last_time_button_pressed = time_now
                        print("Noen ringer på døren")
                        send_arduino("print_text:Behandler....")
                        mixer.music.load('waiting2.wav')
                        mixer.music.play()
                        take_pic(oppdater, 0)
                        new_bot.send_message(chat_id=chat_id, text="/godta  <------> /avvis")
                    else:
                               ser.reset_input_buffer()
                   
                    
             #når ingen svarer fra telegram, blir alt restart ette 50 sek       
            time_now = time.time()
            if(time_now - last_time_button_pressed > 50) and ( open_door_request ) and ( not handling_door ):
                send_arduino("print_text:no answer try again\n")
                mixer.music.load('incorrect.wav')
                mixer.music.play()
                restart()
                        
    except KeyboardInterrupt:
        print("Avslutter kommunikkasjonen")
        ser.close()
        print("Programmet avsluttes")
        oppdater.stop()



t1 = threading.Thread(target=serial_check, daemon = True)
t2 = threading.Thread(target=disp, daemon = True)
t1.start()
t2.start()