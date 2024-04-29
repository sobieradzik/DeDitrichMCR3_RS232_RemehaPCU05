import time
import serial	#pip install pyserial
import json
import logging
from DeDitrichMCR3_RS232_RemehaPCU05 import DeDitrichMCR3_RS232_RemehaPCU05 as Boiler

def main():
    logging.basicConfig(
#            level=logging.DEBUG,
            level=logging.INFO,
#            level=logging.WARN,
#            level=logging.ERROR,
            format="%(asctime)s [%(levelname)s] %(message)s [%(filename)s line %(lineno)d]",
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[	logging.FileHandler("debug.log"),
                        logging.StreamHandler()])
    boiler = Boiler()
    boiler.DoLogs(False)
    boiler.start()
    time.sleep(5)
    logging.warning('------------STARING PROGRAMMING----------------')
    logging.warning('Programming FEEDBACK: '+json.dumps(boiler.SetDHWState(False), indent=2))
    #time.sleep(15)
    #boiler.Stop()
    
    logging.info(json.dumps(boiler.LastTransmissionMessages(), indent=2))
    logging.info('---------------------------------')
    logging.info(json.dumps(boiler.Monitoring(), indent=2))
 
if __name__ == "__main__":
    main()