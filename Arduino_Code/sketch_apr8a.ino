// Dual Joystick + 4 Button Controller
// Right joystick = Left / Right
// Left joystick = Forward / Backward
// Buttons = D3, D4, D5, D6

int rightX = A1;
int rightY = A0;

int leftX = A2;
int leftY = A3;

int btn1 = 3;
int btn2 = 4;
int btn3 = 5;
int btn4 = 6;

void setup()
{
  Serial.begin(115200);

  pinMode(btn1, INPUT_PULLUP);
  pinMode(btn2, INPUT_PULLUP);
  pinMode(btn3, INPUT_PULLUP);
  pinMode(btn4, INPUT_PULLUP);
}

void loop()
{
  int a0 = analogRead(rightY);
  int a1 = analogRead(rightX);

  int a2 = analogRead(leftX);
  int a3 = analogRead(leftY);

  int b1 = 0;
  int b2 = 0;
  int b3 = 0;
  int b4 = 0;

  if (digitalRead(btn1) == LOW) b1 = 1;
  if (digitalRead(btn2) == LOW) b2 = 1;
  if (digitalRead(btn3) == LOW) b3 = 1;
  if (digitalRead(btn4) == LOW) b4 = 1;

  Serial.print(a0);
  Serial.print(",");

  Serial.print(a1);
  Serial.print(",");

  Serial.print(a2);
  Serial.print(",");

  Serial.print(a3);
  Serial.print(",");

  Serial.print(b1);
  Serial.print(",");

  Serial.print(b2);
  Serial.print(",");

  Serial.print(b3);
  Serial.print(",");

  Serial.println(b4);

  delay(5);
}