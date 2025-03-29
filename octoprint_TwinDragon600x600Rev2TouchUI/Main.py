#!/usr/bin/python

"""
*************************************************************************
 *
 * Fracktal Works
 * __________________
 * Authors: Vijay Varada/Nishant Bilurkar
 * Created: May 2023
 *
 * Licence: AGPLv3
*************************************************************************
"""
Development = False   # set to True if running on any system other than RaspberryPi

import mainGUI
import keyboard
import dialog
import styles
import glob

from PyQt5 import QtCore, QtGui, QtWidgets
import time
import sys
import subprocess
from octoprintAPI import octoprintAPI
from hurry.filesize.filesize import size
from datetime import datetime
# from functools import partial
import qrcode
# pip install websocket-client
import websocket #https://pypi.org/project/websocket-client/
import json
import random
import uuid
import os
# import serial
import io
import requests
import re
from collections import OrderedDict
import base64
import threading


#if not Development:
    #import RPi.GPIO as GPIO
    #GPIO.setmode(GPIO.BCM)  # Use the board numbering scheme
    #GPIO.setwarnings(False)  # Disable GPIO warnings H

# TODO:
'''
# Error Handaling
# Logging UI errors to Octoprint Log
# Configuration File Seperation
# Add new Klipper Configuraion

'''

# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# ++++++++++++++++++++++++Logging+++++++++++++++++++++++++++++++++++++++++++++++
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

from logger import setup_logger, delete_old_logs

# Setup logger
logger = setup_logger()

# Delete old logs
delete_old_logs()

# Now you can use logger to log messages
logger.info("TouchUI started")



# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# ++++++++++++++++++++++++Global variables++++++++++++++++++++++++++++++++++++++
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

ip = '0.0.0.0:5000'
apiKey = 'B508534ED20348F090B4D0AD637D3660'

file_name = ''
filaments = [
                ("PLA", 190),
                ("ABS", 220),
                ("PETG", 220),
                ("PVA", 210),
                ("TPU", 230),
                ("Nylon", 220),
                ("PolyCarbonate", 240),
                ("HIPS", 220),
                ("WoodFill", 220),
                ("CopperFill", 200),
                ("Breakaway", 220)
]

filaments = OrderedDict(filaments)

#values before 2020 changes
calibrationPosition = {'X1': 63, 'Y1': 67, #110, 18
                       'X2': 542, 'Y2': 67, #510, 18
                       'X3': 303, 'Y3': 567, #310, 308
                       'X4': 303, 'Y4': 20
                       }

tool0PurgePosition = {'X': -27, 'Y': -112}
tool1PurgePosition = {'X': 648, 'Y': -112}

ptfeTubeLength = 2400 #2400 for 600x600, 1500 for 600x300 keep as multiples of 300 only

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s


def run_async(func):
    """
    Function decorater to make methods run in a thread
    """
    from threading import Thread
    from functools import wraps

    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target=func, args=args, kwargs=kwargs)
        func_hl.start()
        return func_hl

    return async_func


def getIP(interface):
    try:
        scan_result = \
            (subprocess.Popen("ifconfig | grep " + interface + " -A 1", stdout=subprocess.PIPE, shell=True).communicate()[0]).decode("utf-8")
        # Processing STDOUT into a dictionary that later will be converted to a json file later
        rInetAddr = r"inet\s*([\d.]+)"
        rInet6Addr = r"inet6"
        mt6Ip = re.search(rInet6Addr, scan_result)
        mtIp = re.search(rInetAddr, scan_result)
        if not mt6Ip and mtIp and len(mtIp.groups()) == 1:
            return str(mtIp.group(1))
    except Exception as e:
        logger.error("Error in getIP: {}".format(e))
        return None

def getMac(interface):
    logger.info("Getting MAC for interface: {}".format(interface))
    try:
        mac = subprocess.Popen(" cat /sys/class/net/" + interface + "/address",
                               stdout=subprocess.PIPE, shell=True).communicate()[0].rstrip()
        if not mac:
            return "Not found"
        return mac.upper()
    except Exception as e:
        logger.error("Error in getMac: {}".format(e))
        return "Error"


def getWifiAp():
    logger.info("Getting Wifi AP")
    try:
        ap = subprocess.Popen("iwgetid -r",
                              stdout=subprocess.PIPE, shell=True).communicate()[0].rstrip()
        if not ap:
            return "Not connected"
        return ap.decode("utf-8")
    except Exception as e:
        logger.error("Error in getWifiAp: {}".format(e))
        return "Error"


def getHostname():
    logger.info("Getting Hostname")
    try:
        hostname = subprocess.Popen("cat /etc/hostname", stdout=subprocess.PIPE, shell=True).communicate()[0].rstrip()
        if not hostname:
            return "Not connected"
        return hostname.decode("utf-8")  + ".local"
    except Exception as e:
        logger.error("Error in getHostname: {}".format(e))
        return "Error"

#class BuzzerFeedback(object):
    #def __init__(self, buzzerPin):
        #if not Development:
            #GPIO.cleanup()
            #self.buzzerPin = buzzerPin
            #GPIO.setup(self.buzzerPin, GPIO.OUT)
            #GPIO.output(self.buzzerPin, GPIO.LOW)
        #pass

    #@run_async
    #def buzz(self):
        #if not Development:
            #GPIO.output(self.buzzerPin, (GPIO.HIGH))
            #time.sleep(0.005)
            #GPIO.output(self.buzzerPin, GPIO.LOW)
        #pass

#buzzer = BuzzerFeedback(12)



'''
To get the buzzer to beep on button press
'''

OriginalPushButton = QtWidgets.QPushButton
OriginalToolButton = QtWidgets.QToolButton

class QPushButtonFeedback(QtWidgets.QPushButton):
    def mousePressEvent(self, QMouseEvent):
        #buzzer.buzz()
        OriginalPushButton.mousePressEvent(self, QMouseEvent)


class QToolButtonFeedback(QtWidgets.QToolButton):
    def mousePressEvent(self, QMouseEvent):
        #buzzer.buzz()
        OriginalToolButton.mousePressEvent(self, QMouseEvent)


QtWidgets.QToolButton = QToolButtonFeedback
QtWidgets.QPushButton = QPushButtonFeedback


class Image(qrcode.image.base.BaseImage):
    def __init__(self, border, width, box_size):
        self.border = border
        self.width = width
        self.box_size = box_size
        _size = (width + border * 2) * box_size
        self._image = QtGui.QImage(
            _size, _size, QtGui.QImage.Format_RGB16)
        self._image.fill(QtCore.Qt.white)

    def pixmap(self):
        return QtGui.QPixmap.fromImage(self._image)

    def drawrect(self, row, col):
        painter = QtGui.QPainter(self._image)
        painter.fillRect(
            (col + self.border) * self.box_size,
            (row + self.border) * self.box_size,
            self.box_size, self.box_size,
            QtCore.Qt.black)

    def save(self, stream, kind=None):
        pass

class ClickableLineEdit(QtWidgets.QLineEdit):
    clicked_signal = QtCore.pyqtSignal()
    def __init__(self, parent):
        QtWidgets.QLineEdit.__init__(self, parent)
    def mousePressEvent(self, QMouseEvent):
        #buzzer.buzz()
        self.clicked_signal.emit()


class MainUiClass(QtWidgets.QMainWindow, mainGUI.Ui_MainWindow):
    """
    Main GUI Workhorse, all slots and events defined within
    The main implementation class that inherits methods, variables etc from mainGUI_pro_dual_abl.py and QMainWindow
    """
    def __init__(self):
        """
        This method gets called when an object of type MainUIClass is defined
        """
        super(MainUiClass, self).__init__()
        logger.info("MainUiClass.__init__ started")
        try:
            self.setupUi(self)
            self.stackedWidget.setCurrentWidget(self.loadingPage)
            self.setStep(10)
            self.keyboardWindow = None
            self.changeFilamentHeatingFlag = False
            self.setHomeOffsetBool = False
            self.currentImage = None
            self.currentFile = None
            self.sanityCheck = ThreadSanityCheck(virtual=False)
            self.sanityCheck.start()
            self.sanityCheck.loaded_signal.connect(self.proceed)
            self.sanityCheck.startup_error_signal.connect(self.handleStartupError)
            self.setNewToolZOffsetFromCurrentZBool = False
            self.setActiveExtruder(0)
            self.loadFlag = None
            self.dialogShown = False

            self.dialog_doorlock = None
            self.dialog_filamentsensor = None

            for spinbox in self.findChildren(QtWidgets.QSpinBox):
                lineEdit = spinbox.lineEdit()
                lineEdit.setReadOnly(True)
                lineEdit.setDisabled(True)
                p = lineEdit.palette()
                p.setColor(QtGui.QPalette.Highlight, QtGui.QColor(40, 40, 40))
                lineEdit.setPalette(p)


        except Exception as e:
            logger.error("Error in MainUiClass.__init__: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.__init__: {}".format(e), overlay=True)
    def setupUi(self, MainWindow):
        """
        This method sets up the UI, all the widgets, layouts etc are defined here
        """
        logger.info("MainUiClass.setupUi started")
        try:
            super(MainUiClass, self).setupUi(MainWindow)
            font = QtGui.QFont()
            font.setFamily(_fromUtf8("Gotham"))
            font.setPointSize(15)

            self.wifiPasswordLineEdit = ClickableLineEdit(self.wifiSettingsPage)
            self.wifiPasswordLineEdit.setGeometry(QtCore.QRect(300, 170, 400, 60))
            self.wifiPasswordLineEdit.setFont(font)
            self.wifiPasswordLineEdit.setStyleSheet(styles.textedit)
            self.wifiPasswordLineEdit.setObjectName(_fromUtf8("wifiPasswordLineEdit"))

            font.setPointSize(11)
            self.staticIPLineEdit = ClickableLineEdit(self.ethStaticSettings)
            self.staticIPLineEdit.setGeometry(QtCore.QRect(200, 15, 450, 40))
            self.staticIPLineEdit.setFont(font)
            self.staticIPLineEdit.setStyleSheet(styles.textedit)
            self.staticIPLineEdit.setObjectName(_fromUtf8("staticIPLineEdit"))

            self.staticIPGatewayLineEdit = ClickableLineEdit(self.ethStaticSettings)
            self.staticIPGatewayLineEdit.setGeometry(QtCore.QRect(200, 85, 450, 40))
            self.staticIPGatewayLineEdit.setFont(font)
            self.staticIPGatewayLineEdit.setStyleSheet(styles.textedit)
            self.staticIPGatewayLineEdit.setObjectName(_fromUtf8("staticIPGatewayLineEdit"))

            self.staticIPNameServerLineEdit = ClickableLineEdit(self.ethStaticSettings)
            self.staticIPNameServerLineEdit.setGeometry(QtCore.QRect(200, 155, 450, 40))
            self.staticIPNameServerLineEdit.setFont(font)
            self.staticIPNameServerLineEdit.setStyleSheet(styles.textedit)
            self.staticIPNameServerLineEdit.setObjectName(_fromUtf8("staticIPNameServerLineEdit"))

            self.menuCartButton.setDisabled(True)
            self.testPrintsButton.setDisabled(True)

            self.movie = QtGui.QMovie("templates/img/loading-90.gif")
            self.loadingGif.setMovie(self.movie)
            self.movie.start()
        except Exception as e:
            logger.error("Error in MainUiClass.setupUi: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.setupUi: {}".format(e), overlay=True)




    def safeProceed(self):
        """
        When Octoprint server cannot connect for whatever reason, still show the home screen to conduct diagnostics
        """
        logger.info("MainUiClass.safeProceed started")
        try:
            self.movie.stop()
            if not Development:
                self.stackedWidget.setCurrentWidget(self.homePage)
                self.setIPStatus()
            else:
                self.stackedWidget.setCurrentWidget(self.homePage)

            # Text Input events
            self.wifiPasswordLineEdit.clicked_signal.connect(lambda: self.startKeyboard(self.wifiPasswordLineEdit.setText))
            self.staticIPLineEdit.clicked_signal.connect(lambda: self.staticIPShowKeyboard(self.staticIPLineEdit))
            self.staticIPGatewayLineEdit.clicked_signal.connect(lambda: self.staticIPShowKeyboard(self.staticIPGatewayLineEdit))
            self.staticIPNameServerLineEdit.clicked_signal.connect(lambda: self.staticIPShowKeyboard(self.staticIPNameServerLineEdit))

            # Button Events:

            # Home Screen:
            self.stopButton.setDisabled(True)
            # self.menuButton.pressed.connect(self.keyboardButton)
            self.menuButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.MenuPage))
            self.controlButton.setDisabled(True)
            self.playPauseButton.setDisabled(True)

            # MenuScreen
            self.menuBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.homePage))
            self.menuControlButton.setDisabled(True)
            self.menuPrintButton.setDisabled(True)
            self.menuCalibrateButton.setDisabled(True)
            self.menuSettingsButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))


            # Settings Page
            self.networkSettingsButton.pressed.connect(
                lambda: self.stackedWidget.setCurrentWidget(self.networkSettingsPage))
            self.displaySettingsButton.pressed.connect(
                lambda: self.stackedWidget.setCurrentWidget(self.displaySettingsPage))
            self.settingsBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.MenuPage))
            self.pairPhoneButton.pressed.connect(self.pairPhoneApp)
            self.OTAButton.setDisabled(True)
            self.versionButton.setDisabled(True)

            self.restartButton.pressed.connect(self.askAndReboot)
            self.restoreFactoryDefaultsButton.pressed.connect(self.restoreFactoryDefaults)
            self.restorePrintSettingsButton.pressed.connect(self.restorePrintDefaults)

            # Network settings page
            self.networkInfoButton.pressed.connect(self.networkInfo)
            self.configureWifiButton.pressed.connect(self.wifiSettings)
            self.configureStaticIPButton.pressed.connect(self.staticIPSettings)
            self.networkSettingsBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))

            # Network Info Page
            self.networkInfoBackButton.pressed.connect(
                lambda: self.stackedWidget.setCurrentWidget(self.networkSettingsPage))

            # WifiSetings page
            self.wifiSettingsSSIDKeyboardButton.pressed.connect(
                lambda: self.startKeyboard(self.wifiSettingsComboBox.addItem))
            self.wifiSettingsCancelButton.pressed.connect(
                lambda: self.stackedWidget.setCurrentWidget(self.networkSettingsPage))
            self.wifiSettingsDoneButton.pressed.connect(self.acceptWifiSettings)

            # Static IP settings page
            self.staticIPKeyboardButton.pressed.connect(lambda: self.staticIPShowKeyboard(self.staticIPLineEdit))
            self.staticIPGatewayKeyboardButton.pressed.connect(
                lambda: self.staticIPShowKeyboard(self.staticIPGatewayLineEdit))
            self.staticIPNameServerKeyboardButton.pressed.connect(
                lambda: self.staticIPShowKeyboard(self.staticIPNameServerLineEdit))
            self.staticIPSettingsDoneButton.pressed.connect(self.staticIPSaveStaticNetworkInfo)
            self.staticIPSettingsCancelButton.pressed.connect(
                lambda: self.stackedWidget.setCurrentWidget(self.networkSettingsPage))
            self.deleteStaticIPSettingsButton.pressed.connect(self.deleteStaticIPSettings)

            # # Display settings
            # self.rotateDisplay.pressed.connect(self.showRotateDisplaySettingsPage)
            # self.calibrateTouch.pressed.connect(self.touchCalibration)
            self.displaySettingsBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))
            #
            # # Rotate Display Settings
            # self.rotateDisplaySettingsDoneButton.pressed.connect(self.saveRotateDisplaySettings)
            # self.rotateDisplaySettingsCancelButton.pressed.connect(
            #     lambda: self.stackedWidget.setCurrentWidget(self.displaySettingsPage))

            # QR Code
            self.QRCodeBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))

            # SoftwareUpdatePage
            self.softwareUpdateBackButton.setDisabled(True)
            self.performUpdateButton.setDisabled(True)

            # # Firmware update page
            # self.firmwareUpdateBackButton.setDisabled(True)

            # Filament sensor toggle
            self.toggleFilamentSensorButton.setDisabled(True)
        except Exception as e:
            logger.error("Error in MainUiClass.safeProceed: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.safeProceed: {}".format(e), overlay=True)


    def handleStartupError(self):
        """
        Error Handler when Octoprint gives up
        """
        logger.info("MainUiClass.handleStartupError started")
        try:
            if dialog.WarningYesNo(self, "Server Error, Restore failsafe settings?", overlay=True):
                logger.info("Restoring Failsafe Settings")
                os.system('sudo rm -rf /home/pi/.octoprint/users.yaml')
                os.system('sudo rm -rf /home/pi/.octoprint/config.yaml')
                os.system('sudo cp -f config/users.yaml /home/pi/.octoprint/users.yaml')
                os.system('sudo cp -f config/config.yaml /home/pi/.octoprint/config.yaml')
                subprocess.call(["sudo", "systemctl", "restart", "octoprint"])
                self.sanityCheck.start()
            else:
                logger.info("User chose not to restore failsafe settings, going to safeProcees()")
                self.safeProceed()
        except Exception as e:
            logger.error("Error in MainUiClass.handleStartupError: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.handleStartupError: {}".format(e), overlay=True)


    def proceed(self):
        """
        Startes websocket, as well as initialises button actions and callbacks. THis is done in such a manner so that the callbacks that depend on websockets
        load only after the socket is available which in turn is dependent on the server being available which is checked in the sanity check thread
        """
        logger.info("MainUiClass.proceed started")
        try:
            self.QtSocket = QtWebsocket()
            self.QtSocket.start()
            self.setActions()
            self.movie.stop()
            if not Development:
                self.stackedWidget.setCurrentWidget(self.homePage)
                self.setIPStatus()
            else:
                self.stackedWidget.setCurrentWidget(self.homePage)
            self.isFilamentSensorInstalled()
            self.onServerConnected()
            self.checkKlipperPrinterCFG()
        except Exception as e:
            logger.error("Error in MainUiClass.proceed: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.proceed: {}".format(e), overlay=True)
    def setActions(self):

        """
        defines all the Slots and Button events.
        """
        logger.info("MainUiClass.setActions started")
        try:
            #--Dual Caliberation Addition--
            self.QtSocket.set_z_tool_offset_signal.connect(self.setZToolOffset)
            self.QtSocket.z_probe_offset_signal.connect(self.updateEEPROMProbeOffset)
            self.QtSocket.temperatures_signal.connect(self.updateTemperature)
            self.QtSocket.status_signal.connect(self.updateStatus)
            self.QtSocket.print_status_signal.connect(self.updatePrintStatus)
            self.QtSocket.update_started_signal.connect(self.softwareUpdateProgress)
            self.QtSocket.update_log_signal.connect(self.softwareUpdateProgressLog)
            self.QtSocket.update_log_result_signal.connect(self.softwareUpdateResult)
            self.QtSocket.update_failed_signal.connect(self.updateFailed)
            self.QtSocket.connected_signal.connect(self.onServerConnected)
            self.QtSocket.filament_sensor_triggered_signal.connect(self.filamentSensorHandler)
            # self.QtSocket.firmware_updater_signal.connect(self.firmwareUpdateHandler) # Not used for TwinDragon, only for Update Marlin
            #self.QtSocket.z_home_offset_signal.connect(self.getZHomeOffset)  Deprecated, uses probe offset to set initial height instead
            self.QtSocket.active_extruder_signal.connect(self.setActiveExtruder)
            self.QtSocket.z_probing_failed_signal.connect(self.showProbingFailed)
            self.QtSocket.tool_offset_signal.connect(self.getToolOffset)
            self.QtSocket.printer_error_signal.connect(self.showPrinterError)
    
            # Text Input events
            self.wifiPasswordLineEdit.clicked_signal.connect(lambda: self.startKeyboard(self.wifiPasswordLineEdit.setText))
            self.staticIPLineEdit.clicked_signal.connect(lambda: self.staticIPShowKeyboard(self.staticIPLineEdit))
            self.staticIPGatewayLineEdit.clicked_signal.connect(lambda: self.staticIPShowKeyboard(self.staticIPGatewayLineEdit))
            self.staticIPNameServerLineEdit.clicked_signal.connect(lambda: self.staticIPShowKeyboard(self.staticIPNameServerLineEdit))
    
            # Button Events:
    
            # Home Screen:
            self.stopButton.pressed.connect(self.stopActionMessageBox)
            # self.menuButton.pressed.connect(self.keyboardButton)
            self.menuButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.MenuPage))
            self.controlButton.pressed.connect(self.control)
            self.playPauseButton.clicked.connect(self.playPauseAction)
            self.doorLockButton.clicked.connect(self.doorLock)
    
            # MenuScreen
            self.menuBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.homePage))
            self.menuControlButton.pressed.connect(self.control)
            self.menuPrintButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.printLocationPage))
            self.menuCalibrateButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.calibratePage))
            self.menuSettingsButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))
    
            # Calibrate Page
            self.calibrateBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.MenuPage))
            self.nozzleOffsetButton.pressed.connect(self.requestEEPROMProbeOffset)
            # the -ve sign is such that its converted to home offset and not just distance between nozzle and bed
            self.nozzleOffsetSetButton.pressed.connect(
                lambda: self.setZProbeOffset(self.nozzleOffsetDoubleSpinBox.value()))
            self.nozzleOffsetBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.calibratePage))
    
            # --Dual Caliberation Addition--
            self.moveZMT1CaliberateButton.pressed.connect(lambda: octopiclient.jog(z=-0.025))
            self.moveZPT1CaliberateButton.pressed.connect(lambda: octopiclient.jog(z=0.025))
    
            self.calibrationWizardButton.clicked.connect(self.quickStep1)
            self.quickStep1NextButton.clicked.connect(self.quickStep2)
            self.quickStep2NextButton.clicked.connect(self.quickStep3)
            self.quickStep3NextButton.clicked.connect(self.quickStep4)
            self.quickStep4NextButton.clicked.connect(self.nozzleHeightStep1)
            self.nozzleHeightStep1NextButton.clicked.connect(self.nozzleHeightStep1)
            self.quickStep1CancelButton.pressed.connect(self.cancelStep)
            self.quickStep2CancelButton.pressed.connect(self.cancelStep)
            self.quickStep3CancelButton.pressed.connect(self.cancelStep)
            self.quickStep4CancelButton.pressed.connect(self.cancelStep)
            self.nozzleHeightStep1CancelButton.pressed.connect(self.cancelStep)
    
            # --IDEX Caliberation Addition--
    
            self.idexCalibrationWizardButton.clicked.connect(self.idexConfigStep1)
            self.idexConfigStep1NextButton.clicked.connect(self.idexConfigStep2)
            self.idexConfigStep2NextButton.clicked.connect(self.idexConfigStep3)
            self.idexConfigStep3NextButton.clicked.connect(self.idexConfigStep4)
            self.idexConfigStep4NextButton.clicked.connect(self.idexConfigStep5)
            self.idexConfigStep5NextButton.clicked.connect(self.idexDoneStep)
            self.idexConfigStep1CancelButton.pressed.connect(self.idexCancelStep)
            self.idexConfigStep2CancelButton.pressed.connect(self.idexCancelStep)
            self.idexConfigStep3CancelButton.pressed.connect(self.idexCancelStep)
            self.idexConfigStep4CancelButton.pressed.connect(self.idexCancelStep)
            self.idexConfigStep5CancelButton.pressed.connect(self.idexCancelStep)
            self.moveZMIdexButton.pressed.connect(lambda: octopiclient.jog(z=-0.1))
            self.moveZPIdexButton.pressed.connect(lambda: octopiclient.jog(z=0.1))
            
            self.toolOffsetXSetButton.pressed.connect(self.setToolOffsetX)
            self.toolOffsetYSetButton.pressed.connect(self.setToolOffsetY)
            self.toolOffsetZSetButton.pressed.connect(self.setToolOffsetZ)
            self.toolOffsetXYBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.calibratePage))
            self.toolOffsetZBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.calibratePage))
            self.toolOffsetXYButton.pressed.connect(self.updateToolOffsetXY)
            self.toolOffsetZButton.pressed.connect(self.updateToolOffsetZ)
    
            self.testPrintsButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.testPrintsPage1_6))
            self.testPrintsNextButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.testPrintsPage2_6))
            self.testPrintsBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.calibratePage))
            self.testPrintsCancelButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.calibratePage))
            self.dualCaliberationPrintButton.pressed.connect(
                lambda: self.testPrint(str(self.testPrintsTool0SizeComboBox.currentText()).replace('.', ''),
                                       str(self.testPrintsTool1SizeComboBox.currentText()).replace('.', ''), 'dualCalibration'))
            self.bedLevelPrintButton.pressed.connect(
                lambda: self.testPrint(str(self.testPrintsTool0SizeComboBox.currentText()).replace('.', ''),
                                       str(self.testPrintsTool1SizeComboBox.currentText()).replace('.', ''), 'bedLevel'))
            self.movementTestPrintButton.pressed.connect(
                lambda: self.testPrint(str(self.testPrintsTool0SizeComboBox.currentText()).replace('.', ''),
                                       str(self.testPrintsTool1SizeComboBox.currentText()).replace('.', ''), 'movementTest'))
            self.singleNozzlePrintButton.pressed.connect(
                lambda: self.testPrint(str(self.testPrintsTool0SizeComboBox.currentText()).replace('.', ''),
                                       str(self.testPrintsTool1SizeComboBox.currentText()).replace('.', ''), 'dualTest'))
            self.dualNozzlePrintButton.pressed.connect(
                lambda: self.testPrint(str(self.testPrintsTool0SizeComboBox.currentText()).replace('.', ''),
                                       str(self.testPrintsTool1SizeComboBox.currentText()).replace('.', ''), 'singleTest'))
            #~ Input Shaping~#
            self.inputShaperCalibrateButton.pressed.connect(self.inputShaperCalibrate)

            # PrintLocationScreen
            self.printLocationScreenBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.MenuPage))
            self.fromLocalButton.pressed.connect(self.fileListLocal)
            self.fromUsbButton.pressed.connect(self.fileListUSB)
    
            # fileListLocalScreen
            self.localStorageBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.printLocationPage))
            self.localStorageScrollUp.pressed.connect(
                lambda: self.fileListWidget.setCurrentRow(self.fileListWidget.currentRow() - 1))
            self.localStorageScrollDown.pressed.connect(
                lambda: self.fileListWidget.setCurrentRow(self.fileListWidget.currentRow() + 1))
            self.localStorageSelectButton.pressed.connect(self.printSelectedLocal)
            self.localStorageDeleteButton.pressed.connect(self.deleteItem)
    
            # selectedFile Local Screen
            self.fileSelectedBackButton.pressed.connect(self.fileListLocal)
            self.fileSelectedPrintButton.pressed.connect(self.printFile)
    
            # filelistUSBPage
            self.USBStorageBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.printLocationPage))
            self.USBStorageScrollUp.pressed.connect(
                lambda: self.fileListWidgetUSB.setCurrentRow(self.fileListWidgetUSB.currentRow() - 1))
            self.USBStorageScrollDown.pressed.connect(
                lambda: self.fileListWidgetUSB.setCurrentRow(self.fileListWidgetUSB.currentRow() + 1))
            self.USBStorageSelectButton.pressed.connect(self.printSelectedUSB)
            self.USBStorageSaveButton.pressed.connect(lambda: self.transferToLocal(prnt=False))
    
            # selectedFile USB Screen
            self.fileSelectedUSBBackButton.pressed.connect(self.fileListUSB)
            self.fileSelectedUSBTransferButton.pressed.connect(lambda: self.transferToLocal(prnt=False))
            self.fileSelectedUSBPrintButton.pressed.connect(lambda: self.transferToLocal(prnt=True))
    
            # ControlScreen
            self.moveYPButton.pressed.connect(lambda: octopiclient.jog(y=self.step, speed=2000))
            self.moveYMButton.pressed.connect(lambda: octopiclient.jog(y=-self.step, speed=2000))
            self.moveXMButton.pressed.connect(lambda: octopiclient.jog(x=-self.step, speed=2000))
            self.moveXPButton.pressed.connect(lambda: octopiclient.jog(x=self.step, speed=2000))
            self.moveZPButton.pressed.connect(lambda: octopiclient.jog(z=self.step, speed=2000))
            self.moveZMButton.pressed.connect(lambda: octopiclient.jog(z=-self.step, speed=2000))
            self.extruderButton.pressed.connect(lambda: octopiclient.extrude(self.step))
            self.retractButton.pressed.connect(lambda: octopiclient.extrude(-self.step))
            self.motorOffButton.pressed.connect(lambda: octopiclient.gcode(command='M18'))
            self.fanOnButton.pressed.connect(lambda: octopiclient.gcode(command='M106 S255'))
            self.fanOffButton.pressed.connect(lambda: octopiclient.gcode(command='M107'))
            self.cooldownButton.pressed.connect(self.coolDownAction)
            self.step100Button.pressed.connect(lambda: self.setStep(100))
            self.step1Button.pressed.connect(lambda: self.setStep(1))
            self.step10Button.pressed.connect(lambda: self.setStep(10))
            self.homeXYButton.pressed.connect(lambda: octopiclient.home(['x', 'y']))
            self.homeZButton.pressed.connect(lambda: octopiclient.home(['z']))
            self.toolToggleTemperatureButton.clicked.connect(self.selectToolTemperature)
            self.toolToggleMotionButton.clicked.connect(self.selectToolMotion)
            self.controlBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.homePage))
            self.setToolTempButton.pressed.connect(self.setToolTemp)
            self.tool180PreheatButton.pressed.connect(lambda: octopiclient.gcode(command='M104 T1 S180') if self.toolToggleTemperatureButton.isChecked() else octopiclient.gcode(command='M104 T0 S180'))
            self.tool250PreheatButton.pressed.connect(lambda: octopiclient.gcode(command='M104 T1 S250') if self.toolToggleTemperatureButton.isChecked() else octopiclient.gcode(command='M104 T0 S250'))
            self.tool180PreheatButton.pressed.connect(lambda: self.preheatToolTemp(180))
            self.tool250PreheatButton.pressed.connect(lambda: self.preheatToolTemp(250))
            self.setBedTempButton.pressed.connect(lambda: octopiclient.setBedTemperature(self.bedTempSpinBox.value()))
            self.bed60PreheatButton.pressed.connect(lambda: self.preheatBedTemp(60))
            self.bed100PreheatButton.pressed.connect(lambda: self.preheatBedTemp(100))
            #self.chamber40PreheatButton.pressed.connect(lambda: self.preheatChamberTemp(40))
            #self.chamber70PreheatButton.pressed.connect(lambda: self.preheatChamberTemp(70))
            #self.setChamberTempButton.pressed.connect(lambda: octopiclient.gcode(command='M141 S{}'.format(self.chamberTempSpinBox.value())))
            self.setFlowRateButton.pressed.connect(lambda: octopiclient.flowrate(self.flowRateSpinBox.value()))
            self.setFeedRateButton.pressed.connect(lambda: octopiclient.feedrate(self.feedRateSpinBox.value()))
    
            self.moveZPBabyStep.pressed.connect(lambda: octopiclient.gcode(command='M290 Z0.025'))
            self.moveZMBabyStep.pressed.connect(lambda: octopiclient.gcode(command='M290 Z-0.025'))
    
            # ChangeFilament rutien
            self.changeFilamentButton.pressed.connect(self.changeFilament)
            self.toolToggleChangeFilamentButton.clicked.connect(self.selectToolChangeFilament)
            self.changeFilamentBackButton.pressed.connect(self.control)
            self.changeFilamentBackButton2.pressed.connect(self.changeFilamentCancel)
            self.changeFilamentBackButton3.pressed.connect(self.changeFilamentCancel)
            self.changeFilamentUnloadButton.pressed.connect(self.unloadFilament)
            self.changeFilamentLoadButton.pressed.connect(self.loadFilament)
            self.loadedTillExtruderButton.pressed.connect(self.changeFilamentExtrudePageFunction)
            self.loadDoneButton.pressed.connect(self.control)
            self.unloadDoneButton.pressed.connect(self.changeFilament)
            # self.retractFilamentButton.pressed.connect(lambda: octopiclient.extrude(-20))
            # self.ExtrudeButton.pressed.connect(lambda: octopiclient.extrude(20))
    
            # Settings Page
            self.settingsBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.MenuPage))
            self.networkSettingsButton.pressed.connect(
                lambda: self.stackedWidget.setCurrentWidget(self.networkSettingsPage))
            self.displaySettingsButton.pressed.connect(
                lambda: self.stackedWidget.setCurrentWidget(self.displaySettingsPage))
            self.pairPhoneButton.pressed.connect(self.pairPhoneApp)
            self.OTAButton.pressed.connect(self.softwareUpdate)
            self.versionButton.pressed.connect(self.displayVersionInfo)
            self.restartButton.pressed.connect(self.askAndReboot)
            self.restoreFactoryDefaultsButton.pressed.connect(self.restoreFactoryDefaults)
            self.restorePrintSettingsButton.pressed.connect(self.restorePrintDefaults)
    
            # Network settings page
            self.networkInfoButton.pressed.connect(self.networkInfo)
            self.configureWifiButton.pressed.connect(self.wifiSettings)
            self.configureStaticIPButton.pressed.connect(self.staticIPSettings)
            self.networkSettingsBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))
    
            # Network Info Page
            self.networkInfoBackButton.pressed.connect(
                lambda: self.stackedWidget.setCurrentWidget(self.networkSettingsPage))
    
            # WifiSetings page
            self.wifiSettingsSSIDKeyboardButton.pressed.connect(
                lambda: self.startKeyboard(self.wifiSettingsComboBox.addItem))
            self.wifiSettingsCancelButton.pressed.connect(
                lambda: self.stackedWidget.setCurrentWidget(self.networkSettingsPage))
            self.wifiSettingsDoneButton.pressed.connect(self.acceptWifiSettings)
    
            # Static IP settings page
            self.staticIPKeyboardButton.pressed.connect(lambda: self.staticIPShowKeyboard(self.staticIPLineEdit))                                                                            
            self.staticIPGatewayKeyboardButton.pressed.connect(lambda: self.staticIPShowKeyboard(self.staticIPGatewayLineEdit))
            self.staticIPNameServerKeyboardButton.pressed.connect(
                lambda: self.staticIPShowKeyboard(self.staticIPNameServerLineEdit))
            self.staticIPSettingsDoneButton.pressed.connect(self.staticIPSaveStaticNetworkInfo)
            self.staticIPSettingsCancelButton.pressed.connect(
                lambda: self.stackedWidget.setCurrentWidget(self.networkSettingsPage))
            self.deleteStaticIPSettingsButton.pressed.connect(self.deleteStaticIPSettings)
    
            # # Display settings
            # self.rotateDisplay.pressed.connect(self.showRotateDisplaySettingsPage)
            # self.calibrateTouch.pressed.connect(self.touchCalibration)
            self.displaySettingsBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))
            #
            # # Rotate Display Settings
            # self.rotateDisplaySettingsDoneButton.pressed.connect(self.saveRotateDisplaySettings)
            # self.rotateDisplaySettingsCancelButton.pressed.connect(
            #     lambda: self.stackedWidget.setCurrentWidget(self.displaySettingsPage))
    
            # QR Code
            self.QRCodeBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))
    
            # SoftwareUpdatePage
            self.softwareUpdateBackButton.pressed.connect(lambda: self.stackedWidget.setCurrentWidget(self.settingsPage))
            self.performUpdateButton.pressed.connect(lambda: octopiclient.performSoftwareUpdate())
    
            # # Firmware update page
            # self.firmwareUpdateBackButton.pressed.connect(self.firmwareUpdateBack)
    
            # Filament sensor toggle
            self.toggleFilamentSensorButton.clicked.connect(self.toggleFilamentSensor)
        except Exception as e:
            logger.error("Error in MainUiClass.setActions: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.setActions: {}".format(e), overlay=True)

    ''' +++++++++++++++++++++++++Print Restore+++++++++++++++++++++++++++++++++++ '''

    def printRestoreMessageBox(self, file):
        """
        Displays a message box alerting the user of a filament error
        """
        logger.info("MainUiClass.printRestoreMessageBox started")
        try:
            if dialog.WarningYesNo(self, file + " Did not finish, would you like to restore?"):
                response = octopiclient.restore(restore=True)
                if response["status"] == "Successfully Restored":
                    dialog.WarningOk(self, response["status"])
                else:
                    dialog.WarningOk(self, response["status"])
        except Exception as e:
            logger.error("Error in MainUiClass.printRestoreMessageBox: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.printRestoreMessageBox: {}".format(e), overlay=True)


    def onServerConnected(self):
        """
        When the server is connected, check for filament sensor and previous print failure to complere
        """
        logger.info("MainUiClass.onServerConnected started")
        try:
            octopiclient.gcode(command='status') #get klipper status. hanle in
            self.isFilamentSensorInstalled()
            try:
                response = octopiclient.isFailureDetected()
                if response["canRestore"] is True:
                    self.printRestoreMessageBox(response["file"])
                else:
                    # self.firmwareUpdateCheck()
                    pass #Firmware update Functionality not needed for Twin Dragon, need to modify this for updating cfg files
            except:
                pass
        except Exception as e:
            logger.error("Error in MainUiClass.onServerConnected: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.onServerConnected: {}".format(e), overlay=True)

    ''' +++++++++++++++++++++++++Filament Sensor++++++++++++++++++++++++++++++++++++++ '''

    def isFilamentSensorInstalled(self):
        """
        Checks if the filament sensor is installed
        """
        logger.info("MainUiClass.isFilamentSensorInstalled started")
        try:
            success = False
            try:
                headers = {'X-Api-Key': apiKey}
                req = requests.get('http://{}/plugin/Julia2018FilamentSensor/status'.format(ip), headers=headers)
                success = req.status_code == requests.codes.ok
            except:
                pass
            # self.toggleFilamentSensorButton.setEnabled(success)
            return success
        except Exception as e:
            logger.error("Error in MainUiClass.isFilamentSensorInstalled: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.isFilamentSensorInstalled: {}".format(e), overlay=True)

    def toggleFilamentSensor(self):
        """
        Toggles the filament sensor
        """
        logger.info("MainUiClass.toggleFilamentSensor started")
        # headers = {'X-Api-Key': apiKey}
        # # payload = {'sensor_enabled': self.toggleFilamentSensorButton.isChecked()}
        # requests.get('http://{}/plugin/Julia2018FilamentSensor/toggle'.format(ip), headers=headers)   # , data=payload)
        icon = 'filamentSensorOn' if self.toggleFilamentSensorButton.isChecked() else 'filamentSensorOff'
        self.toggleFilamentSensorButton.setIcon(QtGui.QIcon(_fromUtf8("templates/img/" + icon)))
        #octopiclient.gcode(command="SET_FILAMENT_SENSOR SENSOR=SFS_T0 ENABLE={}".format(int(self.toggleFilamentSensorButton.isChecked())))
        #octopiclient.gcode(command="SET_FILAMENT_SENSOR SENSOR=SFS_T1 ENABLE={}".format(int(self.toggleFilamentSensorButton.isChecked())))
        #octopiclient.gcode(command="SET_FILAMENT_SENSOR SENSOR=switch_sensor_T0 ENABLE={}".format(int(self.toggleFilamentSensorButton.isChecked())))
        #octopiclient.gcode(command="SET_FILAMENT_SENSOR SENSOR=encoder_sensor_T0 ENABLE={}".format(int(self.toggleFilamentSensorButton.isChecked())))
        #octopiclient.gcode(command="SET_FILAMENT_SENSOR SENSOR=switch_sensor_T1 ENABLE={}".format(int(self.toggleFilamentSensorButton.isChecked())))
        #octopiclient.gcode(command="SET_FILAMENT_SENSOR SENSOR=encoder_sensor_T1 ENABLE={}".format(int(self.toggleFilamentSensorButton.isChecked())))
        octopiclient.gcode(command="PRIMARY_SFS_ENABLE{}".format(int(self.toggleFilamentSensorButton.isChecked())))
    def filamentSensorHandler(self, data):
        """
        Handles the filament sensor
        """
        logger.info("MainUiClass.filamentSensorHandler started")
        try:
            # sensor_enabled = False
            # # print(data)
            #
            # if 'sensor_enabled' in data:
            #     sensor_enabled = data["sensor_enabled"] == 1
            print(data)

            icon = 'filamentSensorOn' if self.toggleFilamentSensorButton.isChecked() else 'filamentSensorOff'
            self.toggleFilamentSensorButton.setIcon(QtGui.QIcon(_fromUtf8("templates/img/" + icon)))

            if not self.toggleFilamentSensorButton.isChecked():  
                return

            triggered_extruder0 = False
            triggered_extruder1 = False
            # triggered_door = False
            # pause_print = False
            # triggered_door = False
            # pause_print = False

            if '0' in data:
                triggered_extruder0 = True

            if '1' in data:
                triggered_extruder1 = True

            if 'disabled' in data:
                self.toggleFilamentSensorButton.setIcon(QtGui.QIcon(_fromUtf8("templates/img/filamentSensorOff")))

            if 'enabled' in data:
                self.toggleFilamentSensorButton.setIcon(QtGui.QIcon(_fromUtf8("templates/img/filamentSensorOn")))

            # if 'door' in data:
            #     triggered_door = data["door"] == 0
            # if 'pause_print' in data:
            #     pause_print = data["pause_print"]
                
            # if 'door' in data:
            #     triggered_door = data["door"] == 0
            # if 'pause_print' in data:
            #     pause_print = data["pause_print"]

            if triggered_extruder0 and self.stackedWidget.currentWidget() not in [self.changeFilamentPage, self.changeFilamentProgressPage,
                                    self.changeFilamentExtrudePage, self.changeFilamentRetractPage,self.changeFilamentLoadPage]:
                octopiclient.gcode(command='PAUSE')
                if dialog.WarningOk(self, "Filament outage or clog detected in Extruder 0. Please check the external motors. Print paused"):
                    pass

            if triggered_extruder1 and self.stackedWidget.currentWidget() not in [self.changeFilamentPage, self.changeFilamentProgressPage,
                                    self.changeFilamentExtrudePage, self.changeFilamentRetractPage,self.changeFilamentLoadPage]:
                octopiclient.gcode(command='PAUSE')
                if dialog.WarningOk(self, "Filament outage or clog detected in Extruder 1. Please check the external motors. Print paused"):
                    pass

            # if triggered_door:
            #     if self.printerStatusText == "Printing":
            #         no_pause_pages = [self.controlPage, self.changeFilamentPage, self.changeFilamentProgressPage,
            #                           self.changeFilamentExtrudePage, self.changeFilamentRetractPage,self.changeFilamentLoadPage,]
            #         if not pause_print or self.stackedWidget.currentWidget() in no_pause_pages:
            #             if dialog.WarningOk(self, "Door opened"):
            #                 return
            #         octopiclient.pausePrint()
            #         if dialog.WarningOk(self, "Door opened. Print paused.", overlay=True):
            #             return
            #     else:
            #         if dialog.WarningOk(self, "Door opened"):
            #             return
            # if triggered_door:
            #     if self.printerStatusText == "Printing":
            #         no_pause_pages = [self.controlPage, self.changeFilamentPage, self.changeFilamentProgressPage,
            #                           self.changeFilamentExtrudePage, self.changeFilamentRetractPage,self.changeFilamentLoadPage,]
            #         if not pause_print or self.stackedWidget.currentWidget() in no_pause_pages:
            #             if dialog.WarningOk(self, "Door opened"):
            #                 return
            #         octopiclient.pausePrint()
            #         if dialog.WarningOk(self, "Door opened. Print paused.", overlay=True):
            #             return
            #     else:
            #         if dialog.WarningOk(self, "Door opened"):
            #             return
        except Exception as e:
            logger.error("Error in MainUiClass.filamentSensorHandler: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.filamentSensorHandler: {}".format(e), overlay=True)

																			  

    ''' +++++++++++++++++++++++++++ Door Lock +++++++++++++++++++++++++++++++++++++ '''

    def doorLock(self):
        """
        function that toggles locking and unlocking the front door
        :return:
        """
        logger.info("MainUiClass.doorLock started")
        try:
            octopiclient.gcode(command='DoorToggle')
            octopiclient.overrideDoorLock()
        except Exception as e:
            logger.error("Error in MainUiClass.doorLock: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.doorLock: {}".format(e), overlay=True)

    def doorLockMsg(self, data):
        """
        Function that handles the door lock message
        """
        logger.info("MainUiClass.doorLockMsg started")
        try:
            if "msg" not in data:
                return

            msg = data["msg"]

            if self.dialog_doorlock:
                self.dialog_doorlock.close()
                self.dialog_doorlock = None

            if msg is not None:
                self.dialog_doorlock = dialog.dialog(self, msg, icon="exclamation-mark.png")
                if self.dialog_doorlock.exec_() == QtGui.QMessageBox.Ok:
                    self.dialog_doorlock = None
                    return
        except Exception as e:
            logger.error("Error in MainUiClass.doorLockMsg: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.doorLockMsg: {}".format(e), overlay=True)

    def doorLockHandler(self, data):
        """
        Function that handles the door lock status
        """
        logger.info("MainUiClass.doorLockHandler started")
        try:
            door_lock_disabled = False
            door_lock = False
            # door_sensor = False
            # door_lock_override = False

            if 'door_lock' in data:
                door_lock_disabled = data["door_lock"] == "disabled"
                door_lock = data["door_lock"] == 1
            # if 'door_sensor' in data:
            #     door_sensor = data["door_sensor"] == 1
            # if 'door_lock_override' in data:
            #     door_lock_override = data["door_lock_override"] == 1

            # if self.dialog_doorlock:
            #     self.dialog_doorlock.close()
            #     self.dialog_doorlock = None

            self.doorLockButton.setVisible(not door_lock_disabled)
            if not door_lock_disabled:
                # self.doorLockButton.setChecked(not door_lock)
                self.doorLockButton.setText('Lock Door' if not door_lock else 'Unlock Door')

                icon = 'doorLock' if not door_lock else 'doorUnlock'
                self.doorLockButton.setIcon(QtGui.QIcon(_fromUtf8("templates/img/" + icon + ".png")))
            else:
                return
        except Exception as e:
            logger.error("Error in MainUiClass.doorLockHandler: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.doorLockHandler: {}".format(e), overlay=True)

    ''' +++++++++++++++++++++++++++ Firmware Update+++++++++++++++++++++++++++++++++++ '''
    '''TODO: Need to modify this for updating cfg files instead of HEX used for updating Marlin'''
    #
    # isFirmwareUpdateInProgress = False
    #
    # def firmwareUpdateCheck(self):
    #     logger.info("MainUiClass.firmwareUpdateCheck started")
    #     try:
    #         headers = {'X-Api-Key': apiKey}
    #         requests.get('http://{}/plugin/JuliaFirmwareUpdater/update/check'.format(ip), headers=headers)
    #     except Exception as e:
    #         logger.error("Error in MainUiClass.firmwareUpdateCheck: {}".format(e))
    #         dialog.WarningYesNo(self, "Error in MainUiClass.firmwareUpdateCheck: {}".format(e), overlay=True)
    #
    # def firmwareUpdateStart(self):
    #     headers = {'X-Api-Key': apiKey}
    #     requests.get('http://{}/plugin/JuliaFirmwareUpdater/update/start'.format(ip), headers=headers)
    #
    # def firmwareUpdateStartProgress(self):
    #     self.stackedWidget.setCurrentWidget(self.firmwareUpdateProgressPage)
    #     # self.firmwareUpdateLog.setTextColor(QtCore.Qt.yellow)
    #     self.firmwareUpdateLog.setText("<span style='color: cyan'>Julia Firmware Updater<span>")
    #     self.firmwareUpdateLog.append("<span style='color: cyan'>---------------------------------------------------------------</span>")
    #     self.firmwareUpdateBackButton.setEnabled(False)
    #
    # def firmwareUpdateProgress(self, text, backEnabled=False):
    #     self.stackedWidget.setCurrentWidget(self.firmwareUpdateProgressPage)
    #     # self.firmwareUpdateLog.setTextColor(QtCore.Qt.yellow)
    #     self.firmwareUpdateLog.append(str(text))
    #     self.firmwareUpdateBackButton.setEnabled(backEnabled)
    #
    # def firmwareUpdateBack(self):
    #     self.isFirmwareUpdateInProgress = False
    #     self.firmwareUpdateBackButton.setEnabled(False)
    #     self.stackedWidget.setCurrentWidget(self.homePage)
    #
    # def firmwareUpdateHandler(self, data):
    #     if "type" not in data or data["type"] != "status":
    #         return
    #
    #     if "status" not in data:
    #         return
    #
    #     status = data["status"]
    #     subtype = data["subtype"] if "subtype" in data else None
    #
    #     if status == "update_check":    # update check
    #         if subtype == "error":  # notify error in ok diag
    #             self.isFirmwareUpdateInProgress = False
    #             if "message" in data:
    #                 dialog.WarningOk(self, "Firmware Updater Error: " + str(data["message"]), overlay=True)
    #         elif subtype == "success":
    #             if dialog.SuccessYesNo(self, "Firmware update found.\nPress yes to update now!", overlay=True):
    #                 self.isFirmwareUpdateInProgress = True
    #                 self.firmwareUpdateStart()
    #     elif status == "update_start":  # update started
    #         if subtype == "success":    # update progress
    #             self.isFirmwareUpdateInProgress = True
    #             self.firmwareUpdateStartProgress()
    #             if "message" in data:
    #                 message = "<span style='color: yellow'>{}</span>".format(data["message"])
    #                 self.firmwareUpdateProgress(message)
    #         else:   # show error
    #             self.isFirmwareUpdateInProgress = False
    #             # self.firmwareUpdateProgress(data["message"] if "message" in data else "Unknown error!", backEnabled=True)
    #             if "message" in data:
    #                 dialog.WarningOk(self, "Firmware Updater Error: " + str(data["message"]), overlay=True)
    #     elif status == "flasherror" or status == "progress":    # show software update dialog and update textview
    #         if "message" in data:
    #             message = "<span style='color: {}'>{}</span>".format("teal" if status == "progress" else "red", data["message"])
    #             self.firmwareUpdateProgress(message, backEnabled=(status == "flasherror"))
    #     elif status == "success":    # show ok diag to show done
    #         self.isFirmwareUpdateInProgress = False
    #         message = data["message"] if "message" in data else "Flash successful!"
    #         message = "<span style='color: green'>{}</span>".format(message)
    #         message = message + "<br/><br/><span style='color: white'>Press back to continue...</span>"
    #         self.firmwareUpdateProgress(message, backEnabled=True)
    #
    # def getFirmwareVersion(self):
    #     try:
    #         headers = {'X-Api-Key': apiKey}
    #         req = requests.get('http://{}/plugin/JuliaFirmwareUpdater/hardware/version'.format(ip), headers=headers)
    #         data = req.json()
    #         # print(data)
    #         if req.status_code == requests.codes.ok:
    #             info = u'\u2713' if not data["update_available"] else u"\u2717"    # icon
    #             info += " Firmware: "
    #             info += "Unknown" if not data["variant_name"] else data["variant_name"]
    #             info += "\n"
    #             if data["variant_name"]:
    #                 info += "   Installed: "
    #                 info += "Unknown" if not data["version_board"] else data["version_board"]
    #             info += "\n"
    #             info += "" if not data["version_repo"] else "   Available: " + data["version_repo"]
    #             return info
    #     except:
    #         print("Error accessing /plugin/JuliaFirmwareUpdater/hardware/version")
    #         pass
    #     return u'\u2713' + "Firmware: Unknown\n"

    ''' +++++++++++++++++++++++++++++++++OTA Update+++++++++++++++++++++++++++++++++++ '''



    def displayVersionInfo(self):
        """
        Displays the version information for octoprint plugins
        """
        logger.info("MainUiClass.displayVersionInfo started")
        try:
            self.updateListWidget.clear()
            updateAvailable = False
            self.performUpdateButton.setDisabled(True)

            # Firmware version on the MKS https://github.com/FracktalWorks/OctoPrint-JuliaFirmwareUpdater
            # self.updateListWidget.addItem(self.getFirmwareVersion())

            data = octopiclient.getSoftwareUpdateInfo()
            if data:
                for item in data["information"]:
                    # print(item)
                    plugin = data["information"][item]
                    info = u'\u2713' if not plugin["updateAvailable"] else u"\u2717"    # icon
                    info += plugin["displayName"] + "  " + plugin["displayVersion"] + "\n"
                    info += "   Available: "
                    if "information" in plugin and "remote" in plugin["information"] and plugin["information"]["remote"]["value"] is not None:
                        info += plugin["information"]["remote"]["value"]
                    else:
                        info += "Unknown"
                    self.updateListWidget.addItem(info)

                    if plugin["updateAvailable"]:
                        updateAvailable = True

                    # if not updatable:
                    #     self.updateListWidget.addItem(u'\u2713' + data["information"][item]["displayName"] +
                    #                                   "  " + data["information"][item]["displayVersion"] + "\n"
                    #                                   + "   Available: " +
                    #                                   )
                    # else:
                    #     updateAvailable = True
                    #     self.updateListWidget.addItem(u"\u2717" + data["information"][item]["displayName"] +
                    #                                   "  " + data["information"][item]["displayVersion"] + "\n"
                    #                                   + "   Available: " +
                    #                                   data["information"][item]["information"]["remote"]["value"])
            if updateAvailable:
                self.performUpdateButton.setDisabled(False)
            self.stackedWidget.setCurrentWidget(self.OTAUpdatePage)
        except Exception as e:
            logger.error("Error in MainUiClass.displayVersionInfo: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.displayVersionInfo: {}".format(e), overlay=True)

    def softwareUpdateResult(self, data):
        logger.info("MainUiClass.softwareUpdateResult started")
        try:
            messageText = ""
            for item in data:
                messageText += item + ": " + data[item][0] + ".\n"
            messageText += "Restart required"
            self.askAndReboot(messageText)
        except Exception as e:
            logger.error("Error in MainUiClass.softwareUpdateResult: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.softwareUpdateResult: {}".format(e), overlay=True)

    def softwareUpdateProgress(self, data):
        logger.info("MainUiClass.softwareUpdateProgress started")
        try:
            self.stackedWidget.setCurrentWidget(self.softwareUpdateProgressPage)
            self.logTextEdit.setTextColor(QtCore.Qt.red)
            self.logTextEdit.append("---------------------------------------------------------------\n"
                                    "Updating " + data["name"] + " to " + data["version"] + "\n"
                                                                                            "---------------------------------------------------------------")
        except Exception as e:
            logger.error("Error in MainUiClass.softwareUpdateProgress: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.softwareUpdateProgress: {}".format(e), overlay=True)

    def softwareUpdateProgressLog(self, data):
        logger.info("MainUiClass.softwareUpdateProgressLog started")
        try:
            self.logTextEdit.setTextColor(QtCore.Qt.white)
            for line in data:
                self.logTextEdit.append(line["line"])
        except Exception as e:
            logger.error("Error in MainUiClass.softwareUpdateProgressLog: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.softwareUpdateProgressLog: {}".format(e), overlay=True)

    def updateFailed(self, data):
        logger.info("MainUiClass.updateFailed started")
        try:
            self.stackedWidget.setCurrentWidget(self.settingsPage)
            messageText = (data["name"] + " failed to update\n")
            if dialog.WarningOkCancel(self, messageText, overlay=True):
                pass
        except Exception as e:
            logger.error("Error in MainUiClass.updateFailed: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.updateFailed: {}".format(e), overlay=True)

    def softwareUpdate(self):
        logger.info("MainUiClass.softwareUpdate started")
        try:
            data = octopiclient.getSoftwareUpdateInfo()
            updateAvailable = False
            if data:
                for item in data["information"]:
                    if data["information"][item]["updateAvailable"]:
                        updateAvailable = True
            if updateAvailable:
                print('Update Available')
                if dialog.SuccessYesNo(self, "Update Available! Update Now?", overlay=True):
                    octopiclient.performSoftwareUpdate()

            else:
                if dialog.SuccessOk(self, "System is Up To Date!", overlay=True):
                    print('Update Unavailable')
        except Exception as e:
            logger.error("Error in MainUiClass.softwareUpdate: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.softwareUpdate: {}".format(e), overlay=True)

    ''' +++++++++++++++++++++++++++++++++Wifi Config+++++++++++++++++++++++++++++++++++ '''

    def acceptWifiSettings(self):
        logger.info("MainUiClass.acceptWifiSettings started")
        try:
            wlan0_config_file = io.open("/etc/wpa_supplicant/wpa_supplicant.conf", "r+", encoding='utf8')
            wlan0_config_file.truncate()
            ascii_ssid = self.wifiSettingsComboBox.currentText()
            # unicode_ssid = ascii_ssid.decode('string_escape').decode('utf-8')
            wlan0_config_file.write(u"country=IN\n")
            wlan0_config_file.write(u"ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n")
            wlan0_config_file.write(u"update_config=1\n")
            wlan0_config_file.write(u"network={\n")
            wlan0_config_file.write(u'ssid="' + str(ascii_ssid) + '"\n')
            if self.hiddenCheckBox.isChecked():
                wlan0_config_file.write(u'scan_ssid=1\n')
            # wlan0_config_file.write(u"scan_ssid=1\n")
            if str(self.wifiPasswordLineEdit.text()) != "":
                wlan0_config_file.write(u'psk="' + str(self.wifiPasswordLineEdit.text()) + '"\n')
            # wlan0_config_file.write(u"key_mgmt=WPA-PSK\n")
            wlan0_config_file.write(u'}')
            wlan0_config_file.close()
            self.restartWifiThreadObject = ThreadRestartNetworking(ThreadRestartNetworking.WLAN)
            self.restartWifiThreadObject.signal.connect(self.wifiReconnectResult)
            self.restartWifiThreadObject.start()
            self.wifiMessageBox = dialog.dialog(self,
                                                "Restarting networking, please wait...",
                                                icon="exclamation-mark.png",
                                                buttons=QtWidgets.QMessageBox.Cancel)
            if self.wifiMessageBox.exec_() in {QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Cancel}:
                self.stackedWidget.setCurrentWidget(self.networkSettingsPage)
        except Exception as e:
            logger.error("Error in MainUiClass.acceptWifiSettings: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.acceptWifiSettings: {}".format(e), overlay=True)

    def wifiReconnectResult(self, x):
        logger.info("MainUiClass.wifiReconnectResult started")
        try:
            self.wifiMessageBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            if x is not None:
                print("Ouput from signal " + x)
                self.wifiMessageBox.setLocalIcon('success.png')
                self.wifiMessageBox.setText('Connected, IP: ' + x)
                self.wifiMessageBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
                self.ipStatus.setText(x) #sets the IP addr. in the status bar

            else:
                self.wifiMessageBox.setText("Not able to connect to WiFi")
        except Exception as e:
            logger.error("Error in MainUiClass.wifiReconnectResult: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.wifiReconnectResult: {}".format(e), overlay=True)
    def networkInfo(self):
        logger.info("MainUiClass.networkInfo started")
        try:
            ipWifi = getIP(ThreadRestartNetworking.WLAN)
            ipEth = getIP(ThreadRestartNetworking.ETH)

            self.hostname.setText(getHostname())
            self.wifiAp.setText(getWifiAp())
            self.wifiIp.setText("Not connected" if not ipWifi else ipWifi)
            self.ipStatus.setText("Not connected" if not ipWifi else ipWifi)
            self.lanIp.setText("Not connected" if not ipEth else ipEth)
            self.wifiMac.setText(getMac(ThreadRestartNetworking.WLAN).decode('utf8'))
            self.lanMac.setText(getMac(ThreadRestartNetworking.ETH).decode('utf8'))
            self.stackedWidget.setCurrentWidget(self.networkInfoPage)
        except Exception as e:
            logger.error("Error in MainUiClass.networkInfo: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.networkInfo: {}".format(e), overlay=True)

    def wifiSettings(self):
        logger.info("MainUiClass.wifiSettings started")
        try:
            self.stackedWidget.setCurrentWidget(self.wifiSettingsPage)
            self.wifiSettingsComboBox.clear()
            self.wifiSettingsComboBox.addItems(self.scan_wifi())
        except Exception as e:
            logger.error("Error in MainUiClass.wifiSettings: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.wifiSettings: {}".format(e), overlay=True)

    def scan_wifi(self):
        """
        uses linux shell and WIFI interface to scan available networks
        :return: dictionary of the SSID and the signal strength
        """
        logger.info("MainUiClass.scan_wifi started")
        try:
            # scanData = {}
            # print "Scanning available wireless signals available to wlan0"
            scan_result = \
                subprocess.Popen("iwlist wlan0 scan | grep 'ESSID'", stdout=subprocess.PIPE, shell=True).communicate()[0]
            # Processing STDOUT into a dictionary that later will be converted to a json file later
            scan_result = scan_result.decode('utf8').split('ESSID:')  # each ssid and pass from an item in a list ([ssid pass,ssid paas])
            scan_result = [s.strip() for s in scan_result]
            scan_result = [s.strip('"') for s in scan_result]
            scan_result = filter(None, scan_result)
            return scan_result
        except Exception as e:
            logger.error("Error in MainUiClass.scan_wifi: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.scan_wifi: {}".format(e), overlay=True)
            return []

    @run_async
    def setIPStatus(self):
        """
        Function to update IP address of printer on the status bar. Refreshes at a particular interval.
        """
        try:
            while(True):
                try:
                    if getIP("eth0"):
                        self.ipStatus.setText(getIP("eth0"))
                    elif getIP("wlan0"):
                        self.ipStatus.setText(getIP("wlan0"))
                    else:
                        self.ipStatus.setText("Not connected")

                except:
                    self.ipStatus.setText("Not connected")
                time.sleep(60)
        except Exception as e:
            logger.error("Error in MainUiClass.setIPStatus: {}".format(e))



    ''' +++++++++++++++++++++++++++++++++Static IP Settings+++++++++++++++++++++++++++++ '''

    def staticIPSettings(self):
        logger.info("MainUiClass.staticIPSettings started")
        try:
            self.stackedWidget.setCurrentWidget(self.staticIPSettingsPage)
            #add "eth0" and "wlan0" to staticIPComboBox:
            self.staticIPComboBox.clear()
            self.staticIPComboBox.addItems(["eth0", "wlan0"])
        except Exception as e:
            logger.error("Error in MainUiClass.staticIPSettings: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.staticIPSettings: {}".format(e), overlay=True)
    def isIpErr(self, ip):
        return (re.search(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$", ip) is None)

    def showIpErr(self, var):
        return dialog.WarningOk(self, "Invalid input: {0}".format(var))

    def staticIPSaveStaticNetworkInfo(self):
        logger.info("MainUiClass.staticIPSaveStaticNetworkInfo started")
        try:
            txtStaticIPInterface = self.staticIPComboBox.currentText()
            txtStaticIPAddress = str(self.staticIPLineEdit.text())
            txtStaticIPGateway = str(self.staticIPGatewayLineEdit.text())
            txtStaticIPNameServer = str(self.staticIPNameServerLineEdit.text())
            if self.isIpErr(txtStaticIPAddress):
                return self.showIpErr("IP Address")
            if self.isIpErr(txtStaticIPGateway):
                return self.showIpErr("Gateway")
            if txtStaticIPNameServer is not "":
                if self.isIpErr(txtStaticIPNameServer):
                    return self.showIpErr("NameServer")
            Globaltxt = subprocess.Popen("cat /etc/dhcpcd.conf", stdout=subprocess.PIPE, shell=True).communicate()[
                0].decode('utf8')
            staticIPConfig = ""
            # using regex remove all lines staring with "interface" and "static" from txt
            Globaltxt = re.sub(r"interface.*\n", "", Globaltxt)
            Globaltxt = re.sub(r"static.*\n", "", Globaltxt)
            Globaltxt = re.sub(r"^\s+", "", Globaltxt)
            staticIPConfig = "\ninterface {0}\nstatic ip_address={1}/24\nstatic routers={2}\nstatic domain_name_servers=8.8.8.8 8.8.4.4 {3}\n\n".format(
                txtStaticIPInterface, txtStaticIPAddress, txtStaticIPGateway, txtStaticIPNameServer)
            Globaltxt = staticIPConfig + Globaltxt
            with open("/etc/dhcpcd.conf", "w") as f:
                f.write(Globaltxt)

            if txtStaticIPInterface == 'eth0':
                print("Restarting networking for eth0")
                self.restartStaticIPThreadObject = ThreadRestartNetworking(ThreadRestartNetworking.ETH)
                self.restartStaticIPThreadObject.signal.connect(self.staticIPReconnectResult)
                self.restartStaticIPThreadObject.start()
                # self.connect(self.restartStaticIPThreadObject, QtCore.SIGNAL(signal), self.staticIPReconnectResult)
                self.staticIPMessageBox = dialog.dialog(self,
                                                        "Restarting networking, please wait...",
                                                        icon="exclamation-mark.png",
                                                        buttons=QtWidgets.QMessageBox.Cancel)
                if self.staticIPMessageBox.exec_() in {QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Cancel}:
                    self.stackedWidget.setCurrentWidget(self.networkSettingsPage)
            elif txtStaticIPInterface == 'wlan0':
                print("Restarting networking for wlan0")
                self.restartWifiThreadObject = ThreadRestartNetworking(ThreadRestartNetworking.WLAN)
                self.restartWifiThreadObject.signal.connect(self.wifiReconnectResult)
                self.restartWifiThreadObject.start()
                self.wifiMessageBox = dialog.dialog(self,
                                                    "Restarting networking, please wait...",
                                                    icon="exclamation-mark.png",
                                                    buttons=QtWidgets.QMessageBox.Cancel)
                if self.wifiMessageBox.exec_() in {QtWidgets.QMessageBox.Ok, QtWidgets.QMessageBox.Cancel}:
                    self.stackedWidget.setCurrentWidget(self.networkSettingsPage)
        except Exception as e:
            logger.error("Error in MainUiClass.staticIPSaveStaticNetworkInfo: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.staticIPSaveStaticNetworkInfo: {}".format(e), overlay=True)
    def deleteStaticIPSettings(self):
        logger.info("MainUiClass.deleteStaticIPSettings started")
        try:
            Globaltxt = subprocess.Popen("cat /etc/dhcpcd.conf", stdout=subprocess.PIPE, shell=True).communicate()[
                0].decode('utf8')
            # using regex remove all lines staring with "interface" and "static" from txt
            Globaltxt = re.sub(r"interface.*\n", "", Globaltxt)
            Globaltxt = re.sub(r"static.*\n", "", Globaltxt)
            Globaltxt = re.sub(r"^\s+", "", Globaltxt)
            with open("/etc/dhcpcd.conf", "w") as f:
                f.write(Globaltxt)
            self.stackedWidget.setCurrentWidget(self.networkSettingsPage)
        except Exception as e:
            logger.error("Error in MainUiClass.deleteStaticIPSettings: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.deleteStaticIPSettings: {}".format(e), overlay=True)
                                                                                                  
    def staticIPReconnectResult(self, x):
        logger.info("MainUiClass.staticIPReconnectResult started")
        try:
            self.staticIPMessageBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
            if x is not None:
                self.staticIPMessageBox.setLocalIcon('success.png')
                self.staticIPMessageBox.setText('Connected, IP: ' + x)
            else:

                self.staticIPMessageBox.setText("Not able to set Static IP")
        except Exception as e:
            logger.error("Error in MainUiClass.staticIPReconnectResult: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.staticIPReconnectResult: {}".format(e), overlay=True)

    def staticIPShowKeyboard(self, textbox):
        logger.info("MainUiClass.staticIPShowKeyboard started")
        try:
            self.startKeyboard(textbox.setText, onlyNumeric=True, noSpace=True, text=str(textbox.text()))
        except Exception as e:
            logger.error("Error in MainUiClass.staticIPShowKeyboard: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.staticIPShowKeyboard: {}".format(e), overlay=True)


    ''' ++++++++++++++++++++++++++++++++Display Settings+++++++++++++++++++++++++++++++ '''

    def touchCalibration(self):
        logger.info("MainUiClass.touchCalibration started")
        try:
            #os.system('sudo /home/pi/setenv.sh')
            os.system('sudo su')
            os.system('export TSLIB_TSDEVICE=/dev/input/event0')
            os.system('export TSLIB_FBDEVICE=/dev/fb0')
            os.system('ts_calibrate')
        except Exception as e:
            logger.error("Error in MainUiClass.touchCalibration: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.touchCalibration: {}".format(e), overlay=True)

    # def showRotateDisplaySettingsPage(self):
    #
    #     txt = (subprocess.Popen("cat /boot/config.txt", stdout=subprocess.PIPE, shell=True).communicate()[0]).decode("utf-8")
    #
    #     reRot = r"dtoverlay\s*=\s*waveshare35a(\s*:\s*rotate\s*=\s*([0-9]{1,3})){0,1}"
    #     mtRot = re.search(reRot, txt)
    #     # print(mtRot.group(0))
    #
    #     if mtRot and len(mtRot.groups()) == 2 and str(mtRot.group(2)) == "270":
    #         self.rotateDisplaySettingsComboBox.setCurrentIndex(1)
    #     else:
    #         self.rotateDisplaySettingsComboBox.setCurrentIndex(0)
    #
    #     self.stackedWidget.setCurrentWidget(self.rotateDisplaySettingsPage)

    # def saveRotateDisplaySettings(self):
    #     txt1 = (subprocess.Popen("cat /boot/config.txt", stdout=subprocess.PIPE, shell=True).communicate()[0]).decode("utf-8")
    #
    #     reRot = r"dtoverlay\s*=\s*waveshare35a(\s*:\s*rotate\s*=\s*([0-9]{1,3})){0,1}"
    #     if self.rotateDisplaySettingsComboBox.currentIndex() == 1:
    #         op1 = "dtoverlay=waveshare35a,rotate=270,fps=12,speed=16000000"
    #     else:
    #         op1 = "dtoverlay=waveshare35a,fps=12,speed=16000000"
    #     res1 = re.sub(reRot, op1, txt1)
    #
    #     try:
    #         file1 = open("/boot/config.txt", "w")
    #         file1.write(res1)
    #         file1.close()
    #     except:
    #         if dialog.WarningOk(self, "Failed to change rotation settings", overlay=True):
    #             return
    #
    #     txt2 = (subprocess.Popen("cat /usr/share/X11/xorg.conf.d/99-calibration.conf", stdout=subprocess.PIPE,
    #                             shell=True).communicate()[0]).decode("utf-8")
    #
    #     reTouch = r"Option\s+\"Calibration\"\s+\"([\d\s-]+)\""
    #     if self.rotateDisplaySettingsComboBox.currentIndex() == 1:
    #         op2 = "Option \"Calibration\"  \"3919 208 236 3913\""
    #     else:
    #         op2 = "Option \"Calibration\"  \"300 3932 3801 294\""
    #     res2 = re.sub(reTouch, op2, txt2, flags=re.I)
    #
    #     try:
    #         file2 = open("/usr/share/X11/xorg.conf.d/99-calibration.conf", "w")
    #         file2.write(res2)
    #         file2.close()
    #     except:
    #         if dialog.WarningOk(self, "Failed to change touch settings", overlay=True):
    #             return
    #
    #     self.askAndReboot()
    #     self.stackedWidget.setCurrentWidget(self.displaySettingsPage)

    # def saveRotateDisplaySettings(self):
    #     txt1 = (subprocess.Popen("cat /boot/config.txt", stdout=subprocess.PIPE, shell=True).communicate()[0]).decode("utf-8")
    #
    #     try:
    #         if self.rotateDisplaySettingsComboBox.currentIndex() == 1:
    #             os.system('sudo cp -f config/config.txt /boot/config.txt')
    #         else:
    #             os.system('sudo cp -f config/config_rot.txt /boot/config.txt')
    #     except:
    #         if dialog.WarningOk(self, "Failed to change rotation settings", overlay=True):
    #             return
    #     try:
    #         if self.rotateDisplaySettingsComboBox.currentIndex() == 1:
    #             os.system('sudo cp -f config/99-calibration.conf /usr/share/X11/xorg.conf.d/99-calibration.conf')
    #         else:
    #             os.system('sudo cp -f config/99-calibration_rot.conf /usr/share/X11/xorg.conf.d/99-calibration.conf')
    #     except:
    #         if dialog.WarningOk(self, "Failed to change touch settings", overlay=True):
    #             return
    #
    #     self.askAndReboot()
    #     self.stackedWidget.setCurrentWidget(self.displaySettingsPage)
    #

    ''' +++++++++++++++++++++++++++++++++Change Filament+++++++++++++++++++++++++++++++ '''

    def calcExtrudeTime(self, length, speed):
        """
        Calculate the time it takes to extrude a certain length of filament at a certain speed
        :param length: length of filament to extrude
        :param speed: speed at which to extrude
        :return: time in seconds
        """
        return length / (speed/60)

    def unloadFilament(self):
        logger.info("MainUiClass.unloadFilament started")
        try:
            if self.printerStatusText not in ["Printing","Paused"]:
                if self.activeExtruder == 1:
                    octopiclient.jog(tool1PurgePosition['X'],tool1PurgePosition["Y"] ,absolute=True, speed=10000)

                else:
                    octopiclient.jog(tool0PurgePosition['X'],tool0PurgePosition["Y"] ,absolute=True, speed=10000)

            if self.changeFilamentComboBox.findText("Loaded Filament") == -1:
                octopiclient.setToolTemperature({"tool1": filaments[str(
                    self.changeFilamentComboBox.currentText())]}) if self.activeExtruder == 1 else octopiclient.setToolTemperature(
                    {"tool0": filaments[str(self.changeFilamentComboBox.currentText())]})
            self.stackedWidget.setCurrentWidget(self.changeFilamentProgressPage)
            self.changeFilamentStatus.setText("Heating Tool {}, Please Wait...".format(str(self.activeExtruder)))
            self.changeFilamentNameOperation.setText("Unloading {}".format(str(self.changeFilamentComboBox.currentText())))
            # this flag tells the updateTemperature function that runs every second to update the filament change progress bar as well, and to load or unload after heating done
            self.changeFilamentHeatingFlag = True
            self.loadFlag = False
        except Exception as e:
            self.loadFlag = False
            self.changeFilamentHeatingFlag = False
            logger.error("Error in MainUiClass.unloadFilament: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.unloadFilament: {}".format(e), overlay=True)

    def loadFilament(self):
        logger.info("MainUiClass.loadFilament started")
        try:
            if self.printerStatusText not in ["Printing","Paused"]:
                if self.activeExtruder == 1:
                    octopiclient.jog(tool1PurgePosition['X'],tool1PurgePosition["Y"] ,absolute=True, speed=10000)

                else:
                    octopiclient.jog(tool0PurgePosition['X'],tool0PurgePosition["Y"] ,absolute=True, speed=10000)

            if self.changeFilamentComboBox.findText("Loaded Filament") == -1:
                octopiclient.setToolTemperature({"tool1": filaments[str(
                    self.changeFilamentComboBox.currentText())]}) if self.activeExtruder == 1 else octopiclient.setToolTemperature(
                    {"tool0": filaments[str(self.changeFilamentComboBox.currentText())]})
            self.stackedWidget.setCurrentWidget(self.changeFilamentProgressPage)
            self.changeFilamentStatus.setText("Heating Tool {}, Please Wait...".format(str(self.activeExtruder)))
            self.changeFilamentNameOperation.setText("Loading {}".format(str(self.changeFilamentComboBox.currentText())))
            # this flag tells the updateTemperature function that runs every second to update the filament change progress bar as well, and to load or unload after heating done
            self.changeFilamentHeatingFlag = True
            self.loadFlag = True
        except Exception as e:
            self.loadFlag = False
            self.changeFilamentHeatingFlag = False
            logger.error("Error in MainUiClass.loadFilament: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.loadFilament: {}".format(e), overlay=True)


    @run_async
    def changeFilamentLoadFunction(self):
        """
        This function is called once the heating is done, which slowly moves the extruder so that it starts pulling filament
        """
        logger.info("MainUiClass.changeFilamentLoadFunction started")
        try:
            self.stackedWidget.setCurrentWidget(self.changeFilamentLoadPage)
            while self.stackedWidget.currentWidget() == self.changeFilamentLoadPage:
                octopiclient.gcode("G91")
                octopiclient.gcode("G1 E5 F500")
                octopiclient.gcode("G90")
                time.sleep(self.calcExtrudeTime(5, 500))
        except Exception as e:
            logger.error("Error in MainUiClass.changeFilamentLoadFunction: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.changeFilamentLoadFunction: {}".format(e), overlay=True)

    @run_async
    def changeFilamentExtrudePageFunction(self):
        """
        once filament is loaded, this function is called to extrude filament till the toolhead
        """
        logger.info("MainUiClass.changeFilamentExtrudePageFunction started")
        try:
            self.stackedWidget.setCurrentWidget(self.changeFilamentExtrudePage)
            for i in range(int(ptfeTubeLength/150)):
                octopiclient.gcode("G91")
                octopiclient.gcode("G1 E150 F1500")
                octopiclient.gcode("G90")
                time.sleep(self.calcExtrudeTime(150, 1500))
                if self.stackedWidget.currentWidget() is not self.changeFilamentExtrudePage:
                    break

            while self.stackedWidget.currentWidget() == self.changeFilamentExtrudePage:
                if self.changeFilamentComboBox.currentText() == "TPU":
                    octopiclient.gcode("G91")
                    octopiclient.gcode("G1 E20 F300")
                    octopiclient.gcode("G90")
                    time.sleep(self.calcExtrudeTime(20, 300))
                else:
                    octopiclient.gcode("G91")
                    octopiclient.gcode("G1 E20 F600")
                    octopiclient.gcode("G90")
                    time.sleep(self.calcExtrudeTime(20, 600))
        except Exception as e:
            logger.error("Error in MainUiClass.changeFilamentExtrudePageFunction: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.changeFilamentExtrudePageFunction: {}".format(e), overlay=True)
    @run_async
    def changeFilamentRetractFunction(self):
        """
        Remove the filament from the toolhead
        """
        logger.info("MainUiClass.changeFilamentRetractFunction started")
        try:
            self.stackedWidget.setCurrentWidget(self.changeFilamentRetractPage)
            # Tip Shaping to prevent filament jamming in nozzle
            if self.changeFilamentComboBox.currentText() == "TPU":
                octopiclient.gcode("G91")
                octopiclient.gcode("G1 E10 F300")
                time.sleep(self.calcExtrudeTime(10, 300))
            else:
                octopiclient.gcode("G91")
                octopiclient.gcode("G1 E10 F600")
                time.sleep(self.calcExtrudeTime(10, 600))
            octopiclient.gcode("G1 E-25 F6000")
            time.sleep(self.calcExtrudeTime(20, 6000))
            time.sleep(8) #wait for filament to cool inside the nozzle
            octopiclient.gcode("G1 E-150 F5000")
            time.sleep(self.calcExtrudeTime(150, 5000))
            octopiclient.gcode("G90")
            for i in range(int(ptfeTubeLength/150)):
                octopiclient.gcode("G91")
                octopiclient.gcode("G1 E-150 F2000")
                octopiclient.gcode("G90")
                time.sleep(self.calcExtrudeTime(150, 2000))
                if self.stackedWidget.currentWidget() is not self.changeFilamentRetractPage:
                    break

            while self.stackedWidget.currentWidget() == self.changeFilamentRetractPage:
                octopiclient.gcode("G91")
                octopiclient.gcode("G1 E-5 F1000")
                octopiclient.gcode("G90")
                time.sleep(self.calcExtrudeTime(5, 1000))
        except Exception as e:
            logger.error("Error in MainUiClass.changeFilamentRetractFunction: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.changeFilamentRetractFunction: {}".format(e), overlay=True)

    def changeFilament(self):
        """
        This function is called when the user wants to change the filament. It sets the current page to the change filament page
        and preps the printer for filament change
        """
        logger.info("MainUiClass.changeFilament started")
        try:
            time.sleep(1)
            if self.printerStatusText not in ["Printing","Paused"]:
                octopiclient.gcode("G28")
            self.selectToolChangeFilament()

            self.stackedWidget.setCurrentWidget(self.changeFilamentPage)
            self.changeFilamentComboBox.clear()
            self.changeFilamentComboBox.addItems(filaments.keys())
            #Update
            print(self.tool0TargetTemperature)
            if self.tool0TargetTemperature  and self.printerStatusText in ["Printing","Paused"]:
                self.changeFilamentComboBox.addItem("Loaded Filament")
                index = self.changeFilamentComboBox.findText("Loaded Filament")
                if index >= 0 :
                    self.changeFilamentComboBox.setCurrentIndex(index)
        except Exception as e:
            logger.error("Error in MainUiClass.changeFilament: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.changeFilament: {}".format(e), overlay=True)
    def changeFilamentCancel(self):
        logger.info("MainUiClass.changeFilamentCancel started")
        try:
            self.changeFilamentHeatingFlag = False
            if self.printerStatusText not in ["Printing","Paused"]:
                self.coolDownAction()
            self.control()
            self.loadFlag = False
            self.changeFilamentHeatingFlag = False
        except Exception as e:
            logger.error("Error in MainUiClass.changeFilamentCancel: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.changeFilamentCancel: {}".format(e), overlay=True)

    ''' +++++++++++++++++++++++++++++++++Job Operations+++++++++++++++++++++++++++++++ '''

    def stopActionMessageBox(self):
        """
        Displays a message box asking if the user is sure if he wants to turn off the print
        """
        logger.info("MainUiClass.stopActionMessageBox started")
        try:
            if dialog.WarningYesNo(self, "Are you sure you want to stop the print?"):
                octopiclient.cancelPrint()
        except Exception as e:
            logger.error("Error in MainUiClass.stopActionMessageBox: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.stopActionMessageBox: {}".format(e), overlay=True)

    def playPauseAction(self):
        """
        Toggles Play/Pause of a print depending on the status of the print
        """
        logger.info("MainUiClass.playPauseAction started")
        try:
            if self.printerStatusText == "Operational":
                if self.playPauseButton.isChecked:
                    self.checkKlipperPrinterCFG()
                    octopiclient.startPrint()
            elif self.printerStatusText == "Printing":
                octopiclient.pausePrint()
            elif self.printerStatusText == "Paused":
                octopiclient.pausePrint()
        except Exception as e:
            logger.error("Error in MainUiClass.playPauseAction: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.playPauseAction: {}".format(e), overlay=True)

    def fileListLocal(self):
        """
        Gets the file list from octoprint server, displays it on the list, as well as
        sets the stacked widget page to the file list page
        """
        logger.info("MainUiClass.fileListLocal started")
        try:
            self.stackedWidget.setCurrentWidget(self.fileListLocalPage)
            files = []
            for file in octopiclient.retrieveFileInformation()['files']:
                if file["type"] == "machinecode":
                    files.append(file)

            self.fileListWidget.clear()
            files.sort(key=lambda d: d['date'], reverse=True)
            # for item in [f['name'] for f in files] :
            #     self.fileListWidget.addItem(item)
            self.fileListWidget.addItems([f['name'] for f in files])
            self.fileListWidget.setCurrentRow(0)
        except Exception as e:
            logger.error("Error in MainUiClass.fileListLocal: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.fileListLocal: {}".format(e), overlay=True)

    def fileListUSB(self):
        """
        Gets the file list from octoprint server, displays it on the list, as well as
        sets the stacked widget page to the file list page
        ToDO: Add deapth of folders recursively get all gcodes
        """
        logger.info("MainUiClass.fileListUSB started")
        try:
            self.stackedWidget.setCurrentWidget(self.fileListUSBPage)
            self.fileListWidgetUSB.clear()
            files = subprocess.Popen("ls /media/usb0 | grep gcode", stdout=subprocess.PIPE, shell=True).communicate()[0]
            files = files.decode('utf-8').split('\n')
            files = filter(None, files)
            # for item in files:
            #     self.fileListWidgetUSB.addItem(item)
            self.fileListWidgetUSB.addItems(files)
            self.fileListWidgetUSB.setCurrentRow(0)
        except Exception as e:
            logger.error("Error in MainUiClass.fileListUSB: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.fileListUSB: {}".format(e), overlay=True)


    def printSelectedLocal(self):

        """
        gets information about the selected file from octoprint server,
        as well as sets the current page to the print selected page.
        This function also selects the file to print from octoprint
        """
        logger.info("MainUiClass.printSelectedLocal started")
        try:
            self.fileSelected.setText(self.fileListWidget.currentItem().text())
            self.stackedWidget.setCurrentWidget(self.printSelectedLocalPage)
            file = octopiclient.retrieveFileInformation(self.fileListWidget.currentItem().text())
            try:
                self.fileSizeSelected.setText(size(file['size']))
            except KeyError:
                self.fileSizeSelected.setText('-')
            try:
                self.fileDateSelected.setText(datetime.fromtimestamp(file['date']).strftime('%d/%m/%Y %H:%M:%S'))
            except KeyError:
                self.fileDateSelected.setText('-')
            try:
                m, s = divmod(file['gcodeAnalysis']['estimatedPrintTime'], 60)
                h, m = divmod(m, 60)
                d, h = divmod(h, 24)
                self.filePrintTimeSelected.setText("%dd:%dh:%02dm:%02ds" % (d, h, m, s))
            except KeyError:
                self.filePrintTimeSelected.setText('-')
            try:
                self.filamentVolumeSelected.setText(
                    ("%.2f cm" % file['gcodeAnalysis']['filament']['tool0']['volume']) + chr(179))
            except KeyError:
                self.filamentVolumeSelected.setText('-')

            try:
                self.filamentLengthFileSelected.setText(
                    "%.2f mm" % file['gcodeAnalysis']['filament']['tool0']['length'])
            except KeyError:
                self.filamentLengthFileSelected.setText('-')
            # uncomment to select the file when selectedd in list
            # octopiclient.selectFile(self.fileListWidget.currentItem().text(), False)
            self.stackedWidget.setCurrentWidget(self.printSelectedLocalPage)

            '''
            If image is available from server, set it, otherwise display default image
            '''
            self.displayThumbnail(self.printPreviewSelected, str(self.fileListWidget.currentItem().text()), usb=False)

        except Exception as e:
            logger.error("Error in MainUiClass.printSelectedLocal: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.printSelectedLocal: {}".format(e), overlay=True)


    def printSelectedUSB(self):
        """
        Sets the screen to the print selected screen for USB, on which you can transfer to local drive and view preview image.
        :return:
        """
        logger.info("MainUiClass.printSelectedUSB started")
        try:
            self.fileSelectedUSBName.setText(self.fileListWidgetUSB.currentItem().text())
            self.stackedWidget.setCurrentWidget(self.printSelectedUSBPage)
            self.displayThumbnail(self.printPreviewSelectedUSB, '/media/usb0/' + str(self.fileListWidgetUSB.currentItem().text()), usb=True)
        except Exception as e:
            logger.error("Error in MainUiClass.printSelectedUSB: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.printSelectedUSB: {}".format(e), overlay=True)

            # Set Image from USB

    def transferToLocal(self, prnt=False):
        """
        Transfers a file from USB mounted at /media/usb0 to octoprint's watched folder so that it gets automatically detected bu Octoprint.
        Warning: If the file is read-only, octoprint API for reading the file crashes.
        """
        logger.info("MainUiClass.transferToLocal started")
        try:
            file = '/media/usb0/' + str(self.fileListWidgetUSB.currentItem().text())

            self.uploadThread = ThreadFileUpload(file, prnt=prnt)
            self.uploadThread.start()
            if prnt:
                self.stackedWidget.setCurrentWidget(self.homePage)
        except Exception as e:
            logger.error("Error in MainUiClass.transferToLocal: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.transferToLocal: {}".format(e), overlay=True)

    def printFile(self):
        """
        Prints the file selected from printSelected()
        """
        logger.info("MainUiClass.printFile started")
        try:
            octopiclient.home(['x', 'y', 'z'])
            octopiclient.selectFile(self.fileListWidget.currentItem().text(), True)
            self.checkKlipperPrinterCFG()
            self.stackedWidget.setCurrentWidget(self.homePage)
        except Exception as e:
            logger.error("Error in MainUiClass.printFile: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.printFile: {}".format(e), overlay=True)


    def deleteItem(self):
        """
        Deletes a gcode file, and if associates, its image file from the memory
        """
        logger.info("MainUiClass.deleteItem started")
        try:
            octopiclient.deleteFile(self.fileListWidget.currentItem().text())
            octopiclient.deleteFile(self.fileListWidget.currentItem().text().replace(".gcode", ".png"))
            # delete PNG also
            self.fileListLocal()
        except Exception as e:
            logger.error("Error in MainUiClass.deleteItem: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.deleteItem: {}".format(e), overlay=True)


    def getImageFromGcode(self,gcodeLocation):
        """
        Gets the image from the gcode text file
        """
        logger.info("MainUiClass.getImageFromGcode started")
        try:
            with open(gcodeLocation, 'rb') as f:
                content = f.readlines()[:500]
                content = b''.join(content)
            start = content.find(b'; thumbnail begin')
            end = content.find(b'; thumbnail end')
            if start != -1 and end != -1:
                thumbnail = content[start:end]
                thumbnail = base64.b64decode(thumbnail[thumbnail.find(b'\n') + 1:].replace(b'; ', b'').replace(b'\r\n', b''))
                return thumbnail
            else:
                return False
        except Exception as e:
            logger.error("Error in MainUiClass.getImageFromGcode: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.getImageFromGcode: {}".format(e), overlay=True)
            return False

    @run_async
    def displayThumbnail(self,labelObject,fileLocation, usb=False):
        """
        Displays the image on the label object
        :param labelObject: QLabel object to display the image
        :param fileLocation: location of the file
        :param usb: if the file is from
        """
        logger.info("MainUiClass.displayThumbnail started")
        try:
            pixmap = QtGui.QPixmap()
            if usb:
                img = self.getImageFromGcode(fileLocation)
            else:
                img = octopiclient.getImage(fileLocation)
            if img:
                pixmap.loadFromData(img)
                labelObject.setPixmap(pixmap)
            else:
                labelObject.setPixmap(QtGui.QPixmap(_fromUtf8("templates/img/thumbnail.png")))
        except Exception as e:
            labelObject.setPixmap(QtGui.QPixmap(_fromUtf8("templates/img/thumbnail.png")))
            logger.error("Error in MainUiClass.displayThumbnail: {}".format(e))

    ''' +++++++++++++++++++++++++++++++++Printer Status+++++++++++++++++++++++++++++++ '''

    def updateTemperature(self, temperature):
        """
        Slot that gets a signal originating from the thread that keeps polling for printer status
        runs at 1HZ, so do things that need to be constantly updated only. This also controls the cooling fan depending on the temperatures
        :param temperature: dict containing key:value pairs with keys being the tools, bed and their values being their corresponding temperratures
        """
        try:
            try:
                if temperature['tool0Target'] == 0:
                    self.tool0TempBar.setMaximum(300)
                    self.tool0TempBar.setStyleSheet(styles.bar_heater_cold)
                elif temperature['tool0Actual'] <= temperature['tool0Target']:
                    self.tool0TempBar.setMaximum(temperature['tool0Target'])
                    self.tool0TempBar.setStyleSheet(styles.bar_heater_heating)
                else:
                    self.tool0TempBar.setMaximum(temperature['tool0Actual'])
                self.tool0TempBar.setValue(temperature['tool0Actual'])
                self.tool0ActualTemperature.setText(str(int(temperature['tool0Actual'])))  # + unichr(176)
                self.tool0TargetTemperature.setText(str(int(temperature['tool0Target'])))

                if temperature['tool1Target'] == 0:
                    self.tool1TempBar.setMaximum(300)
                    self.tool1TempBar.setStyleSheet(styles.bar_heater_cold)
                elif temperature['tool1Actual'] <= temperature['tool1Target']:
                    self.tool1TempBar.setMaximum(temperature['tool1Target'])
                    self.tool1TempBar.setStyleSheet(styles.bar_heater_heating)
                else:
                    self.tool1TempBar.setMaximum(temperature['tool1Actual'])
                self.tool1TempBar.setValue(temperature['tool1Actual'])
                self.tool1ActualTemperature.setText(str(int(temperature['tool1Actual'])))  # + unichr(176)
                self.tool1TargetTemperature.setText(str(int(temperature['tool1Target'])))

                if temperature['bedTarget'] == 0:
                    self.bedTempBar.setMaximum(150)
                    self.bedTempBar.setStyleSheet(styles.bar_heater_cold)
                elif temperature['bedActual'] <= temperature['bedTarget']:
                    self.bedTempBar.setMaximum(temperature['bedTarget'])
                    self.bedTempBar.setStyleSheet(styles.bar_heater_heating)
                else:
                    self.bedTempBar.setMaximum(temperature['bedActual'])
                self.bedTempBar.setValue(temperature['bedActual'])
                self.bedActualTemperatute.setText(str(int(temperature['bedActual'])))  # + unichr(176))
                self.bedTargetTemperature.setText(str(int(temperature['bedTarget'])))  # + unichr(176))

            except:
                pass

            # updates the progress bar on the change filament screen
            if self.changeFilamentHeatingFlag:
                if self.activeExtruder == 0:
                    if temperature['tool0Target'] == 0:
                        self.changeFilamentProgress.setMaximum(300)
                    elif temperature['tool0Target'] - temperature['tool0Actual'] > 1:
                        self.changeFilamentProgress.setMaximum(temperature['tool0Target'])
                    else:
                        self.changeFilamentProgress.setMaximum(temperature['tool0Actual'])
                        self.changeFilamentHeatingFlag = False
                        if self.loadFlag:
                            self.changeFilamentLoadFunction()
                            #self.stackedWidget.setCurrentWidget(self.changeFilamentExtrudePage)
                        else:
                            #self.stackedWidget.setCurrentWidget(self.changeFilamentRetractPage)
                            octopiclient.extrude(5)     # extrudes some amount of filament to prevent plugging
                            self.changeFilamentRetractFunction()

                    self.changeFilamentProgress.setValue(temperature['tool0Actual'])
                elif self.activeExtruder == 1:
                    if temperature['tool1Target'] == 0:
                        self.changeFilamentProgress.setMaximum(300)
                    elif temperature['tool1Target'] - temperature['tool1Actual'] > 1:
                        self.changeFilamentProgress.setMaximum(temperature['tool1Target'])
                    else:
                        self.changeFilamentProgress.setMaximum(temperature['tool1Actual'])
                        self.changeFilamentHeatingFlag = False
                        if self.loadFlag:
                            self.changeFilamentLoadFunction()
                            #self.stackedWidget.setCurrentWidget(self.changeFilamentExtrudePage)
                        else:
                            #self.stackedWidget.setCurrentWidget(self.changeFilamentRetractPage)
                            octopiclient.extrude(5)     # extrudes some amount of filament to prevent plugging
                            self.changeFilamentRetractFunction()

                    self.changeFilamentProgress.setValue(temperature['tool1Actual'])
        except Exception as e:
            logger.error("Error in MainUiClass.updateTemperature: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.updateTemperature: {}".format(e), overlay=True)

    def updatePrintStatus(self, file):
        """
        displays infromation of a particular file on the home page,is a slot for the signal emited from the thread that keeps pooling for printer status
        runs at 1HZ, so do things that need to be constantly updated only
        :param file: dict of all the attributes of a particualr file
        """

        try:
            if file is None:
                self.currentFile = None
                self.currentImage = None
                self.timeLeft.setText("-")
                self.fileName.setText("-")
                self.printProgressBar.setValue(0)
                self.printTime.setText("-")
                self.playPauseButton.setDisabled(True)  # if file available, make play buttom visible

            else:
                self.playPauseButton.setDisabled(False)  # if file available, make play buttom visible
                self.fileName.setText(file['job']['file']['name'])
                self.currentFile = file['job']['file']['name']
                if file['progress']['printTime'] is None:
                    self.printTime.setText("-")
                else:
                    m, s = divmod(file['progress']['printTime'], 60)
                    h, m = divmod(m, 60)
                    d, h = divmod(h, 24)
                    self.printTime.setText("%d:%d:%02d:%02d" % (d, h, m, s))

                if file['progress']['printTimeLeft'] is None:
                    self.timeLeft.setText("-")
                else:
                    m, s = divmod(file['progress']['printTimeLeft'], 60)
                    h, m = divmod(m, 60)
                    d, h = divmod(h, 24)
                    self.timeLeft.setText("%d:%d:%02d:%02d" % (d, h, m, s))

                if file['progress']['completion'] is None:
                    self.printProgressBar.setValue(0)
                else:
                    self.printProgressBar.setValue(file['progress']['completion'])

                '''
                If image is available from server, set it, otherwise display default image.
                If the image was already loaded, dont load it again.
                '''
                if self.currentImage != self.currentFile:
                    self.currentImage = self.currentFile
                    self.displayThumbnail(self.printPreviewMain, self.currentFile, usb=False)
        except Exception as e:
            logger.error("Error in MainUiClass.updatePrintStatus: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.updatePrintStatus: {}".format(e), overlay=True)

    def updateStatus(self, status):
        """
        Updates the status bar, is a slot for the signal emited from the thread that constantly polls for printer status
        this function updates the status bar, as well as enables/disables relavent buttons
        :param status: String of the status text
        """
        try:
            self.printerStatusText = status
            self.printerStatus.setText(status)

            if status == "Printing":  # Green
                self.printerStatusColour.setStyleSheet(styles.printer_status_green)
            elif status == "Offline":  # Red
                self.printerStatusColour.setStyleSheet(styles.printer_status_red)
            elif status == "Paused":  # Amber
                self.printerStatusColour.setStyleSheet(styles.printer_status_amber)
            elif status == "Operational":  # Amber
                self.printerStatusColour.setStyleSheet(styles.printer_status_blue)

            '''
            Depending on Status, enable and Disable Buttons
            '''
            if status == "Printing":
                self.playPauseButton.setChecked(True)
                self.stopButton.setDisabled(False)
                self.motionTab.setDisabled(True)
                self.changeFilamentButton.setDisabled(True)
                self.menuCalibrateButton.setDisabled(True)
                self.menuPrintButton.setDisabled(True)
                self.doorLockButton.setDisabled(False)
                # if not self.__timelapse_enabled:
                #     octopiclient.cancelPrint()
                #     self.coolDownAction()

            elif status == "Paused":
                self.playPauseButton.setChecked(False)
                self.stopButton.setDisabled(False)
                self.motionTab.setDisabled(False)
                self.changeFilamentButton.setDisabled(False)
                self.menuCalibrateButton.setDisabled(True)
                self.menuPrintButton.setDisabled(True)
                self.doorLockButton.setDisabled(False)


            else:
                self.stopButton.setDisabled(True)
                self.playPauseButton.setChecked(False)
                self.motionTab.setDisabled(False)
                self.changeFilamentButton.setDisabled(False)
                self.menuCalibrateButton.setDisabled(False)
                self.menuPrintButton.setDisabled(False)
                self.doorLockButton.setDisabled(True)
        except Exception as e:
            logger.error("Error in MainUiClass.updateStatus: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.updateStatus: {}".format(e), overlay=True)

    ''' ++++++++++++++++++++++++++++Active Extruder/Tool Change++++++++++++++++++++++++ '''

    def selectToolChangeFilament(self):
        """
        Selects the tool whose temperature needs to be changed. It accordingly changes the button text. it also updates the status of the other toggle buttons
        """
        logger.info("MainUiClass.selectToolChangeFilament started")
        try:
            if self.toolToggleChangeFilamentButton.isChecked():
                self.setActiveExtruder(1)
                octopiclient.selectTool(1)
                octopiclient.jog(tool1PurgePosition['X'],tool1PurgePosition["Y"] ,absolute=True, speed=10000)
                time.sleep(1)

            else:
                self.setActiveExtruder(0)
                octopiclient.selectTool(0)
                octopiclient.jog(tool0PurgePosition['X'],tool0PurgePosition["Y"] ,absolute=True, speed=10000)
                time.sleep(1)
        except Exception as e:
            logger.error("Error in MainUiClass.selectToolChangeFilament: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.selectToolChangeFilament: {}".format(e), overlay=True)


    def selectToolMotion(self):
        """
        Selects the tool whose temperature needs to be changed. It accordingly changes the button text. it also updates the status of the other toggle buttons
        """
        logger.info("MainUiClass.selectToolMotion started")
        try:
            if self.toolToggleMotionButton.isChecked():
                self.setActiveExtruder(1)
                octopiclient.selectTool(1)

            else:
                self.setActiveExtruder(0)
                octopiclient.selectTool(0)
        except Exception as e:
            logger.error("Error in MainUiClass.selectToolMotion: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.selectToolMotion: {}".format(e), overlay=True)

    def selectToolTemperature(self):
        """
        Selects the tool whose temperature needs to be changed. It accordingly changes the button text.it also updates the status of the other toggle buttons
        """
        logger.info("MainUiClass.selectToolTemperature started")
        try:
            # self.toolToggleTemperatureButton.setText(
            #     "1") if self.toolToggleTemperatureButton.isChecked() else self.toolToggleTemperatureButton.setText("0")
            if self.toolToggleTemperatureButton.isChecked():
                print ("extruder 1 Temperature")
                self.toolTempSpinBox.setProperty("value", float(self.tool1TargetTemperature.text()))
            else:
                print ("extruder 0 Temperature")
                self.toolTempSpinBox.setProperty("value", float(self.tool0TargetTemperature.text()))
        except Exception as e:
            logger.error("Error in MainUiClass.selectToolTemperature: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.selectToolTemperature: {}".format(e), overlay=True)

    def setActiveExtruder(self, activeNozzle):
        """
        Sets the active extruder, and changes the UI accordingly
        """
        logger.info("MainUiClass.setActiveExtruder started")
        try:
            activeNozzle = int(activeNozzle)
            if activeNozzle == 0:
                self.tool0Label.setPixmap(QtGui.QPixmap(_fromUtf8("templates/img/activeNozzle.png")))
                self.tool1Label.setPixmap(QtGui.QPixmap(_fromUtf8("templates/img/Nozzle.png")))
                self.toolToggleChangeFilamentButton.setChecked(False)
                # self.toolToggleChangeFilamentButton.setText("0")
                self.toolToggleMotionButton.setChecked(False)
                self.toolToggleMotionButton.setText("0")
                self.activeExtruder = 0
            elif activeNozzle == 1:
                self.tool0Label.setPixmap(QtGui.QPixmap(_fromUtf8("templates/img/Nozzle.png")))
                self.tool1Label.setPixmap(QtGui.QPixmap(_fromUtf8("templates/img/activeNozzle.png")))
                self.toolToggleChangeFilamentButton.setChecked(True)
                # self.toolToggleChangeFilamentButton.setText("1")
                self.toolToggleMotionButton.setChecked(True)
                self.toolToggleMotionButton.setText("1")
                self.activeExtruder = 1

                # set button states
                # set octoprint if mismatch
        except Exception as e:
            logger.error("Error in MainUiClass.setActiveExtruder: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.setActiveExtruder: {}".format(e), overlay=True)

    ''' +++++++++++++++++++++++++++++++++Control Screen+++++++++++++++++++++++++++++++ '''

    def control(self):
        """
        Sets the current page to the control page
        """
        logger.info("MainUiClass.control started")
        try:
            self.stackedWidget.setCurrentWidget(self.controlPage)
            if self.toolToggleTemperatureButton.isChecked():
                self.toolTempSpinBox.setProperty("value", float(self.tool1TargetTemperature.text()))
            else:
                self.toolTempSpinBox.setProperty("value", float(self.tool0TargetTemperature.text()))
            self.bedTempSpinBox.setProperty("value", float(self.bedTargetTemperature.text()))
        except Exception as e:
            logger.error("Error in MainUiClass.control: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.control: {}".format(e), overlay=True)

    def setStep(self, stepRate):
        """
        Sets the class variable "Step" which would be needed for movement and joging
        :param stepRate: step multiplier for movement in the move
        :return: nothing
        """
        logger.info("MainUiClass.setStep started")
        try:
            if stepRate == 100:
                self.step100Button.setFlat(True)
                self.step1Button.setFlat(False)
                self.step10Button.setFlat(False)
                self.step = 100
            if stepRate == 1:
                self.step100Button.setFlat(False)
                self.step1Button.setFlat(True)
                self.step10Button.setFlat(False)
                self.step = 1
            if stepRate == 10:
                self.step100Button.setFlat(False)
                self.step1Button.setFlat(False)
                self.step10Button.setFlat(True)
                self.step = 10
        except Exception as e:
            logger.error("Error in MainUiClass.setStep: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.setStep: {}".format(e), overlay=True)

    def setToolTemp(self):
        """
        Sets the temperature of the tool, depending on the tool selected
        """
        logger.info("MainUiClass.setToolTemp started")
        try:
            if self.toolToggleTemperatureButton.isChecked():
                octopiclient.gcode(command='M104 T1 S' + str(self.toolTempSpinBox.value()))
                # octopiclient.setToolTemperature({"tool1": self.toolTempSpinBox.value()})
            else:
                octopiclient.gcode(command='M104 T0 S' + str(self.toolTempSpinBox.value()))
                # octopiclient.setToolTemperature({"tool0": self.toolTempSpinBox.value()})
        except Exception as e:
            logger.error("Error in MainUiClass.setToolTemp: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.setToolTemp: {}".format(e), overlay=True)

    def preheatToolTemp(self, temp):
        """
        Preheats the tool to the given temperature
        param temp: temperature to preheat to
        """
        logger.info("MainUiClass.preheatToolTemp started")
        try:
            if self.toolToggleTemperatureButton.isChecked():
                octopiclient.gcode(command='M104 T1 S' + str(temp))
            else:
                octopiclient.gcode(command='M104 T0 S' + str(temp))
            self.toolTempSpinBox.setProperty("value", temp)
        except Exception as e:
            logger.error("Error in MainUiClass.preheatToolTemp: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.preheatToolTemp: {}".format(e), overlay=True)

    def preheatBedTemp(self, temp):
        """
        Preheats the bed to the given temperature
        param temp: temperature to preheat to
        """
        logger.info("MainUiClass.preheatBedTemp started")
        try:
            octopiclient.gcode(command='M140 S' + str(temp))
            self.bedTempSpinBox.setProperty("value", temp)
        except Exception as e:
            logger.error("Error in MainUiClass.preheatBedTemp: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.preheatBedTemp: {}".format(e), overlay=True)

    def coolDownAction(self):
        """'
        Turns all heaters and fans off
        """
        logger.info("MainUiClass.coolDownAction started")
        try:
            octopiclient.gcode(command='M107')
            octopiclient.setToolTemperature({"tool0": 0, "tool1": 0})
            # octopiclient.setToolTemperature({"tool0": 0})
            octopiclient.setBedTemperature(0)
            self.toolTempSpinBox.setProperty("value", 0)
            self.bedTempSpinBox.setProperty("value", 0)
        except Exception as e:
            logger.error("Error in MainUiClass.coolDownAction: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.coolDownAction: {}".format(e), overlay=True)

    ''' +++++++++++++++++++++++++++++++++++Calibration++++++++++++++++++++++++++++++++ '''

    def inputShaperCalibrate(self):
        logger.info("MainUiClass.inputShaperCalibrate started")
        try:
            dialog.WarningOk(self, "Wait for all calibration movements to finish before proceeding.", overlay=True)
            octopiclient.gcode(command='G28')
            octopiclient.gcode(command='SHAPER_CALIBRATE')
            octopiclient.gcode(command='SAVE_CONFIG')

        except Exception as e:
            error_message = f"Error in inptuShaperCalibrate: {str(e)}"
            logger.error(error_message)
            dialog.WarningOk(self, error_message, overlay=True)

    def setZToolOffset(self, offset):
        """
        Sets the home offset after the caliberation wizard is done, which is a callback to
        the response of M114 that is sent at the end of the Wizard in doneStep()
        :param offset: the value off the offset to set. is a str is coming from M114, and is float if coming from the nozzleOffsetPage
        :return:

        #TODO can make this simpler, asset the offset value to string float to begin with instead of doing confitionals
        """
        logger.info("MainUiClass.setZToolOffset started")
        self.currentZPosition = offset #gets the current z position, used to set new tool offsets.
        try:
            if self.setNewToolZOffsetFromCurrentZBool:
                print(self.toolOffsetZ)
                print(self.currentZPosition)
                newToolOffsetZ = (float(self.toolOffsetZ) + float(self.currentZPosition))
                octopiclient.gcode(command='M218 T1 Z{}'.format(newToolOffsetZ))  # restore eeprom settings to get Z home offset, mesh bed leveling back
                self.setNewToolZOffsetFromCurrentZBool =False
                octopiclient.gcode(command='SAVE_CONFIG')  # store eeprom settings to get Z home offset
        except Exception as e:
            logger.error("Error in MainUiClass.setZToolOffset: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.setZToolOffset: {}".format(e), overlay=True)

    def showProbingFailed(self,msg='Probing Failed, Calibrate bed again or check for hardware issue',overlay=True):
        logger.info("MainUiClass.showProbingFailed started")
        try:
            if dialog.WarningOk(self, msg, overlay=overlay):
                octopiclient.cancelPrint()
                return True
            return False
        except Exception as e:
            logger.error("Error in MainUiClass.showProbingFailed: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.showProbingFailed: {}".format(e), overlay=True)

    def showPrinterError(self, msg='Printer error, Check Terminal', overlay=False):
        logger.info("MainUiClass.showPrinterError started")
        try:
            if any(error in msg for error in
                   ["Can not update MCU","Error loading template", "Must home axis first", "probe", "Error during homing move", "still triggered after retract", "'mcu' must be specified"]):
                logger.error("CRITICAL ERROR SHUTDOWN NEEDED")
                if self.printerStatusText in ["Starting","Printing","Paused"]:
                    octopiclient.cancelPrint()
                    octopiclient.gcode(command='M112')
                    try:
                        octopiclient.connectPrinter(port="/tmp/printer", baudrate=115200)
                    except Exception as e:
                        octopiclient.connectPrinter(port="VIRTUAL", baudrate=115200)
                    octopiclient.gcode(command='FIRMWARE_RESTART')
                    octopiclient.gcode(command='RESTART')
                    if not self.dialogShown:
                        self.dialogShown = True
                        if dialog.WarningOk(self, msg + ", Cancelling Print.", overlay=overlay):
                            self.dialogShown = False
                    logger.error("CRITICAL ERROR SHUTDOWN DONE")
                else:
                    if not self.dialogShown:
                        self.dialogShown = True
                        octopiclient.gcode(command='FIRMWARE_RESTART')
                        octopiclient.gcode(command='RESTART')
                        if dialog.WarningOk(self, msg, overlay=overlay):
                            self.dialogShown = False

            else:
                if not self.dialogShown:
                    self.dialogShown = True
                    if dialog.WarningOk(self, msg, overlay=overlay):
                        self.dialogShown = False

        except Exception as e:
            logger.error("Error in MainUiClass.showPrinterError: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.showPrinterError: {}".format(e), overlay=True)
    def updateEEPROMProbeOffset(self, offset):
        """
        Sets the spinbox value to have the value of the Z offset from the printer.
        the value is -ve so as to be more intuitive.
        :param offset:
        :return:
        """
        logger.info("MainUiClass.updateEEPROMProbeOffset started")
        try:
            self.currentNozzleOffset.setText(str(float(offset)))
            self.nozzleOffsetDoubleSpinBox.setValue(0)
        except Exception as e:
            logger.error("Error in MainUiClass.updateEEPROMProbeOffset: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.updateEEPROMProbeOffset: {}".format(e), overlay=True)


    def setZProbeOffset(self, offset):
        """
        Sets Z Probe offset from spinbox

        #TODO can make this simpler, asset the offset value to string float to begin with instead of doing confitionals
        """
        logger.info("MainUiClass.setZProbeOffset started")
        try:
            octopiclient.gcode(command='M851 Z{}'.format(round(float(offset),2))) #M851 only ajusts nozzle offset
            self.nozzleOffsetDoubleSpinBox.setValue(0)
            _offset=float(self.currentNozzleOffset.text())+float(offset)
            self.currentNozzleOffset.setText(str(float(self.currentNozzleOffset.text())-float(offset))) # show nozzle offset after adjustment
            octopiclient.gcode(command='M500')
        except Exception as e:
            logger.error("Error in MainUiClass.setZProbeOffset: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.setZProbeOffset: {}".format(e), overlay=True)

    def requestEEPROMProbeOffset(self):
        """
        Updates the value of M206 Z in the nozzle offset spinbox. Sends M503 so that the pritner returns the value as a websocket calback
        :return:
        """
        logger.info("MainUiClass.requestEEPROMProbeOffset started")
        try:
            octopiclient.gcode(command='M503')
            self.stackedWidget.setCurrentWidget(self.nozzleOffsetPage)
        except Exception as e:
            logger.error("Error in MainUiClass.requestEEPROMProbeOffset: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.requestEEPROMProbeOffset: {}".format(e), overlay=True)

    def nozzleOffset(self):
        """
        Updates the value of M206 Z in the nozzle offset spinbox. Sends M503 so that the pritner returns the value as a websocket calback
        :return:
        """
        logger.info("MainUiClass.nozzleOffset started")
        try:
            octopiclient.gcode(command='M503')
            self.stackedWidget.setCurrentWidget(self.nozzleOffsetPage)
        except Exception as e:
            logger.error("Error in MainUiClass.nozzleOffset: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.nozzleOffset: {}".format(e), overlay=True)

    def updateToolOffsetXY(self):
        logger.info("MainUiClass.updateToolOffsetXY started")
        try:
            octopiclient.gcode(command='M503')
            self.stackedWidget.setCurrentWidget(self.toolOffsetXYPage)
        except Exception as e:
            logger.error("Error in MainUiClass.updateToolOffsetXY: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.updateToolOffsetXY: {}".format(e), overlay=True)

    def updateToolOffsetZ(self):
        logger.info("MainUiClass.updateToolOffsetZ started")
        try:
            octopiclient.gcode(command='M503')
            self.stackedWidget.setCurrentWidget(self.toolOffsetZpage)
        except Exception as e:
            logger.error("Error in MainUiClass.updateToolOffsetZ: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.updateToolOffsetZ: {}".format(e), overlay=True)

    def setToolOffsetX(self):
        logger.info("MainUiClass.setToolOffsetX started")
        try:
            octopiclient.gcode(command='M218 T1 X{}'.format(round(self.toolOffsetXDoubleSpinBox.value(),2)))  # restore eeprom settings to get Z home offset, mesh bed leveling back
            octopiclient.gcode(command='M500')
        except Exception as e:
            logger.error("Error in MainUiClass.setToolOffsetX: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.setToolOffsetX: {}".format(e), overlay=True)

    def setToolOffsetY(self):
        logger.info("MainUiClass.setToolOffsetY started")
        try:
            octopiclient.gcode(command='M218 T1 Y{}'.format(round(self.toolOffsetYDoubleSpinBox.value(),2)))  # restore eeprom settings to get Z home offset, mesh bed leveling back
            octopiclient.gcode(command='M500')
            octopiclient.gcode(command='M500')
        except Exception as e:
            logger.error("Error in MainUiClass.setToolOffsetY: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.setToolOffsetY: {}".format(e), overlay=True)

    def setToolOffsetZ(self):
        logger.info("MainUiClass.setToolOffsetZ started")
        try:
            octopiclient.gcode(command='M218 T1 Z{}'.format(round(self.toolOffsetZDoubleSpinBox.value(),2)))  # restore eeprom settings to get Z home offset, mesh bed leveling back
            octopiclient.gcode(command='M500')
        except Exception as e:
            logger.error("Error in MainUiClass.setToolOffsetZ: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.setToolOffsetZ: {}".format(e), overlay=True)

    def getToolOffset(self, M218Data):
        logger.info("MainUiClass.getToolOffset started")
        try:
            #if float(M218Data[M218Data.index('X') + 1:].split(' ', 1)[0] ) > 0:
            self.toolOffsetZ = M218Data[M218Data.index('Z') + 1:].split(' ', 1)[0]
            self.toolOffsetX = M218Data[M218Data.index('X') + 1:].split(' ', 1)[0]
            self.toolOffsetY = M218Data[M218Data.index('Y') + 1:].split(' ', 1)[0]
            self.toolOffsetXDoubleSpinBox.setValue(float(self.toolOffsetX))
            self.toolOffsetYDoubleSpinBox.setValue(float(self.toolOffsetY))
            self.toolOffsetZDoubleSpinBox.setValue(float(self.toolOffsetZ))
            self.idexToolOffsetRestoreValue = float(self.toolOffsetZ)
        except Exception as e:
            logger.error("Error in MainUiClass.getToolOffset: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.getToolOffset: {}".format(e), overlay=True)

    def quickStep1(self):
        """
        Shows welcome message.
        Homes to MAX
        goes to position where leveling screws can be opened
        :return:
        """
        logger.info("MainUiClass.quickStep1 started")
        try:
            self.toolZOffsetCaliberationPageCount = 0
            octopiclient.gcode(command='M104 S200')
            octopiclient.gcode(command='M104 T1 S200')
            #octopiclient.gcode(command='M211 S0')  # Disable software endstop
            octopiclient.gcode(command='T0')  # Set active tool to t0
            octopiclient.gcode(command='M503')  # makes sure internal value of Z offset and Tool offsets are stored before erasing
            octopiclient.gcode(command='M420 S0')  # Dissable mesh bed leveling for good measure
            self.stackedWidget.setCurrentWidget(self.quickStep1Page)
            octopiclient.home(['x', 'y', 'z'])
            octopiclient.gcode(command='T0')
            octopiclient.jog(x=40, y=40, absolute=True, speed=2000)
        except Exception as e:
            logger.error("Error in MainUiClass.quickStep1: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.quickStep1: {}".format(e), overlay=True)
    def quickStep2(self):
        """
        levels first position (RIGHT)
        :return:
        """
        logger.info("MainUiClass.quickStep2 started")
        try:
            self.stackedWidget.setCurrentWidget(self.quickStep2Page)
            octopiclient.jog(x=calibrationPosition['X1'], y=calibrationPosition['Y1'], absolute=True, speed=10000)
            octopiclient.jog(z=0, absolute=True, speed=1500)
            self.movie1 = QtGui.QMovie("templates/img/Calibration/CalibrationPoint1.gif")
            self.CalibrationPoint1.setMovie(self.movie1)
            self.movie1.start()
        except Exception as e:
            logger.error("Error in MainUiClass.quickStep2: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.quickStep2: {}".format(e), overlay=True)
            try:
                self.movie1.stop()
            except:
                pass

    def quickStep3(self):
        """
        levels second leveling position (LEFT)
        """
        logger.info("MainUiClass.quickStep3 started")
        try:
            self.stackedWidget.setCurrentWidget(self.quickStep3Page)
            octopiclient.jog(z=10, absolute=True, speed=1500)
            octopiclient.jog(x=calibrationPosition['X2'], y=calibrationPosition['Y2'], absolute=True, speed=10000)
            octopiclient.jog(z=0, absolute=True, speed=1500)
            self.movie1.stop()
            self.movie2 = QtGui.QMovie("templates/img/Calibration/CalibrationPoint2.gif")
            self.CalibrationPoint2.setMovie(self.movie2)
            self.movie2.start()
        except Exception as e:
            logger.error("Error in MainUiClass.quickStep3: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.quickStep3: {}".format(e), overlay=True)
            try:
                self.movie1.stop()
                self.movie2.stop()
            except:
                pass

    def quickStep4(self):
        """
        levels third leveling position  (BACK)
        :return:
        """
        logger.info("MainUiClass.quickStep4 started")
        try:
            # sent twice for some reason
            self.stackedWidget.setCurrentWidget(self.quickStep4Page)
            octopiclient.jog(z=10, absolute=True, speed=1500)
            octopiclient.jog(x=calibrationPosition['X3'], y=calibrationPosition['Y3'], absolute=True, speed=10000)
            octopiclient.jog(z=0, absolute=True, speed=1500)
            self.movie2.stop()
            self.movie3 = QtGui.QMovie("templates/img/Calibration/CalibrationPoint3.gif")
            self.CalibrationPoint3.setMovie(self.movie3)
            self.movie3.start()
        except Exception as e:
            logger.error("Error in MainUiClass.quickStep4: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.quickStep4: {}".format(e), overlay=True)
            try:
                self.movie2.stop()
                self.movie3.stop()
            except:
                pass


    def nozzleHeightStep1(self):
        logger.info("MainUiClass.nozzleHeightStep1 started")
        try:
            self.movie3.stop()
            if self.toolZOffsetCaliberationPageCount == 0 :
                self.toolZOffsetLabel.setText("Move the bed up or down to the First Nozzle , testing height using paper")
                self.stackedWidget.setCurrentWidget(self.nozzleHeightStep1Page)
                octopiclient.jog(z=10, absolute=True, speed=1500)
                octopiclient.jog(x=calibrationPosition['X4'], y=calibrationPosition['Y4'], absolute=True, speed=10000)
                octopiclient.jog(z=1, absolute=True, speed=1500)
                self.toolZOffsetCaliberationPageCount = 1
            elif self.toolZOffsetCaliberationPageCount == 1:
                self.toolZOffsetLabel.setText("Move the bed up or down to the Second Nozzle , testing height using paper")
                octopiclient.gcode(command='G92 Z0')#set the current Z position to zero
                octopiclient.jog(z=1, absolute=True, speed=1500)
                octopiclient.gcode(command='T1')
                octopiclient.jog(x=calibrationPosition['X4'], y=calibrationPosition['Y4'], absolute=True, speed=10000)
                self.toolZOffsetCaliberationPageCount = 2
            else:
                self.doneStep()
        except Exception as e:
            logger.error("Error in MainUiClass.nozzleHeightStep1: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.nozzleHeightStep1: {}".format(e), overlay=True)
            try:
                self.movie1.stop()
                self.movie2.stop()
                self.movie3.stop()
            except:
                pass

    def doneStep(self):
        """
        Exits leveling
        :return:
        """
        logger.info("MainUiClass.doneStep started")
        try:
            self.setNewToolZOffsetFromCurrentZBool = True
            octopiclient.gcode(command='M114')
            octopiclient.jog(z=4, absolute=True, speed=1500)
            octopiclient.gcode(command='T0')
            #octopiclient.gcode(command='M211 S1')  # Disable software endstop
            self.stackedWidget.setCurrentWidget(self.calibratePage)
            octopiclient.home(['x', 'y', 'z'])
            octopiclient.gcode(command='M104 S0')
            octopiclient.gcode(command='M104 T1 S0')
            octopiclient.gcode(command='M84')
            octopiclient.gcode(command='M500')  # store eeprom settings to get Z home offset, mesh bed leveling back
        except Exception as e:
            logger.error("Error in MainUiClass.doneStep: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.doneStep: {}".format(e), overlay=True)
            try:
                self.movie1.stop()
                self.movie2.stop()
                self.movie3.stop()
            except:
                pass

    def cancelStep(self):
        logger.info("MainUiClass.cancelStep started")
        try:
            self.stackedWidget.setCurrentWidget(self.calibratePage)
            octopiclient.home(['x', 'y', 'z'])
            octopiclient.gcode(command='M104 S0')
            octopiclient.gcode(command='M104 T1 S0')
            octopiclient.gcode(command='M84')
            try:
                self.movie1.stop()
                self.movie2.stop()
                self.movie3.stop()
            except:
                pass
        except Exception as e:
            logger.error("Error in MainUiClass.cancelStep: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.cancelStep: {}".format(e), overlay=True)
            try:
                self.movie1.stop()
                self.movie2.stop()
                self.movie3.stop()
            except:
                pass

    
    def testPrint(self,tool0Diameter,tool1Diameter,gcode):
        """
        Prints a test print
        :param tool0Diameter: Diameter of tool 0 nozzle.04,06 or 08
        :param tool1Diameter: Diameter of tool 1 nozzle.40,06 or 08
        :param gcode: type of gcode to print, dual nozzle calibration, bed leveling, movement or samaple prints in
        single and dual. bedLevel, dualCalibration, movementTest, dualTest, singleTest
        :return:
        """
        logger.info("MainUiClass.testPrint started")
        try:
            if gcode is 'bedLevel':
                self.printFromPath('gcode/' + tool0Diameter + '_BedLeveling.gcode', True)
            elif gcode is 'dualCalibration':
                self.printFromPath(
                    'gcode/' + tool0Diameter + '_' + tool1Diameter + '_dual_extruder_calibration_Idex.gcode',
                    True)
            elif gcode is 'movementTest':
                self.printFromPath('gcode/movementTest.gcode', True)
            elif gcode is 'dualTest':
                self.printFromPath(
                    'gcode/' + tool0Diameter + '_' + tool1Diameter + '_Fracktal_logo_Idex.gcode',
                    True)
            elif gcode is 'singleTest':
                self.printFromPath('gcode/' + tool0Diameter + '_Fracktal_logo_Idex.gcode',True)

            else:
                print("gcode not found")
        except Exception as e:
            logger.error("Error in MainUiClass.testPrint: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.testPrint: {}".format(e), overlay=True)
    def printFromPath(self,path,prnt=True):
        """
        Transfers a file from a specific to octoprint's watched folder so that it gets automatically detected by Octoprint.
        Warning: If the file is read-only, octoprint API for reading the file crashes.
        """
        logger.info("MainUiClass.printFromPath started")
        try:
            self.uploadThread = ThreadFileUpload(path, prnt=prnt)
            self.uploadThread.start()
            if prnt:
                self.stackedWidget.setCurrentWidget(self.homePage)
        except Exception as e:
            logger.error("Error in MainUiClass.printFromPath: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.printFromPath: {}".format(e), overlay=True)


    ''' +++++++++++++++++++++++++++++++++++IDEX Config++++++++++++++++++++++++++++++++ '''


    def idexConfigStep1(self):
        """
        Shows welcome message.
        Welcome Page, Give Info. Unlock nozzle and push down
        :return:
        """
        logger.info("MainUiClass.idexConfigStep1 started")
        try:
            octopiclient.gcode(command='M503')  # Gets old tool offset position
            octopiclient.gcode(command='M218 T1 Z0')  # set nozzle tool offsets to 0
            octopiclient.gcode(command='M104 S200')
            octopiclient.gcode(command='M104 T1 S200')
            octopiclient.home(['x', 'y', 'z'])
            octopiclient.gcode(command='G1 X10 Y10 Z20 F5000')
            octopiclient.gcode(command='T0')  # Set active tool to t0
            octopiclient.gcode(command='M420 S0')  # Dissable mesh bed leveling for good measure
            self.stackedWidget.setCurrentWidget(self.idexConfigStep1Page)
            self.movie5 = QtGui.QMovie("templates/img/Calibration/Nozzlelevel1.gif")
            self.Nozzlelevel1.setMovie(self.movie5)
            self.movie5.start()
        except Exception as e:
            logger.error("Error in MainUiClass.idexConfigStep1: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.idexConfigStep1: {}".format(e), overlay=True)
            try:
                self.movie5.stop()
            except:
                pass

    def idexConfigStep2(self):
        """
        levels first position (RIGHT)
        :return:
        """
        logger.info("MainUiClass.idexConfigStep2 started")
        try:
            self.stackedWidget.setCurrentWidget(self.idexConfigStep2Page)
            octopiclient.jog(x=calibrationPosition['X1'], y=calibrationPosition['Y1'], absolute=True, speed=10000)
            octopiclient.jog(z=0, absolute=True, speed=1500)
            self.movie5.stop()
            self.movie6 = QtGui.QMovie("templates/img/Calibration/CalibrationPoint1.gif")
            self.CalibrationPoint1_2.setMovie(self.movie6)
            self.movie6.start()
        except Exception as e:
            logger.error("Error in MainUiClass.idexConfigStep2: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.idexConfigStep2: {}".format(e), overlay=True)
            try:
                self.movie5.stop()
                self.movie6.stop()
            except:
                pass


    def idexConfigStep3(self):
        """
        levels second leveling position (LEFT)
        """
        logger.info("MainUiClass.idexConfigStep3 started")
        try:
            self.stackedWidget.setCurrentWidget(self.idexConfigStep3Page)
            octopiclient.jog(z=10, absolute=True, speed=1500)
            octopiclient.jog(x=calibrationPosition['X2'], y=calibrationPosition['Y2'], absolute=True, speed=10000)
            octopiclient.jog(z=0, absolute=True, speed=1500)
            self.movie6.stop()
            self.movie7 = QtGui.QMovie("templates/img/Calibration/CalibrationPoint2.gif")
            self.CalibrationPoint2_2.setMovie(self.movie7)
            self.movie7.start()
        except Exception as e:
            logger.error("Error in MainUiClass.idexConfigStep3: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.idexConfigStep3: {}".format(e), overlay=True)
            try:
                self.movie6.stop()
                self.movie7.stop()
            except:
                pass

    def idexConfigStep4(self):
        """
        Set to Mirror mode and asks to loosen the carriage, push both doen to max
        :return:
        """
        logger.info("MainUiClass.idexConfigStep4 started")
        try:
            self.stackedWidget.setCurrentWidget(self.idexConfigStep4Page)
            octopiclient.jog(z=10, absolute=True, speed=1500)
            octopiclient.gcode(command='M605 S3')
            octopiclient.jog(x=calibrationPosition['X1'], y=calibrationPosition['Y1'], absolute=True, speed=10000)
            self.movie7.stop()
            self.movie8 = QtGui.QMovie("templates/img/Calibration/NozzleLevelNew1.gif")
            self.Nozzlelevel1_2.setMovie(self.movie8)
            self.movie8.start()
        except Exception as e:
            logger.error("Error in MainUiClass.idexConfigStep4: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.idexConfigStep4: {}".format(e), overlay=True)
            try:
                self.movie7.stop()
                self.movie8.stop()
            except:
                pass


    def idexConfigStep5(self):
        """
        take bed up until both nozzles touch the bed. ASk to take nozzle up and down till nozzle just rests on the bed and tighten
        :return:
        """
        logger.info("MainUiClass.idexConfigStep5 started")
        try:
            self.stackedWidget.setCurrentWidget(self.idexConfigStep5Page)
            octopiclient.jog(z=1, absolute=True, speed=10000)
            self.movie8.stop()
            self.movie9 = QtGui.QMovie("templates/img/Calibration/NozzlelevelNew2.gif")
            self.Nozzlelevel2.setMovie(self.movie9)
            self.movie9.start()
        except Exception as e:
            logger.error("Error in MainUiClass.idexConfigStep5: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.idexConfigStep5: {}".format(e), overlay=True)
            try:
                self.movie8.stop()
                self.movie9.stop()
            except:
                pass



    def idexDoneStep(self):
        """
        Exits leveling
        :return:
        """
        logger.info("MainUiClass.idexDoneStep started")
        try:
            octopiclient.jog(z=4, absolute=True, speed=1500)
            self.stackedWidget.setCurrentWidget(self.calibratePage)
            self.movie9.stop()
            octopiclient.home(['z'])
            octopiclient.home(['x', 'y'])
            octopiclient.gcode(command='M104 S0')
            octopiclient.gcode(command='M104 T1 S0')
            octopiclient.gcode(command='M605 S1')
            octopiclient.gcode(command='M218 T1 Z0') #set nozzle offsets to 0
            octopiclient.gcode(command='M84')
            octopiclient.gcode(command='M500')  # store eeprom settings to get Z home offset, mesh bed leveling back
        except Exception as e:
            logger.error("Error in MainUiClass.idexDoneStep: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.idexDoneStep: {}".format(e), overlay=True)
            try:
                self.movie9.stop()
            except:
                pass

    def idexCancelStep(self):
        logger.info("MainUiClass.idexCancelStep started")
        try:
            self.stackedWidget.setCurrentWidget(self.calibratePage)
            try:
                self.movie5.stop()
                self.movie6.stop()
                self.movie7.stop()
                self.movie8.stop()
                self.movie9.stop()
            except:
                pass
            octopiclient.gcode(command='M605 S1')
            octopiclient.home(['z'])
            octopiclient.home(['x', 'y'])
            octopiclient.gcode(command='M104 S0')
            octopiclient.gcode(command='M104 T1 S0')
            octopiclient.gcode(command='M218 T1 Z{}'.format(self.idexToolOffsetRestoreValue))
            octopiclient.gcode(command='M84')
        except Exception as e:
            logger.error("Error in MainUiClass.idexCancelStep: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.idexCancelStep: {}".format(e), overlay=True)


    ''' +++++++++++++++++++++++++++++++++++Keyboard++++++++++++++++++++++++++++++++ '''

    def startKeyboard(self, returnFn, onlyNumeric=False, noSpace=False, text=""):
        """
        starts the keyboard screen for entering Password
        """
        logger.info("MainUiClass.startKeyboard started")
        try:
            keyBoardobj = keyboard.Keyboard(onlyNumeric=onlyNumeric, noSpace=noSpace, text=text)
            keyBoardobj.keyboard_signal.connect(returnFn)
            keyBoardobj.setWindowFlags(QtCore.Qt.FramelessWindowHint)
            keyBoardobj.show()
        except Exception as e:
            logger.error("Error in MainUiClass.startKeyboard: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.startKeyboard: {}".format(e), overlay=True)

    ''' ++++++++++++++++++++++++++++++Restore Defaults++++++++++++++++++++++++++++ '''

    def restoreFactoryDefaults(self):
        logger.info("MainUiClass.restoreFactoryDefaults started")
        try:
            if dialog.WarningYesNo(self, "Are you sure you want to restore machine state to factory defaults?\nWarning: Doing so will also reset printer profiles, WiFi & Ethernet config.",
                                   overlay=True):
                os.system('sudo cp -f config/dhcpcd.conf /etc/dhcpcd.conf')
                os.system('sudo cp -f config/wpa_supplicant.conf /etc/wpa_supplicant/wpa_supplicant.conf')
                os.system('sudo rm -rf /home/pi/.octoprint/users.yaml')
                os.system('sudo cp -f config/users.yaml /home/pi/.octoprint/users.yaml')
                os.system('sudo rm -rf /home/pi/.octoprint/printerProfiles/*')
                os.system('sudo rm -rf /home/pi/.octoprint/scripts/gcode')
                os.system('sudo rm -rf /home/pi/.octoprint/print_restore.json')
                os.system('sudo cp -f config/config.yaml /home/pi/.octoprint/config.yaml')
                self.tellAndReboot("Settings restored. Rebooting...")
        except Exception as e:
            logger.error("Error in MainUiClass.restoreFactoryDefaults: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.restoreFactoryDefaults: {}".format(e), overlay=True)

    def restorePrintDefaults(self):
        logger.info("MainUiClass.restorePrintDefaults started")
        try:
            if dialog.WarningYesNo(self, "Are you sure you want to restore default print settings?\nWarning: Doing so will erase offsets and bed leveling info",
                                   overlay=True):
                os.system('sudo cp -f firmware/COMMON_FILAMENT_SENSOR.cfg /home/pi/COMMON_FILAMENT_SENSOR.cfg')
                os.system('sudo cp -f firmware/COMMON_GCODE_MACROS.cfg /home/pi/COMMON_GCODE_MACROS.cfg')
                os.system('sudo cp -f firmware/COMMON_IDEX.cfg /home/pi/COMMON_IDEX.cfg')
                os.system('sudo cp -f firmware/COMMON_MOTHERBOARD.cfg /home/pi/COMMON_MOTHERBOARD.cfg')
                os.system('sudo cp -f firmware/PRINTERS_TWINDRAGON_600x300.cfg /home/pi/PRINTERS_TWINDRAGON_600x300.cfg')
                os.system('sudo cp -f firmware/PRINTERS_TWINDRAGON_600x600.cfg /home/pi/PRINTERS_TWINDRAGON_600x600.cfg')
                os.system('sudo cp -f firmware/TOOLHEADS_TD-01_TOOLHEAD0.cfg /home/pi/TOOLHEADS_TD-01_TOOLHEAD0.cfg')
                os.system('sudo cp -f firmware/TOOLHEADS_TD-01_TOOLHEAD1.cfg /home/pi/TOOLHEADS_TD-01_TOOLHEAD1.cfg')
                os.system('sudo cp -f firmware/variables.cfg /home/pi/variables.cfg')
                #TODO: check printer variant setting and modify printer.cfg accordingly
                octopiclient.gcode(command='M502')
                octopiclient.gcode(command='M500')
                octopiclient.gcode(command='FIRMWARE_RESTART')
                octopiclient.gcode(command='RESTART')
        except Exception as e:
            logger.error("Error in MainUiClass.restorePrintDefaults: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.restorePrintDefaults: {}".format(e), overlay=True)

    ''' +++++++++++++++++++++++++++++++++++ Misc ++++++++++++++++++++++++++++++++ '''

    def tellAndReboot(self, msg="Rebooting...", overlay=True):
        if dialog.WarningOk(self, msg, overlay=overlay):
            os.system('sudo reboot now')
            return True
        return False

    def askAndReboot(self, msg="Are you sure you want to reboot?", overlay=True):
        if dialog.WarningYesNo(self, msg, overlay=overlay):
            os.system('sudo reboot now')
            return True
        return False

    def checkKlipperPrinterCFG(self):
        """
        Checks for valid printer.cfg and restores if needed
        """

        # Open the printer.cfg file:
        logger.info("MainUiClass.checkKlipperPrinterCFG started")
        try:
            try:
                with open('/home/pi/printer.cfg', 'r') as currentConfigFile:
                    currentConfig = currentConfigFile.read()
                    if "# MCU Config" in currentConfig:
                        configCorruptedFlag = False
                        logger.info("Printer Config File OK")
                    else:
                        configCorruptedFlag = True
                        logger.error("Printer Config File Corrupted, Attempting to restore Backup")

            except:
                configCorruptedFlag = True
                logger.error("Printer Config File Not Found, Attempting to restore Backup")

            if configCorruptedFlag:
                backupFiles = sorted(glob.glob('/home/pi/printer-*.cfg'), key=os.path.getmtime, reverse=True)
                print("\n".join(backupFiles))
                for backupFile in backupFiles:
                    with open(str(backupFile), 'r') as backupConfigFile:
                        backupConfig = backupConfigFile.read()
                        if "# MCU Config" in backupConfig:
                            try:
                                os.remove('/home/pi/printer.cfg')
                            except:
                                logger.error("printer.cfg does not exist for deletion")
                            try:
                                os.rename(backupFile, '/home/pi/printer.cfg')
                                logger.info("Printer Config File Restored")
                                return()
                            except:
                                pass
                # If no valid backups found, show error dialog:
                dialog.WarningOk(self, "Printer Config File corrupted. Contact Fracktal support or raise a ticket at care.fracktal.in")
                if self.printerStatus == "Printing":
                    octopiclient.cancelPrint()
                    self.coolDownAction()
            elif not configCorruptedFlag:
                backupFiles = sorted(glob.glob('/home/pi/printer-*.cfg'), key=os.path.getmtime, reverse=True)
                try:
                    for backupFile in backupFiles[5:]:
                        os.remove(backupFile)
                except:
                    pass
        except Exception as e:
            logger.error("Error in MainUiClass.checkKlipperPrinterCFG: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.checkKlipperPrinterCFG: {}".format(e), overlay=True)

    def pairPhoneApp(self):
        logger.info("MainUiClass.pairPhoneApp started")
        try:
            if getIP(ThreadRestartNetworking.ETH) is not None:
                qrip = getIP(ThreadRestartNetworking.ETH)
            elif getIP(ThreadRestartNetworking.WLAN) is not None:
                qrip = getIP(ThreadRestartNetworking.WLAN)
            else:
                if dialog.WarningOk(self, "Network Disconnected"):
                    return
            self.QRCodeLabel.setPixmap(
                qrcode.make("http://"+ qrip, image_factory=Image).pixmap())
            self.stackedWidget.setCurrentWidget(self.QRCodePage)
        except Exception as e:
            logger.error("Error in MainUiClass.pairPhoneApp: {}".format(e))
            dialog.WarningOk(self, "Error in MainUiClass.pairPhoneApp: {}".format(e), overlay=True)

class QtWebsocket(QtCore.QThread):
    """
    https://pypi.python.org/pypi/websocket-client
    https://wiki.python.org/moin/PyQt/Threading,_Signals_and_Slots
    """

    z_home_offset_signal = QtCore.pyqtSignal(str)
    temperatures_signal = QtCore.pyqtSignal(dict)
    status_signal = QtCore.pyqtSignal(str)
    print_status_signal = QtCore.pyqtSignal('PyQt_PyObject')
    update_started_signal = QtCore.pyqtSignal(dict)
    update_log_signal = QtCore.pyqtSignal(dict)
    update_log_result_signal = QtCore.pyqtSignal(dict)
    update_failed_signal = QtCore.pyqtSignal(dict)
    connected_signal = QtCore.pyqtSignal()
    filament_sensor_triggered_signal = QtCore.pyqtSignal(str)
    firmware_updater_signal = QtCore.pyqtSignal(dict)
    set_z_tool_offset_signal = QtCore.pyqtSignal(str,bool)
    tool_offset_signal = QtCore.pyqtSignal(str)
    active_extruder_signal = QtCore.pyqtSignal(str)
    z_probe_offset_signal = QtCore.pyqtSignal(str)
    z_probing_failed_signal = QtCore.pyqtSignal()
    printer_error_signal = QtCore.pyqtSignal(str)

    def __init__(self):
        logger.info("QtWebsocket started")
        super(QtWebsocket, self).__init__()
        self.ws = None
        self.heartbeat_timer = None
        try:
            url = "ws://{}/sockjs/{:0>3d}/{}/websocket".format(
                ip,  # host + port + prefix, but no protocol
                random.randrange(0, stop=999),  # server_id
                uuid.uuid4()  # session_id
            )

            self.ws = websocket.WebSocketApp(url,
                                             on_message=self.on_message,
                                             on_error=self.on_error,
                                             on_close=self.on_close,
                                             on_open=self.on_open)
        except Exception as e:
            logger.error("Error in QtWebsocket: {}".format(e))

    def run(self):
        logger.info("QtWebsocket.run started")
        try:
            self.ws.run_forever()
            self.reset_heartbeat_timer()
        except Exception as e:
            logger.error("Error in QtWebsocket.run: {}".format(e))
    def reset_heartbeat_timer(self):
        try:
            if self.heartbeat_timer is not None:
                self.heartbeat_timer.cancel()

            self.heartbeat_timer = threading.Timer(120, self.reestablish_connection)  # 120 seconds = 2 minutes
            self.heartbeat_timer.start()
        except Exception as e:
            logger.error("Error in QtWebsocket.reset_heartbeat_timer: {}".format(e))
    def reestablish_connection(self):
        logger.info("QtWebsocket.reestablish_connection started")
        try:
            self.__init__()
            self.start()
        except Exception as e:
            logger.error("Error in QtWebsocket.reestablish_connection: {}".format(e))
    def send(self, data):
        logger.info("QtWebsocket.send started")
        try:
            payload = '["' + json.dumps(data).replace('"', '\\"') + '"]'
            self.ws.send(payload)
        except Exception as e:
            logger.error("Error in QtWebsocket.send: {}".format(e))
            dialog.WarningOk(self, "Error in QtWebsocket.send: {}".format(e), overlay=True)

    def authenticate(self):
        logger.info("QtWebsocket.authenticate started")
        try:
            # perform passive login to retrieve username and session key for API key
            url = 'http://' + ip + '/api/login'
            headers = {'content-type': 'application/json', 'X-Api-Key': apiKey}
            payload = {"passive": True}
            response = requests.post(url, data=json.dumps(payload), headers=headers)
            data = response.json()

            # prepare auth payload
            auth_message = {"auth": "{name}:{session}".format(**data)}

            # send it
            self.send(auth_message)
        except Exception as e:
            logger.error("Error in QtWebsocket.authenticate: {}".format(e))

    def on_message(self, ws, message):
        message_type = message[0]
        if message_type == "h":
            # "heartbeat" message
            self.reset_heartbeat_timer()
            return
        elif message_type == "o":
            # "open" message
            return
        elif message_type == "c":
            # "close" message
            return

        message_body = message[1:]
        if not message_body:
            return
        data = json.loads(message_body)[0]

        if message_type == "m":
            data = [data, ]

        if message_type == "a":
            self.process(data)

    def on_open(self,ws):
        self.authenticate()

    def on_close(self, ws):
        pass

    def on_error(self, ws, error):
        logger.error("Error in QtWebsocket: {}".format(error))

    @run_async
    def process(self, data):
        try:
            if "event" in data:
                if data["event"]["type"] == "Connected":
                    self.connected_signal.emit()
                    print("connected")
            if "plugin" in data:
                # if data["plugin"]["plugin"] == 'Julia2018FilamentSensor':
                #      self.filament_sensor_triggered_signal.emit(data["plugin"]["data"])

                if data["plugin"]["plugin"] == 'JuliaFirmwareUpdater':
                    self.firmware_updater_signal.emit(data["plugin"]["data"])

                elif data["plugin"]["plugin"] == 'softwareupdate':
                    if data["plugin"]["data"]["type"] == "updating":
                        self.update_started_signal.emit(data["plugin"]["data"]["data"])
                    elif data["plugin"]["data"]["type"] == "loglines":
                        self.update_log_signal.emit(data["plugin"]["data"]["data"]["loglines"])
                    elif data["plugin"]["data"]["type"] == "restarting":
                        self.update_log_result_signal.emit(data["plugin"]["data"]["data"]["results"])
                    elif data["plugin"]["data"]["type"] == "update_failed":
                        self.update_failed_signal.emit(data["plugin"]["data"]["data"])

            if "current" in data:
                if data["current"]["messages"]:
                    for item in data["current"]["messages"]:
                        if 'Filament Runout or clogged' in item: # "Filament Runout on T0/T1"
                            self.filament_sensor_triggered_signal.emit(item[item.index('T') + 1:].split(' ', 1)[0])

                        if 'Primary FS Status' in item:
                            self.filament_sensor_triggered_signal.emit(item)

                        if 'M206' in item: #response to M503, send current Z offset value
                            self.z_home_offset_signal.emit(item[item.index('Z') + 1:].split(' ', 1)[0])
                        # if 'Count' in item:  # gets the current Z value, uses it to set Z offset
                        #     self.emit(QtCore.SIGNAL('SET_Z_HOME_OFFSET'), item[item.index('Z') + 2:].split(' ', 1)[0],
                        #               False)
                        if 'Count' in item:  # can get thris throught the positionUpdate event
                            self.set_z_tool_offset_signal.emit(item[item.index('z') + 2:].split(',', 1)[0],
                                      False)
                        if 'M218' in item:
                            self.tool_offset_signal.emit(item[item.index('M218'):])
                        if 'Active Extruder' in item:  # can get thris throught the positionUpdate event
                            self.active_extruder_signal.emit(item[-1])

                        if 'M851' in item:
                            self.z_probe_offset_signal.emit(item[item.index('Z') + 1:].split(' ', 1)[0])
                        if 'PROBING_FAILED' in item: #TODO: check if this is the correct error message
                            self.z_probing_failed_signal.emit()

                        for ignore_item in [
                            #"Error",
                            "!! Printer is not ready",
                            "!! Move out of range:",
                            "!! Shutdown due to M112"
                            # "ok",
                            # "B:",
                            # "N",
                            # "echo: "
                        ]:
                           if ignore_item in item:
                               # Ignore this item
                               break
                        else:
                           if item.startswith('!!') or item.startswith('Error'):
                               self.printer_error_signal.emit(item)
                               logger.error("Error From Klipper/Printer: {}".format(item))

                if data["current"]["state"]["text"]:
                    self.status_signal.emit(data["current"]["state"]["text"])

                fileInfo = {"job": data["current"]["job"], "progress": data["current"]["progress"]}
                if fileInfo['job']['file']['name'] is not None:
                    self.print_status_signal.emit(fileInfo)
                else:
                    self.print_status_signal.emit(None)

                def temp(data, tool, temp):
                    try:
                        if tool in data["current"]["temps"][0]:
                            return data["current"]["temps"][0][tool][temp]
                    except:
                        pass
                    return 0

                if data["current"]["temps"] and len(data["current"]["temps"]) > 0:
                    try:
                        temperatures = {'tool0Actual': temp(data, "tool0", "actual"),
                                        'tool0Target': temp(data, "tool0", "target"),
                                        'tool1Actual': temp(data, "tool1", "actual"),
                                        'tool1Target': temp(data, "tool1", "target"),
                                        'bedActual': temp(data, "bed", "actual"),
                                        'bedTarget': temp(data, "bed", "target")}
                        self.temperatures_signal.emit(temperatures)
                    except KeyError:
                        # temperatures = {'tool0Actual': 0,
                        #                 'tool0Target': 0,
                        #                 'tool1Actual': 0,
                        #                 'tool1Target': 0,
                        #                 'bedActual': 0,
                        #                 'bedTarget': 0}
                        pass
        except Exception as e:
            logger.error("Error in QtWebsocket.process: {}".format(e))
#
class ThreadSanityCheck(QtCore.QThread):

    loaded_signal = QtCore.pyqtSignal()
    startup_error_signal = QtCore.pyqtSignal()

    def __init__(self, logger = None, virtual=False):
        super(ThreadSanityCheck, self).__init__()
        self.MKSPort = None
        self.virtual = virtual
        if not Development:
            self._logger = logger

    def run(self):
        global octopiclient
        self.shutdown_flag = False
        # get the first value of t1 (runtime check)
        uptime = 0
        # keep trying untill octoprint connects
        while (True):
            # Start an object instance of octopiAPI
            try:
                if (uptime > 60):
                    self.shutdown_flag = True
                    self.startup_error_signal.emit()
                    break
                octopiclient = octoprintAPI(ip, apiKey)
                if not self.virtual:
                    # result = subprocess.Popen("dmesg | grep 'ttyUSB'", stdout=subprocess.PIPE, shell=True).communicate()[0]
                    # result = result.split(b'\n')  # each ssid and pass from an item in a list ([ssid pass,ssid paas])
                    # print(result)
                    # result = [s.strip() for s in result]
                    # for line in result:
                    #     if b'FTDI' in line:
                    #         self.MKSPort = line[line.index(b'ttyUSB'):line.index(b'ttyUSB') + 7].decode('utf-8')
                    #         print(self.MKSPort)
                    #     if b'ch34' in line:
                    #         self.MKSPort = line[line.index(b'ttyUSB'):line.index(b'ttyUSB') + 7].decode('utf-8')
                    #         print(self.MKSPort)
                    try:
                        octopiclient.connectPrinter(port="/tmp/printer", baudrate=115200)
                    except Exception as e:
                        octopiclient.connectPrinter(port="VIRTUAL", baudrate=115200)
                    # else:
                    #     octopiclient.connectPrinter(port="/dev/" + self.MKSPort, baudrate=115200)
                break
            except Exception as e:
                time.sleep(1)
                uptime = uptime + 1
                print("Not Connected!")
        if not self.shutdown_flag:
            self.loaded_signal.emit()

class ThreadFileUpload(QtCore.QThread):
    def __init__(self, file, prnt=False):
        super(ThreadFileUpload, self).__init__()
        self.file = file
        self.prnt = prnt

    def run(self):

        try:
            exists = os.path.exists(self.file.replace(".gcode", ".png"))
        except:
            exists = False
        if exists:
            octopiclient.uploadImage(self.file.replace(".gcode", ".png"))

        if self.prnt:
            octopiclient.uploadGcode(file=self.file, select=True, prnt=True)
        else:
            octopiclient.uploadGcode(file=self.file, select=False, prnt=False)

class ThreadRestartNetworking(QtCore.QThread):
    WLAN = "wlan0"
    ETH = "eth0"
    signal = QtCore.pyqtSignal('PyQt_PyObject')

    def __init__(self, interface):
        super(ThreadRestartNetworking, self).__init__()
        self.interface = interface
    def run(self):
        self.restart_interface()
        attempt = 0
        while attempt < 3:
            # print(getIP(self.interface))
            if getIP(self.interface):
                self.signal.emit(getIP(self.interface))
                break
            else:
                attempt += 1
                time.sleep(5)
        if attempt >= 3:
            self.signal.emit(None)

    def restart_interface(self):
        """
        restars wlan0 wireless interface to use new changes in wpa_supplicant.conf file
        :return:
        """
        if self.interface == "wlan0":
            subprocess.call(["wpa_cli","-i",  self.interface, "reconfigure"], shell=False)
        if self.interface == "eth0":
            subprocess.call(["ifconfig",  self.interface, "down"], shell=False)
            time.sleep(1)
            subprocess.call(["ifconfig", self.interface, "up"], shell=False)
        # subprocess.call(["ifdown", "--force", self.interface], shell=False)
        # subprocess.call(["ifup", "--force", self.interface], shell=False)
        time.sleep(5)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # Intialize the library (must be called once before other functions).
    # Creates an object of type MainUiClass
    MainWindow = MainUiClass()
    MainWindow.show()
    # MainWindow.showFullScreen()
    # MainWindow.setWindowFlags(QtCore.Qt.FramelessWindowHint)
    # Create NeoPixel object with appropriate configuration.
    # charm = FlickCharm()
    # charm.activateOn(MainWindow.FileListWidget)
sys.exit(app.exec_())
