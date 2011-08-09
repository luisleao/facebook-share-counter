
#include <XBee.h>
#include <TimedAction.h>
#include <WiFly.h>
#include <string.h>


//#define CS         10
//#define MOSI       11
//#define MISO       12
//#define SCK        13


XBee xbee = XBee();

// serial high
uint8_t ndCmd[] = {'N','D'};

AtCommandRequest atRequest = AtCommandRequest(ndCmd);
AtCommandResponse atResponse = AtCommandResponse();

ZBTxRequest zbTx = ZBTxRequest();
ZBRxResponse zResponse = ZBRxResponse();

//XBeeAddress64 addr;


int conta = 0;


uint8_t payload_add_ok[] = { 0x76, ' ', 'o', 'n', ' ' };
uint8_t payload_add_err[] = { 0x76, '-', '-', '-', '-' };
uint8_t payload[] = { 0x76, ' ', ' ', ' ', ' ' };


TimedAction timedAction = TimedAction(15000, sendND);




#define BUFFER_LENGTH 81
char buff[BUFFER_LENGTH];
int pointer = 0;
boolean buffer_active = false;




void clean_buffer() {
  pointer = 0;
  memset(buff,0,sizeof(buff)); 
}




void flashLed(int pin, int times, int wait) {
    for (int i = 0; i < times; i++) {
      digitalWrite(pin, HIGH);
      delay(wait);
      digitalWrite(pin, LOW);
      
      if (i + 1 < times) {
        delay(wait);
      }
    }
}



void setup() {
  SpiSerial.begin();
  xbee.begin(9600);
  delay(5000);
  sendND();
  
  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);
  
}

void loop() {
  timedAction.check();
  if (SpiSerial.available())
    carrega_buffer();

  xbee.readPacket();
  if (xbee.getResponse().isAvailable()) {
    process_at_response();
  }

}


void carrega_buffer() {
  while(SpiSerial.available()) {
    char c = SpiSerial.read();
    switch(c) {
      case 10:
        break;
        
      case 13:
        clean_buffer();
        //Serial.println();
        break;
        
      case '\t':
        buffer_active = true;
        break;
        
      case 27:
        buffer_active = false;
        buff[pointer]='\0';
        while(SpiSerial.available()) {
          char c = SpiSerial.read();
        }
        processa_retorno();
        break;
        
      default:
        if (buffer_active) {
          buff[pointer] = c;
          if (pointer < BUFFER_LENGTH) pointer++;
        }
        //Serial.print(c);
    }
  }
}

int getIntValue(char c) {
    if (c >= '0' && c <= '9') {
	  return c - '0';
    } else if (c >= 'a' && c <= 'f') {
	  return c - 'a' + 10;
    } else if (c >= 'A' && c <= 'F') {
	  return c - 'A' + 10;
    } else {
	  return -1;   // getting here is bad: it means the character was invalid
    }
}

void processa_retorno() {
  
  
  String conteudo = String(buff);
  clean_buffer();  
  
  flashLed(13, 5, 100);
  
  //String teste = "0013A200 405D7097 19";
  //16949760/553973993
  //if (conteudo.length() != 20)
  //  return;
  
  //for (int i=7; i>=0; i--) {
  //  int v = getIntValue(conteudo.charAt(i));
  //  enderecoH += v << 28
  //}
  
  uint32_t enderecoH = 0;
  enderecoH += uint32_t(getIntValue(conteudo.charAt(0))) << 28;
  enderecoH += uint32_t(getIntValue(conteudo.charAt(1))) << 24;
  enderecoH += uint32_t(getIntValue(conteudo.charAt(2))) << 20;
  enderecoH += uint32_t(getIntValue(conteudo.charAt(3))) << 16;
  enderecoH += uint32_t(getIntValue(conteudo.charAt(4))) << 12;
  enderecoH += uint32_t(getIntValue(conteudo.charAt(5))) << 8;
  enderecoH += uint32_t(getIntValue(conteudo.charAt(6))) << 4;
  enderecoH += uint32_t(getIntValue(conteudo.charAt(7)));
  
  uint32_t enderecoL = 0;
  enderecoL += uint32_t(getIntValue(conteudo.charAt(8))) << 28;
  enderecoL += uint32_t(getIntValue(conteudo.charAt(9))) << 24;
  enderecoL += uint32_t(getIntValue(conteudo.charAt(10))) << 20;
  enderecoL += uint32_t(getIntValue(conteudo.charAt(11))) << 16;
  enderecoL += uint32_t(getIntValue(conteudo.charAt(12))) << 12;
  enderecoL += uint32_t(getIntValue(conteudo.charAt(13))) << 8;
  enderecoL += uint32_t(getIntValue(conteudo.charAt(14))) << 4;
  enderecoL += uint32_t(getIntValue(conteudo.charAt(15)));

  XBeeAddress64 addr = XBeeAddress64(enderecoH, enderecoL);
  //addr.setMsb(enderecoH); 
  //addr.setLsb(enderecoL); 
  
  String valor = conteudo.substring(16);
  for (int i=0; i<valor.length(); i++) {
    payload[i+1] = valor[i];
  }

  zbTx = ZBTxRequest(addr, payload, sizeof(payload));
  xbee.send(zbTx);

}



void sendND() {
  timedAction.disable();
  //GLCD.println("Requesting...");
  
  atRequest.setCommand(ndCmd);  
  xbee.send(atRequest);
  timedAction.reset();
  timedAction.enable();
}

void sendPayload(XBeeAddress64 addr, char tp) {
  String numero = "    " + String((millis()/1000) % 100); //9999);
  numero = numero.substring(numero.length() - 4);
  for (int i=0; i<numero.length(); i++) {
    payload[i+1] = numero[i];
  }
  if (payload[4] != char((millis()/1000) % 10)) {
    payload[4] = char((millis()/1000) % 10);
  }
  
  payload[1] = tp;

  zbTx = ZBTxRequest(addr, payload, sizeof(payload));
  xbee.send(zbTx);

}

String getHexAddr(long addr) {
  String retorno = String(addr, HEX);
  retorno = "00000000" + retorno;
  return retorno.substring(retorno.length()-8).toUpperCase();
}

void process_at_response() {

    if (xbee.getResponse().getApiId() == ZB_IO_NODE_IDENTIFIER_RESPONSE) {
      xbee.getResponse().getZBRxResponse(zResponse);
      XBeeAddress64 addr = zResponse.getRemoteAddress64(); // 

      String endereco = getHexAddr(addr.getMsb()) + getHexAddr(addr.getLsb());
      //TODO: chamada wifly
      //SpiSerial.print(endereco);
      //SpiSerial.print("/");
      //sendPayload(addr, 'A');
      sendND();
      
    } if (xbee.getResponse().getApiId() == AT_COMMAND_RESPONSE) {
      xbee.getResponse().getAtCommandResponse(atResponse);
      if (atResponse.isOk()) {
        if (atResponse.getValueLength() > 0) {
          if (atResponse.getCommand()[0] == 'N' && atResponse.getCommand()[1] == 'D') {
            if (atResponse.getValueLength() > 0) {
              
              XBeeAddress64 addr = XBeeAddress64(); //XBeeAddress64 
              addr.setMsb((uint32_t(atResponse.getValue()[2]) << 24) + (uint32_t(atResponse.getValue()[3]) << 16) + (uint16_t(atResponse.getValue()[4]) << 8) + atResponse.getValue()[5]);
  	      addr.setLsb((uint32_t(atResponse.getValue()[6]) << 24) + (uint32_t(atResponse.getValue()[7]) << 16) + (uint16_t(atResponse.getValue()[8]) << 8) + (atResponse.getValue()[9]));

              String endereco = getHexAddr(addr.getMsb()) + getHexAddr(addr.getLsb());
              //sendPayload(addr, 'F');
              //chamada wifly
              SpiSerial.print(endereco);
              SpiSerial.print("/");
            }
          }
        }
      }
    }
}




