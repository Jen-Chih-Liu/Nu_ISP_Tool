#from PyQt5 import QtCore, QtGui, QtWidgets 
from PyQt5.QtCore import QThread, pyqtSignal 
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QApplication ,QStyleFactory
from usb.backend import libusb1
import serial.tools.list_ports
import argparse
import usb.util
import sys
import usb.core
import usb.util
import platform
import struct
from argparse import ArgumentParser
import logging
from GUI_MODE_1 import Ui_Form
import time
import subprocess 

import win32api, win32gui 

#isp command table
CMD_UPDATE_APROM=0xA0
CMD_READ_CONFIG=0XA2
CMD_SYNC_PACKNO=0XA4
CMD_GET_FWVER=0XA6
CMD_GET_DEVICEID=0XB1
CMD_RUN_APROM=0XAB
CMD_RUN_LDROM=0XAC
CMD_RESET=0xAD
CMD_GET_FLASHMODE=0xCA
CMD_CONNECT=0xAE
#isp command

class ISP_COMMAND:
		def __init__(self):
			self.PacketNumber=0
			self.GUI_MODE=0
			self.AP_CHECKSUM=0;
			self.AP_FILE=[]
			self.dev=None
			self.ep_in=None
		def Interface(self,VID_in=0x0416,PID_in=0x3F00):
			#self.dev = usb.core.find(idVendor=VID_in, idProduct=PID_in)
			self.dev = usb.core.find(idVendor=0x0416, idProduct=0x3F00)
			if self.dev is None:
				#raise ValueError('USB Device not found, please check the USB Cable and ISP FW in LDROM')
				#sys.exit(0)	
				return False
			else:
				return True

		def OPEN_USB(self,VID_in=0x0416,PID_in=0x3F00):
			self.dev = usb.core.find(idVendor=0x0416, idProduct=0x3F00)
			if self.dev is None:
				#raise ValueError('USB Device not found, please check the USB Cable and ISP FW in LDROM')
				#sys.exit(0)	
				return False
			#linux
			if(platform.system()=="linux"): 
				if self.dev.is_kernel_driver_active(0): 
					self.dev.detach_kernel_driver(0)
			self.dev.set_configuration()
			usb.util.claim_interface(self.dev, 0)
			self.dev.reset()
			cfg=self.dev[0]
			intf=cfg[(0,0)]
			self.ep_in= usb.util.find_descriptor(intf,# match the first OUT endpoint
													custom_match = \
													lambda e: \
													usb.util.endpoint_direction(e.bEndpointAddress) == \
													usb.util.ENDPOINT_IN)
			#print("USB Find. \n\r")
			logging.info("USB Find.")
			return True
		def CLOSE_USB(self):
			self.dev.reset()

		def USB_TRANSFER(self, outpackage, packagenumber,write_only):
			outpackage[4]=packagenumber&0xff
			outpackage[5]=packagenumber>>8&0xff
			outpackage[6]=packagenumber>>16&0xff
			outpackage[7]=packagenumber>>24&0xff
			test=self.dev.write(0x02,outpackage)
			if (write_only==1):
				return_buffer=[]
				return return_buffer
			return_str=self.dev.read(0x81,64,10000) #return by string
			return_buffer=bytearray(return_str)
			checksum=0
			for i in range(len(outpackage)):
				checksum=checksum+outpackage[i]
			#print("checksum=0x%x"%checksum)
			packege_checksum=0
			packege_checksum=return_buffer[0]
			packege_checksum=(return_buffer[1]<<8)|packege_checksum
			if checksum!=packege_checksum:
				logging.info("checksum error")
				return_buffer=[]
				return return_buffer
			RPN=0
			RPN=return_buffer[4]
			RPN=(return_buffer[5]<<8)|RPN
			RPN=(return_buffer[6]<<16)|RPN
			RPN=(return_buffer[7]<<24)|RPN
			if RPN!=(packagenumber+1):
				logging.info("package number error")
				return_buffer=[]
				return return_buffer
			return return_buffer

		def ISP_CMD_CONNECT(self):
			ISP_PACKAGE=[0 for i in range(64)] # 64 byte data buffer is all zero
			ISP_PACKAGE[0]=CMD_CONNECT #command
			self.PacketNumber=0x01
			r_buf=self.USB_TRANSFER(ISP_PACKAGE,self.PacketNumber,0)
			if len(r_buf)==64:
				return True
			else:
				return False

		def ISP_CMD_SYNC_PACKNO(self):
			self.PacketNumber =self.PacketNumber+2
			ISP_PACKAGE = [0 for i in range(64)] 
			ISP_PACKAGE[0]=CMD_SYNC_PACKNO
			ISP_PACKAGE[8]=self.PacketNumber&0xff
			ISP_PACKAGE[9]=self.PacketNumber>>8&0xff
			ISP_PACKAGE[10]=self.PacketNumber>>16&0xff
			ISP_PACKAGE[11]=self.PacketNumber>>24&0xff
			r_buf=self.USB_TRANSFER(ISP_PACKAGE,self.PacketNumber,0)
			if len(r_buf)==64:
				return True
			else:
				return False
		def ISP_CMD_GET_FWVER(self):
			self.PacketNumber=self.PacketNumber+2
			ISP_PACKAGE = [0 for i in range(64)] 
			ISP_PACKAGE[0]=CMD_GET_FWVER
			buf=self.USB_TRANSFER(ISP_PACKAGE,self.PacketNumber,0)
			FW_VERSION=buf[8]
			#print("FW_VERSION=0x%8x" % FW_VERSION)
			logging.info("FW_VERSION=0x%8x" % FW_VERSION)
			return FW_VERSION

		def ISP_CMD_RUN_APROM(self):
			self.PacketNumber=self.PacketNumber+2
			ISP_PACKAGE = [0 for i in range(64)] 
			ISP_PACKAGE[0]=CMD_RUN_APROM
			self.USB_TRANSFER(ISP_PACKAGE,self.PacketNumber,1)
			#no return 

		def ISP_CMD_GET_DEVICEID(self):
			self.PacketNumber=self.PacketNumber+2
			ISP_PACKAGE = [0 for i in range(64)] 
			ISP_PACKAGE[0]=CMD_GET_DEVICEID
			buf=self.USB_TRANSFER(ISP_PACKAGE,self.PacketNumber,0) 
			PID=buf[8]|buf[9]<<8|buf[10]<<16|buf[11]<<24 
			logging.info("PID=0x%8x" % PID) 
			return PID

		def ISP_CMD_READ_CONFIG(self):
			self.PacketNumber=self.PacketNumber+2
			ISP_PACKAGE = [0 for i in range(64)] 
			ISP_PACKAGE[0]=CMD_READ_CONFIG
			buf=self.USB_TRANSFER(ISP_PACKAGE,self.PacketNumber,0) 
			CONFIG0=buf[8]|buf[9]<<8|buf[10]<<16|buf[11]<<24 
			CONFIG1=buf[12]|buf[13]<<8|buf[14]<<16|buf[15]<<24 
			logging.info("CONFIG0=0x%8x" % CONFIG0)
			logging.info("CONFIG1=0x%8x" % CONFIG1)

		#load file to array
		def READ_APROM_BIN_FILE(self, FILENAME):
			try:
				f=open(FILENAME, 'rb')            
				self.AP_CHECKSUM=0
				self.AP_FILE=[]
				while True:
					x=f.read(1)
					if not x:
						break
					temp=struct.unpack('B',x) 
					self.AP_FILE.append(temp[0])
					self.AP_CHECKSUM=self.AP_CHECKSUM+temp[0]
				f.close() 
			except:
				logging.info ("APROM File load error")
				return False
			return True

		def UPDATE_APROM(self):
			self.PacketNumber=self.PacketNumber+2
			AP_ADRESS=0;
			AP_SIZE=len(self.AP_FILE)
			ISP_PACKAGE = [0 for i in range(64)] 
			ISP_PACKAGE[0]=CMD_UPDATE_APROM
			#APROM START ADDRESS 
			ISP_PACKAGE[8]=AP_ADRESS&0xff
			ISP_PACKAGE[9]=AP_ADRESS>>8&0xff
			ISP_PACKAGE[10]=AP_ADRESS>>16&0xff
			ISP_PACKAGE[11]=AP_ADRESS>>24&0xff
			#APROM SIZE
			ISP_PACKAGE[12]=AP_SIZE&0xff  
			ISP_PACKAGE[13]=AP_SIZE>>8&0xff
			ISP_PACKAGE[14]=AP_SIZE>>16&0xff
			ISP_PACKAGE[15]=AP_SIZE>>24&0xff
			ISP_PACKAGE[16:64]=self.AP_FILE[0:48] #first package to copy
			#print '[{}]'.format(', '.join(hex(x) for x in PAP_COMMNAD)) 
			if len(self.USB_TRANSFER(ISP_PACKAGE,self.PacketNumber,0))==0:
				return False
			logging.info ("APROM File erase done")
			for i in range(48,AP_SIZE,56):
				logging.info ("process %d",i/AP_SIZE*100)
				self.PacketNumber=self.PacketNumber+2
				ISP_PACKAGE = [0 for j in range(64)] 
				ISP_PACKAGE[8:64]=self.AP_FILE[i:(i+56)]
				if len(ISP_PACKAGE) < 64:
					for k in range(64-len(ISP_PACKAGE)):
						ISP_PACKAGE.append(0xFF)          
				if (((AP_SIZE-i)<56) or ((AP_SIZE-i)==56)):
					buf=self.USB_TRANSFER(ISP_PACKAGE,self.PacketNumber,0)
					d_checksum=buf[8]|buf[9]<<8
					if(d_checksum==(self.AP_CHECKSUM&0xffff)):
						logging.info ("process 100")
				else:
					self.USB_TRANSFER(ISP_PACKAGE,self.PacketNumber,0)
			logging.info ("process 100")
			logging.info ("finish")
			return True


		def COM_PORT_LIST(self):
			ports = list(serial.tools.list_ports.comports())
			for p in ports:
				print(p.description)
				
		def USB_PORT_LIST(self):
			dev = usb.core.find(find_all=True)            
			# loop through devices, printing vendor and product ids in decimal and hex
			for cfg in dev:
				#print("Device:"+ usb.util.get_string(cfg, 256, cfg.iManufacturer))              
				print('VendorID=' + hex(cfg.idVendor) + ' & ProductID=' + hex(cfg.idProduct))

class Worker(QThread):
		sinOut = pyqtSignal(str)

		def __init__(self,parent=None):
			super(Worker,self).__init__(parent)
			self.working = True
			self.ISP = ISP_COMMAND()
		def __del__(self):
			self.working = False
			self.wait()

		def Thread_UPDATE_APROM(self):
			self.ISP.READ_APROM_BIN_FILE("test.bin")
			#print(self.ISP.AP_CHECKSUM)
			#print(len(self.ISP.AP_FILE))
			self.ISP.PacketNumber=self.ISP.PacketNumber+2
			AP_ADRESS=0;
			AP_SIZE=len(self.ISP.AP_FILE)
			ISP_PACKAGE = [0 for i in range(64)] 
			ISP_PACKAGE[0]=CMD_UPDATE_APROM
			#APROM START ADDRESS 
			ISP_PACKAGE[8]=AP_ADRESS&0xff
			ISP_PACKAGE[9]=AP_ADRESS>>8&0xff
			ISP_PACKAGE[10]=AP_ADRESS>>16&0xff
			ISP_PACKAGE[11]=AP_ADRESS>>24&0xff
			#APROM SIZE
			ISP_PACKAGE[12]=AP_SIZE&0xff  
			ISP_PACKAGE[13]=AP_SIZE>>8&0xff
			ISP_PACKAGE[14]=AP_SIZE>>16&0xff
			ISP_PACKAGE[15]=AP_SIZE>>24&0xff
			ISP_PACKAGE[16:64]=self.ISP.AP_FILE[0:48] #first package to copy
			#print '[{}]'.format(', '.join(hex(x) for x in PAP_COMMNAD))
			if len(self.ISP.USB_TRANSFER(ISP_PACKAGE,self.ISP.PacketNumber,0))==0:
				return False
			logging.info ("APROM File erase done")
			for i in range(48,AP_SIZE,56):
				logging.info ("process %d",i/AP_SIZE*100)
				self.sinOut.emit(str(int(i/AP_SIZE*100)))
				self.ISP.PacketNumber=self.ISP.PacketNumber+2
				ISP_PACKAGE = [0 for j in range(64)] 
				ISP_PACKAGE[8:64]=self.ISP.AP_FILE[i:(i+56)]
				if len(ISP_PACKAGE) < 64:
					for k in range(64-len(ISP_PACKAGE)):
						ISP_PACKAGE.append(0xFF)          
				if (((AP_SIZE-i)<56) or ((AP_SIZE-i)==56)):
					buf=self.ISP.USB_TRANSFER(ISP_PACKAGE,self.ISP.PacketNumber,0)
					#d_checksum=buf[8]|buf[9]<<8
					#print(d_checksum)
					#print(self.ISP.AP_CHECKSUM)
					#if(d_checksum==(self.ISP.AP_CHECKSUM&0xffff)):
					if len(buf)!=0:
					    logging.info ("process 100")
					    self.sinOut.emit("100")
				else:
					self.ISP.USB_TRANSFER(ISP_PACKAGE,self.ISP.PacketNumber,0)
			logging.info ("finish")
			return True

		def run(self):
			if self.ISP.Interface()==0:
				return
			self.ISP.OPEN_USB()
			self.ISP.ISP_CMD_CONNECT()
			self.ISP.ISP_CMD_SYNC_PACKNO()
			self.ISP.ISP_CMD_GET_FWVER()
			self.ISP.ISP_CMD_GET_DEVICEID()
			self.ISP.ISP_CMD_READ_CONFIG()			
			self.Thread_UPDATE_APROM()
			self.ISP.CLOSE_USB()

class MyMainWindow(QMainWindow, Ui_Form):
		def __init__(self, parent=None):     
			super(MyMainWindow, self).__init__(parent) 
			self.setupUi(self) 
			self.progressBar.setValue(0)
			self.thread = Worker()
			self.ISP_TEMP=None
			self.thread.sinOut.connect(self.slotAdd)
			self.pushButton.clicked.connect(self.startISP)
		def slotAdd(self,count):
			if(int(count)<=100):
				self.progressBar.setValue(int(count))
				#time.sleep(0.1)
			if(int(count)==100):
				self.pushButton.setEnabled(True)  
		def startISP(self):
			self.ISP_TEMP = ISP_COMMAND()
			if self.ISP_TEMP.Interface()==0:
				return
			self.pushButton.setEnabled(False)
			self.progressBar.setValue(0)
			self.thread.start()


if __name__=="__main__":
		parser = ArgumentParser()
		parser.add_argument("-USB", help="comport numbmer -USB VID:PID, exsample:-USB 0X0416:0X3F00", dest="USB_ID", default="default")       
		parser.add_argument("-APROM", help="program aprom file, -aprom test.bin", dest="APROM_FILE", default="default") 
		parser.add_argument('-LIST_USB', dest="LIST_USB", action='store_true', default=False, help='LIST all USB port')
		parser.add_argument('-AUTO', dest="AUTO", action='store_true', default=False, help='To do connect, read id, erase, program, aprom')
		parser.add_argument('-FWVERSION', dest="FW_VERSION", action='store_true', default=False, help='To read target chip fw version')
		parser.add_argument('-PID', dest="PID", action='store_true', default=False, help='To read target chip PID')
		parser.add_argument('-R_CONFIG', dest="R_CONFIG", action='store_true', default=False, help='To read target chip config value setting')		
		parser.add_argument('-GUIDEBUG', dest="GUIDEBUG", action='store_true', default=False, help='The GUI print message')
		args = parser.parse_args()
		logging.basicConfig(level=logging.INFO)

		if len(sys.argv)==1:#gui mode
			#close python console
			ct = win32api.GetConsoleTitle()   
			hd = win32gui.FindWindow(0,ct)   
			win32gui.ShowWindow(hd,0)          
			app = QApplication(sys.argv)  
			app_icon = QIcon("IMG/icon.ico")
			app.setWindowIcon(app_icon)
			s = QStyleFactory.create('Fusion') 
			app.setStyle(s) 
			myWin = MyMainWindow()  
			myWin.show()   
			sys.exit(app.exec_()) 

		if args.GUIDEBUG:
			app = QApplication(sys.argv)  
			s = QStyleFactory.create('Fusion') 
			app.setStyle(s) 
			app_icon = QIcon("IMG/icon.ico")
			app.setWindowIcon(app_icon)
			myWin = MyMainWindow()  
			myWin.show()   
			sys.exit(app.exec_()) 
		#command line process
		ISP=ISP_COMMAND()

		if args.LIST_USB:
			ISP.USB_PORT_LIST()
			sys.exit(0)

		if args.USB_ID!="default":       
			s_USB_ID=args.USB_ID.split(":")
			#print(len(s_USB_ID))
			USB_VID=int(s_USB_ID[0],0)
			USB_PID=int(s_USB_ID[1],0)
			if (ISP.Interface(VID_in=USB_VID,PID_in=USB_PID)==False):           
				sys.exit(0)
			ISP.OPEN_USB(VID_in=USB_VID,PID_in=USB_PID);
		else:
			if (ISP.Interface()==False):
				sys.exit(0)
			ISP.OPEN_USB()


		if args.FW_VERSION:
			if ISP.ISP_CMD_CONNECT()!=True:
				sys.exit(0)
			ISP.ISP_CMD_GET_FWVER()

		if args.PID:
			if ISP.ISP_CMD_CONNECT()!=True:
				sys.exit(0)
			ISP.ISP_CMD_GET_DEVICEID();

		if args.R_CONFIG:
			if ISP.ISP_CMD_CONNECT()!=True:
				sys.exit(0)
			ISP.ISP_CMD_READ_CONFIG();

		if args.AUTO:
			if args.APROM_FILE=="default": 
				logging.info("Please add permeter for bin file")
				sys.exit(0)
			if args.APROM_FILE!="default":
				if (ISP.READ_APROM_BIN_FILE(args.APROM_FILE)==True):
					logging.info("file checksum:"+str(hex(ISP.AP_CHECKSUM)))
					logging.info(("file size:"+str(len(ISP.AP_FILE))))
				else:
					logging.info("check file exit")



		if args.AUTO:  
			if ISP.ISP_CMD_CONNECT()!=True:
			    sys.exit(0)
			if ISP.ISP_CMD_SYNC_PACKNO()!=True:
			    sys.exit(0)
			ISP.ISP_CMD_GET_FWVER()
			ISP.ISP_CMD_GET_DEVICEID();
			ISP.ISP_CMD_READ_CONFIG();
			ISP.UPDATE_APROM()
