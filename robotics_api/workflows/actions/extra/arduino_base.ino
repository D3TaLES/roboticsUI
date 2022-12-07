void setup() {
	Serial.begin(115200);
}
void loop() {
	if(Serial.available() > 0) {
		int data = Serial.parseInt();
    Serial.print(data);
    if(data==0){
		  Serial.print("down-success");
      }
    else if (data==1) {
      Serial.print("up-success");
    }
	}
}