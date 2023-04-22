 #include <LiquidCrystal.h>
#include <Servo.h>
#include <Wire.h>

#define echo A0
#define trig A1
#define servo_door_pin 10
#define servo_lock_pin 11
#define rgb_red 9
#define rgb_green 8
#define rgb_blue 7 
#define buzzer_pin 6
#define button_pin 12
#define lcd_rs A4
#define lcd_e A5
#define lcd_d4 2
#define lcd_d5 3
#define lcd_d6 4
#define lcd_d7 5

#define servo_open 240
#define servo_close 70

LiquidCrystal lcd(lcd_rs,lcd_e,lcd_d4,lcd_d5,lcd_d6,lcd_d7); //create the lcd object 

Servo servo_door; //create the servo object
Servo servo_lock;

//globale variables
unsigned long LastTime_button_changed = millis(); 
unsigned long debounce_delay = 50;
byte previous_button_state;
long Duration;
int distance;

void servo_init(){
  
  servo_door.attach(servo_door_pin);
  servo_door.write(servo_close); //set by default on close position
  servo_lock.attach(servo_lock_pin);
  servo_lock.write(160);
  
  }

void serial_init(){
    
  Serial.begin(9600);
  while(!Serial){} 
  while(Serial.available()>0){ //clear input_buffer
  Serial.read();
  }
  }
  
void lcd_init(){
  
  lcd.begin(16,2);
  lcd.print("Starter.....");
  delay(1000);
  lcd.clear();
  
  }

void setup() {
  servo_init();
  serial_init();
  lcd_init();
  pinMode(trig,OUTPUT);
  pinMode(echo,INPUT);
  
  pinMode(button_pin,INPUT);
  pinMode(buzzer_pin,OUTPUT);
  pinMode(rgb_red,OUTPUT);
  pinMode(rgb_green,OUTPUT);
  pinMode(rgb_blue,OUTPUT);

  

  previous_button_state = digitalRead(button_pin);



  
}

void loop() {
  //debouncing
  digitalWrite(trig, LOW);
  delayMicroseconds(2);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);
  Duration = pulseIn(echo, HIGH);
  distance = Duration * 0.034/2;
  unsigned long time_now = millis(); 
  if(time_now - LastTime_button_changed >= debounce_delay){ //if we have spent enough time since the button has changed for the last time
    byte button_state = digitalRead(button_pin);
    if (distance<= 5){
    LastTime_button_changed= time_now;
    servo_lock.write(90);
    delay(50);
    for(int i= servo_close ; i< servo_open ; i++){
      servo_door.write(i);
      delay(30);
    }
    delay(5);
    for(int i= servo_open ; i>servo_close ; i--){
      servo_door.write(i);
      delay(30);
      }
    servo_lock.write(160);
  } 
  
      
    if(previous_button_state != button_state){ //button is pressed or released
      LastTime_button_changed = time_now;
      previous_button_state = button_state;
      if(button_state == HIGH){ //is pressed
        Serial.println("Ringer"); //send a message to serial
      }
    }
  }
 if(Serial.available()>0){ //check if we have recieved something from serial port
  String cmd = Serial.readStringUntil('\n'); //read the whole message
  //process the command from rpi
  if( cmd== "open_door" ){
    servo_lock.write(90);
    delay(50);
    for(int i= servo_close ; i< servo_open ; i++){
      servo_door.write(i);
      delay(30);
      
      }

    }  
  else if (cmd== "close_door"){
    for(int i= servo_open ; i>servo_close ; i--){
      servo_door.write(i);
      delay(30);
      }
     
    servo_lock.write(160);  
     
     //servo_door.write(servo_close);
    }
  else if(cmd.startsWith("print_text:")){
    cmd.remove(0,11);
    String line1 = cmd.substring(0,16);
    String line2 = cmd.substring(16);
    lcd.clear();
    lcd.setCursor(2,2);
    lcd.print(line1);
    lcd.setCursor(2,3);
    lcd.print(line2);
    }
   else if(cmd.startsWith("play_buzzer:")){

    cmd.remove(0,12);
    int comaindex = cmd.indexOf(','); //find the place of coma to define freq and 
    int freq = cmd.substring(0, comaindex).toInt(); // converting of string to int and put it into the freq
    int duration = cmd.substring(comaindex + 1).toInt();
      tone(buzzer_pin, freq, duration);
    }
    else if(cmd.startsWith("someone_is_waiting.")){

    cmd.remove(0,19);
    
    Serial.println("Ringer");
    }
    else if(cmd.startsWith("set_led:")){
    cmd.remove(0,8);
    //000, 000, 000
    int red = cmd.substring(0,3).toInt();
    int green = cmd.substring(4,7).toInt();
    int blue = cmd.substring(8).toInt();
    analogWrite(rgb_red,red);
    analogWrite(rgb_blue,blue);
    analogWrite(rgb_green,green);
    }
  else {
     while(Serial.available()>0){ //clear input_buffer
  Serial.read();
  }
  
    }
   
  } 
}
  
