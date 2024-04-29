import threading
import serial
import json
import logging
import traceback
from datetime import date, datetime
import time

class DeDitrichMCR3_RS232_RemehaPCU05(threading.Thread):
    
    def __init__(self):
        super(DeDitrichMCR3_RS232_RemehaPCU05, self).__init__()
        logging.warning('DeDitrichMCR3_RS232_RemehaPCU05: __init__ call')   
        self.__SerialPort = '/dev/ttyUSB0'   #for RPi
        #self.__SerialPort = 'COM5'            #for Windows OS
        self.__stop = True    
        self.__delayBeforeReading = 0.4
        self.__sleepTime = 10
        self.__programming = False
        self.__programmingLock = False
        self.__obsolenceTime = 10 #inSeconds
        self.__logs = True
        self.__device = {}
        self.__device['hasSample'] = False
        self.__device['hasID'] = False
        self.__device['hasParams'] = False
        self.__device['TimeStamp'] = '2000-01-01 00:00:00'
        lastProgramming = {}
        lastProgramming['Success'] = False
        lastProgramming['TimeStamp'] = '2000-01-01 00:00:00'
        lastProgramming['Msg'] = 'Not executed yes'
        self.__device['lastProgramming'] = lastProgramming
        self.__origin = {}
        self.__settings = {}
        self.__settings['readyToSend'] = False
        self.__opened = False
        self.__boiler = self.CreateBoiler()

#----------------------
#public members
    def run(self):
        logging.warning('DeDitrichMCR3_RS232_RemehaPCU05: run thread')   
        self.__Connect()
        while self.__stop:
            try:
                if not self.__programming:
                    self.__ReadSample(log=self.__logs)
                    #self.__ReadID(log=self.__logs)                     #unuseful for me
                    self.__ReadParams(log=self.__logs)
                    self.__device['TimeStamp'] = getTimeStamp()
                    logging.info('TimeStamp: '+ str(self.__device['TimeStamp']))
                else:
                    self.__device['lastProgramming'] = self.__SendParams()
            except Exception as ex:
                logging.error(ex)
                traceback.print_exc()    
            #time.sleep(self.__sleepTime)
			t=0
			while t < self.__sleepTime and not self.__programming:		#interrupt sleeping when programming request
				time.sleep(2)
				t+=2
			
        self.__Disconnect()
        logging.info('DeDitrichMCR3_RS232_RemehaPCU05: stopped thread')   
    
    def Stop(self):
        self.__stop = False
    
    def DoLogs(self,logs):
        self.__logs = logs

    def Monitoring(self):
#        if True or self.__logs:
#            res = {}
#            res['DataFromDevice'] = self.__device
#            private = {}
#            private['Connection'] = self.__opened
#            private['ObsolenceOfData'] = self.__GetObsolence()
#            private['ProgrammingMode'] = self.__programming
#            return res
        return self.__device

    def LastTransmissionMessages(self):
        return self.__origin

    def SetDHWState(self, DHWState):
        if self.__programmingLock:
            return False
        payload = {}
        fields = []
        if self.__settings['readyToSend']:
            payload = self.__settings['payload']
            fields = payload['fields']
        fields.append('DHWState')
        payload['fields'] = fields
        payload['DHWState'] = DHWState
        self.__settings['payload'] = payload
        self.__settings['readyToSend'] = True
        self.__programming = True
        return True

    def SetCHState(self, CHState):
        if self.__programmingLock:
            return False
        payload = {}
        fields = []
        if self.__settings['readyToSend']:
            payload = self.__settings['payload']
            fields = payload['fields']
        fields.append('CHState')
        payload['fields'] = fields
        payload['CHState'] = CHState
        self.__settings['payload'] = payload
        self.__settings['readyToSend'] = True
        self.__programming = True
        return True
            
#----------------------
#private members
    def CreateBoiler(self):
        boiler = None
        try: 
            boiler=serial.Serial(
                port=self.__SerialPort,
                baudrate=9600,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=10
            )
            self.__opened = True
            logging.warning('Openned MCR3 connection ...')
        except Exception as ex:
                logging.error(ex)
                traceback.print_exc()    
        return boiler
                
    def __Connect(self):
        try:
            if self.__boiler is None:
                self.__boiler = self.CreateBoiler()
            if not self.__opened and not self.__boiler is None:
                logging.warning('Opening MCR3 connection ...')
                self.__boiler.open()
                self.__opened = True
                logging.warning('Openned!')
            if self.__boiler.isOpen():
                self.__boiler.flushInput()
                self.__boiler.flushOutput()
                #logging.debug('Streams flushed')
        except Exception as ex:
            logging.error(ex)
            traceback.print_exc()   
            self.__opened = False             
    
    def __Disconnect(self):
        try:
            if not self.__boiler is None:
                self.__boiler.close()
                logging.warning('MCR3 connection closed!')
        except Exception as ex:
            logging.error(ex)
            traceback.print_exc()
        self.__opened = False

    def __ReqRes(self, requestCommand, readdata=True, delayBeforeReading=1, log=True):
        self.__Connect()
        self.__boiler.write(bytearray.fromhex(requestCommand))
        time.sleep(delayBeforeReading)
        if log:
            logging.info('Reading response ...')
        if readdata:
            bytesToRead = self.__boiler.inWaiting()
            device_read = self.__boiler.read(bytesToRead).hex()
            if log:
                logging.info('>> '+ device_read)
            return device_read
        return ''
    
    def __SeriesReqRes(self, origin, readdata=True, delayBeforeReading=1, log=True):
        for i in range(len(origin)):
            if log:
                logging.info('Requesting: '+str(i+1)+'/'+str(len(origin))+' ...')
            origin[i]['res'] = self.__ReqRes(requestCommand=origin[i]['req'], readdata=readdata, delayBeforeReading=delayBeforeReading, log=log)
            origin[i]['res_length'] = len(origin[i]['res'])
        return origin
        
    def __ReadSample(self, log=True):
        response = {}
        origin = []
        origin.append({'req':'02fe010508020169ab03'})
        if log:
            logging.info('Requesting Remeha Sample ...')
        try:
            origin = self.__SeriesReqRes(origin, delayBeforeReading=self.__delayBeforeReading, log=log)
        except Exception as ex:
            logging.error(ex)
            traceback.print_exc()
            self.__Disconnect()
            return response
        self.__origin['RemehaSample'] = origin
        storedParams = []
        #keys: 't'-title, 'i'- ID in reqs array, 's'-startID, 'e'-endID, 'f'-multiplyingfactor
        storedParams.append({'t':'Flow Temp',           'i':0, 's':14, 'e':18, 'f':0.01})
        storedParams.append({'t':'Return Temp',         'i':0, 's':18, 'e':22, 'f':0.01})
        storedParams.append({'t':'DHW-in Temp',  		'i':0, 's':22, 'e':26, 'f':0.01})	#will be extended in basis of XLS map
        err = False
        logging.debug('Remeha Sample response: '+origin[0]['res'])
        for param in storedParams:
            try:
                if param['e']-param['s'] == 4:
                    response[param['t']] = round((int(origin[param['i']]['res'][param['s']+2:param['e']],16)*256 + int(origin[param['i']]['res'][param['s']:param['s']+2],16)) * param['f'], 2)
                elif param['e']-param['s'] == 2:
                    response[param['t']] = int(origin[param['i']]['res'][param['s']:param['e']],16)
            except Exception as ex:
                logging.warning(ex)
                logging.warning(json.dumps(param, indent=2))
                logging.warning(json.dumps(origin, indent=2))
                traceback.print_exc()
                self.__Disconnect()
                err = True
        if not err:
            self.__device['hasSample'] = True
            self.__device['RemehaSample'] = response
        #print(response)
        if log:
            logging.debug(json.dumps(response, indent=2))
        return response  

    def __ReadID(self, log=True):
        response = {}
        origin = []
        origin.append({'req':'02fe000508010bd49c03'})
        origin.append({'req':'02fe010508010be95c03'})
        origin.append({'req':'02fe030508010b909c03'})
        origin.append({'req':'02fe0b0508010b715d03'})
        #02 fe 01 05 08 02 01 69 ab 03  ???
        if log:
            logging.info('Requesting Remeha ID ...')
        try:
            origin = self.__SeriesReqRes(origin, delayBeforeReading=self.__delayBeforeReading, log=log)
        except Exception as ex:
            logging.error(ex)
            traceback.print_exc()
            self.__Disconnect()
            return response
        self.__origin['RemehaID'] = origin
        self.__device['hasID'] = True
        self.__device['RemehaID'] = response
        #print(response)
        if log:
            logging.debug(json.dumps(response, indent=2))
        return response     
       
    def __ReadParams(self, log=True):
        response = {}
        origin = []
        origin.append({'req':'02fe0005081014990403'})
#        origin.append({'req':'02fe000508101558c403'})  #unuseful for me; waste of time
#        origin.append({'req':'02fe000508101618c503'})
#        origin.append({'req':'02fe0005081017d90503'})
#        origin.append({'req':'02fe0005081018990103'})
#        origin.append({'req':'02fe000508101958c103'})
#        origin.append({'req':'02fe000508101a18c003'})
#        origin.append({'req':'02fe000508101bd90003'})
        #0742a0000540d20742a0000540d20742a0000540d2
        if log:
            logging.info('Requesting Remeha Params ...')
        try:
            origin = self.__SeriesReqRes(origin, delayBeforeReading=self.__delayBeforeReading, log=log)
        except Exception as ex:
            logging.error(ex)
            traceback.print_exc()
            self.__Disconnect()
            return response
        self.__origin['RemehaParams'] = origin
        storedParams = []
        #keys: 't'-title, 'i'- ID in reqs array, 's'-startID, 'e'-endID, 'f'-multiplyingfactor
        #storedParams.append({'t':'Max flow temperature during CH mode',     'i':0, 's':14, 'e':16, 'f':1})
        storedParams.append({'t':'Desired DHW temp',        'i':0, 's':16, 'e':18, 'f':1})
        storedParams.append({'t':'CH/DHW on/off',           'i':0, 's':18, 'e':20, 'f':1})
        storedParams.append({'t':'ComfortDHW',              'i':0, 's':20, 'e':22, 'f':1}) #will be extended in basis of XLS map
        err = False
        for param in storedParams:
            try:
                response[param['t']] = int(origin[param['i']]['res'][param['s']:param['e']],16)*param['f']
            except Exception as ex:
                logging.warning(ex)
                logging.warning('param: '+json.dumps(param, indent=2))
                logging.warning('origin: '+json.dumps(origin, indent=2))
                traceback.print_exc()
                self.__Disconnect()
                err = True
        if not err:
            self.__device['hasParams'] = True
            self.__device['RemehaParams'] = response
        #print(response)
        if log:
            logging.debug(json.dumps(response, indent=2))
        return response        
    
    def __SendParams(self, log=True):
        response = self.__device['lastProgramming']
        response['Success'] = False
        response['TimeStamp'] = getTimeStamp()
        response['Msg'] = 'Programming started'
        if self.__programmingLock:
            response['Msg'] = 'Currentlu programming mode. Wait...'
            return response
        if not self.__programming:
            response['Msg'] = 'Method __SendParams run but the programming mode not set'
            return response
        self.__programmingLock = True
        params2Send = self.__CalculateParams2Send()
        if params2Send['empty']:
            self.__programming = False
            self.__programmingLock = False
            response['Msg'] = params2Send['Msg']
            return response
        CHDHW = ''
        par1ext = ''
        par2ext = ''
        for param in params2Send['fields']: 
            if param == 'CH/DHW on/off':
                CHDHW = str(params2Send[param])
                if params2Send[param] == 0:
                    par1ext = '025303'
                    par2ext = 'acf1dfc403'
                elif params2Send[param] == 1:
                    par1ext = '029203'
                    par2ext = 'adcdde4503'
                elif params2Send[param] == 2:
                    par1ext = '019103'
                    par2ext = 'ae89de8603'
                elif params2Send[param] == 3:
                    par1ext = '015003'
                    par2ext = 'afb5df0703'
        if log:
            logging.debug('Programming CH_DHW ...')
            logging.debug('CHDHW: '+CHDHW+' | par1ext: '+par1ext+' | par2ext: '+par2ext)
        origin = []
        origin.append({'req':'0742a0000540d20742a0000540d20742a0000540d2'})
        origin.append({'req':'02520506010b5b03'})
        origin.append({'req':'02520506010b5b03'})
        origin.append({'req':'02520506010b5b03'})
        try:
            self.__SeriesReqRes(origin, readdata=False, delayBeforeReading=self.__delayBeforeReading)
        except Exception as ex:
            logging.error(ex)
            traceback.print_exc()
            self.__Disconnect()
            response['Msg'] = ex
            self.__programming = False
            self.__programmingLock = False
            return response
        #self.__ReadID()	#Remeha Recon send these befor programming,
        #self.__ReadID()    #however it works at me without it
        origin = []
        origin.append({'req':'02fe000508080c930e03'})
        origin.append({'req':'02fe000518111446370'+CHDHW+'0202ffffffffffffffffffffff'+par1ext})
        origin.append({'req':'02fe0005181115251e0e1414ff28231414f1090af6000f216903'})
        origin.append({'req':'02fe0005181116060001020000000100571e01ffffffff0af803'})
        origin.append({'req':'02fe0005181117ffffffffffff323c5000c8050012'+par2ext})
        origin.append({'req':'02fe0005181118ff28465a3219051e0a1e0309413f1464928b03'})
        origin.append({'req':'02fe00051811196464074605051e0205002800000fbc09328603'})
        origin.append({'req':'02fe000518111a0078000a051e654b02fe0a000a64ff289f6103'})
        origin.append({'req':'02fe000518111b1a02050502020a14141905ffffffc238ef2903'})
        origin.append({'req':'02fe0005081f0c9cfe03'})
        try:
            origin = self.__SeriesReqRes(origin, delayBeforeReading=self.__delayBeforeReading)
        except Exception as ex:
            logging.error(ex)
            traceback.print_exc()
            self.__Disconnect()
            response['Msg'] = ex
            self.__programming = False
            self.__programmingLock = False
            return response
        response['Msg'] = 'Done'
        response['Success'] = True
        self.__origin['Programming'] = origin
        #self.__ReadParams()	#Remeha Recon send these after programming, I did it in the next loop step
        if log:
            logging.debug(json.dumps(response, indent=2))
        self.__programming = False
        self.__programmingLock = False
        return response
    
    def __CalculateParams2Send(self):
        res = {}
        res['empty'] = True
        fields = []
        try:
            if not self.__settings['readyToSend']:
                raise Exception("No new values of CHDHW in self.__settings to send")
            if not self.__device['hasParams'] or self.__GetObsolence():
                raise Exception("No current params read from boiler")
            params2Send = self.__settings['payload']['fields']
            res['Msg'] = ''
            currState = self.__device['RemehaParams']['CH/DHW on/off']
            for param in params2Send: 
                if param == 'DHWState':
                    if currState == 0 and self.__settings['payload'][param]:
                        res['CH/DHW on/off'] = 3
                    elif currState == 1 and not self.__settings['payload'][param]:
                        res['CH/DHW on/off'] = 2
                    elif currState == 2 and self.__settings['payload'][param]:
                        res['CH/DHW on/off'] = 1
                    elif currState == 3 and not self.__settings['payload'][param]:
                        res['CH/DHW on/off'] = 0
                    else:
                        logging.warning('CH/DHW: No change is required. New params are the same as boiler has.')
                        logging.warning('Programming will be continue for other new params if defined.')
                        res['Msg'] += 'DHW: No new param.'
                        continue
                    currState = res['CH/DHW on/off']
                    res['empty'] = False
                    if 'CH/DHW on/off' not in fields:
                        fields.append('CH/DHW on/off')
                elif param == 'CHState':
                    #0:CH Off DHW Off       00 -> 00
                    #1:CH  On DHW  On;      01 -> 11
                    #2:CH  On DHW Off;      10 -> 10
                    #3:CH Off DHW  On       11 -> 01
                    if currState == 0 and self.__settings['payload'][param]:
                        res['CH/DHW on/off'] = 2
                    elif currState == 1 and not self.__settings['payload'][param]:
                        res['CH/DHW on/off'] = 3
                    elif currState == 2 and not self.__settings['payload'][param]:
                        res['CH/DHW on/off'] = 0
                    elif currState == 3 and self.__settings['payload'][param]:
                        res['CH/DHW on/off'] = 1
                    else:
                        logging.warning('CH/DHW: No change is required. New params are the same as boiler has.')
                        logging.warning('Programming will be continue for other new params if defined.')
                        res['Msg'] += 'CH: No new param.'
                        continue
                    currState = res['CH/DHW on/off']
                    res['empty'] = False
                    if 'CH/DHW on/off' not in fields:
                        fields.append('CH/DHW on/off')
            res['fields'] = fields
            self.__settings['readyToSend'] = False
            self.__settings.pop('payload', None)
        except Exception as ex:
            logging.warning(ex)
            traceback.print_exc()   
            res['Msg'] = str(ex)
        return res

    def __GetObsolence(self): #return True if TimeStamp is obsolete
        FMT = '%Y-%m-%d %H:%M:%S'
        dT = datetime.strptime(getTimeStamp(), FMT) - datetime.strptime(self.__device['TimeStamp'], FMT)
        logging.debug('----------------- diff='+str(dT.total_seconds())+'s')
        if dT.total_seconds() > self.__obsolenceTime:
            return True
        return False
        
        
def getTimeStamp():
    return str(date.today()) + " " + datetime.now().strftime("%H:%M:%S")

