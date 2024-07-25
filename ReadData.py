import time
import serial
import json
import logging

def setup_logger(logger_name,logfile):
                logger = logging.getLogger(logger_name)
                logger.setLevel(logging.INFO)
                # create file handler which logs even debug messages
                fh = logging.FileHandler(logfile)
                fh.setLevel(logging.INFO)
                # create console handler with a higher log level
                ch = logging.StreamHandler()
                ch.setLevel(logging.INFO)
                # create formatter and add it to the handlers
                formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s [%(filename)s line %(lineno)d]')
                fh.setFormatter(formatter)
                ch.setFormatter(formatter)
                # add the handlers to the logger
                logger.addHandler(fh)
                logger.addHandler(ch)
                return logger

logger=setup_logger('mylogger','/home/sobieradzik/DeDitrich_debug_log.txt')
logger.info("-------------------------------")

from DeDitrichMCR3_RS232_RemehaPCU05 import DeDitrichMCR3_RS232_RemehaPCU05 as Boiler

def main():
    boiler = Boiler()
    boiler.DoLogs(False)
    boiler.start()
    time.sleep(5)
    logger.warning('------------STARTING PROGRAMMING----------------')
    logger.warning('Programming FEEDBACK: '+json.dumps(boiler.SetDHWState(False), indent=2))
    #time.sleep(15)
    #boiler.Stop()
    
    #logging.info(json.dumps(boiler.LastTransmissionMessages(), indent=2))
    #logging.info('---------------------------------')
    #logging.info(json.dumps(boiler.Monitoring(), indent=2))

    
    
    #data = boiler.GetSample()    
    #print(json.dumps(data, indent=2))
    #data = boiler.GetID()    
    #print(json.dumps(data, indent=2))
    #data = boiler.GetParams()    
    #print(json.dumps(data, indent=2))
    #data = boiler.SetParams(CH=True, DHW=False)    
    #print(json.dumps(data, indent=2))
 
if __name__ == "__main__":
    main()