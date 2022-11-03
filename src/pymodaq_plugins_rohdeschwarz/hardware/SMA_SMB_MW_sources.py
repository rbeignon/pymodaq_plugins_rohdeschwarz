# -*- coding: utf-8 -*-

"""
This file is the wrapper for MW sources SMB and SMA from Rohde & Schwarz.
It was tested on the models SMB100A and SMA100B.

Parts of this file were developed from the Qudi mw_source_smbv hardware module.
Copyright (c) the Qudi Developers.
"""

import visa
import numpy as np
import time
from . import ureg # shared UnitRegistry from pint initialized in __init__.py

class MWsource:

    def __init__(self):
        super().__init__()
        
        self._model = ""
        self._address = ""
        self._timeout = 1e4 * ureg.millisecond
        self._mode = "cw"
        self._power = 0 * ureg.dBm

 

    def open_communication(self):    
        """Initiate the communication with the device.
        """

        self.rm = visa.ResourceManager()
        try:
            self._connection = self.rm.open_resource(self._address,
                                            timeout=self._timeout.magnitude)
        except:
            return False

        self._model = self._connection.query('*IDN?').split(',')[1]
        self._command_wait('*CLS')
        self._command_wait('*RST')
        return
    

    def close_communication(self):
        """Close properly the communication with the device.
        """
        self.rm.close()


    def _command_wait(self, command_str):
        """Writes the command in command_str via ressource manager and waits
        until the device has finished processing it.

        Parameters
        ----------
        command_str : str
            the command to send to the device
        """
        self._connection.write(command_str)
        self._connection.write('*WAI')
        while int(float(self._connection.query('*OPC?'))) != 1:
            time.sleep(0.2)
        return


    def off(self):
        """
        Switches off any microwave output.
        Must return AFTER the device is actually stopped.
        """
        mode, is_running = self.get_status()
        if not is_running:
            return 

        self._connection.write('OUTP:STAT OFF')
        self._connection.write('*WAI')
        while int(float(self._connection.query('OUTP:STAT?'))) != 0:
            time.sleep(0.2)
        return 


    def get_status(self):
        """Gets the current status of the MW source, i.e. the mode
        (cw, list or sweep) and the output state.

        Returns
        --------
        str
            either "cw", "list" or "sweep"
        bool
            True if MW is on, False otherwise
        """
        is_running = bool(int(float(self._connection.query('OUTP:STAT?'))))
        mode = self._connection.query(':FREQ:MODE?').strip('\n').lower()
        if mode == 'swe':
            mode = 'sweep'
        return mode, is_running


    def get_power(self):
        """Gets the microwave output power.
         The function returns:
         - a single value if the device is in cw or sweep mode or
           if all the values are the same in list mode,
         - an array of values if different values are used in list mode.

        Returns
        --------
        [pint Quantity, or 1D ndarray of Quantities]
            Power set at the device in dBm, or array of values in list mode.
        """
        mode, is_running = self.get_status()
        # This case works for cw AND sweep mode
        if ('cw' in mode) or ('sweep' in mode):
            rep = float(self._connection.query(':POW?'))
        # for the list mode
        elif 'list' in mode:
            pow_list =  self._connection.query('LIST:POW?')
            pow_list = pow_list.split(",")
            rep = np.array([float(x) for x in pow_list])
            if rep.all() == rep[0]:
                rep = rep[0]
        return rep * ureg.dBm


    def get_frequency(self):
        """Gets the frequency of the microwave output.
        The function returns:
         - a single value if the device is in cw mode,
         - an array [start, stop, step] in sweep mode
         - an array of values in list mode.

        Returns
        --------
        [pint Quantity, or 1D ndarray of Quantities]
            Frequencies currently set in the device, in Hz
        """
        mode, is_running = self.get_status()
        if 'cw' in mode:
            rep = float(self._connection.query(':FREQ?'))
        elif 'sweep' in mode:
            start = float(self._connection.query(':FREQ:STAR?'))
            stop = float(self._connection.query(':FREQ:STOP?'))
            step = float(self._connection.query(':SWE:STEP?'))
            rep = [start+step, stop, step]
        elif 'list' in mode: 
            freq_str = self._connection.query(':LIST:FREQ?')
            freq_list = freq_str.split(',')
            rep = np.array([float(f) for f in freq_list]) # convert in Hz     
        return rep * ureg.Hz
    
