#include <XBee.h>


const int firstEMatch = 5;
const int firstBoardIdSwitch = 2;
const int numBoardIdSwitch = 2;
const int numEMatch[] = {48, 32, 4, 4};
const int numBoards = 4;
const int fireTime = 1000; // time in ms to keep eMatch on
unsigned long eMatchOnTime[48];

int boardId = -1;

XBee xbee = XBee();
ZBRxResponse rx = ZBRxResponse();
uint8_t infoPayload[] = { 'I', 0, 0 };
XBeeAddress64 addr64 = XBeeAddress64(0x00000000, 0x00000000);
ZBTxRequest zbTx = ZBTxRequest(addr64, infoPayload, sizeof(infoPayload));
//ZBTxStatusResponse txStatus = ZBTxStatusResponse();

void boardIdSetup() {
  for (int i = firstBoardIdSwitch; i < firstBoardIdSwitch + numBoardIdSwitch; i++) {
    pinMode(i, INPUT_PULLUP);
  }
}

void eMatchSetup() {
  // enable output pins and set low
  for (int i = 0; i < numEMatch[boardId]; i++)
  {
    pinMode(i + firstEMatch, OUTPUT);
    digitalWrite(i + firstEMatch, HIGH);
    eMatchOnTime[i] = 0;
  }
}

void xBeeSetup() {
  Serial.begin(9600);
  xbee.setSerial(Serial);
}

void getBoardId() {
  boardId = 0;
  for (int i = 0; i < numBoardIdSwitch; i++) {
    boardId |= !digitalRead(i + firstBoardIdSwitch) << i;
  }
}

void xBeeRead() {
  xbee.readPacket();
    
  if (xbee.getResponse().isAvailable() && xbee.getResponse().getApiId() == ZB_RX_RESPONSE) {
    xbee.getResponse().getZBRxResponse(rx);
    if (rx.getDataLength() > 0) {
      switch (rx.getData(0)) {
        case 'f':
          if (rx.getDataLength() == 2) {
            startFire(rx.getData(1));
          } // else error no eMatch id
          break;
        case 'i':
          sendBoardInfo();
          break;
        //default error unknown command
      }
    } // else error no data?
  } // else ZB_TX_STATUS_RESPONSE
}

void startFire(int eMatch) {
  if (eMatch >= 0 && eMatch < numEMatch[boardId]) {
    digitalWrite(eMatch + firstEMatch, LOW);
    eMatchOnTime[eMatch] = millis();
  }
}

void stopFire(int eMatch) {
  digitalWrite(eMatch + firstEMatch, HIGH);
  eMatchOnTime[eMatch] = 0;
}

void checkStopFire() {
  for (int i = 0; i < numEMatch[boardId]; i++) {
    if (eMatchOnTime[i] != 0 && eMatchOnTime[i] + fireTime < millis()) {
      stopFire(i);
    }
  }
}

void sendBoardInfo() {
  infoPayload[1] = boardId;
  infoPayload[2] = numEMatch[boardId];
  xbee.send(zbTx);
}

void setup() {
  boardIdSetup();
  getBoardId();
  if (boardId >= numBoards) {
    //error
    exit(0);
  }
  eMatchSetup();
  xBeeSetup();
}

void loop() {
  xBeeRead();
  checkStopFire();
  /*for (int i = 0; i < numEMatch[boardId]; i++) {
    digitalWrite(i + firstEMatch, LOW);
    delay(1000);
    digitalWrite(i + firstEMatch, HIGH);
  }*/
}
