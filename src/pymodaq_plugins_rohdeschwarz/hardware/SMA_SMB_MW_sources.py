# -*- coding: utf-8 -*-

"""
This file is the wrapper for MW sources SMB and SMA from Rohde & Schwarz.
It was tested on the models SMB100A and SMA100B.

Parts of this file were developed from the Qudi mw_source_smbv hardware module.
Copyright (c) the Qudi Developers.
"""

import pyvisa as visa
import numpy as np
import time
# shared UnitRegistry from pint initialized in __init__.py
from pymodaq_plugins_rohdeschwarz import ureg, Q_ 

class MWsource:

    def __init__(self):
        super().__init__()
        
        self._model = ""
        self._address = ""
        self._timeout = 1e4 * ureg.millisecond

    
    def get_address(self):
        """Gets the visa address used to communicate with  the device.
        
        Returns
        -------
        str: the visa address currently set.
        """
        return self._address

    
    def set_address(self, visa_address):
        """Set the visa address to communication with the device.
        Should be called before open_communication. Beware, it does not
        reset the connection, you have to do it otherwise the stored address
        and the used one will be different.

        Parameters
        ----------
        visa_address: str
            Visa address of the device
        """
        self._address = visa_address


    def get_timeout(self):
        """Gets the visa address used to communicate with  the device.
        
        Returns
        -------
        pint Quantity (time): the communication timeout
        """
        return self._timeout

    
    def set_timeout(self, timeout):
        """Set the timeout for communication with the device.
        Should be called before open_communication. Beware, it does not
        reset the connection, you have to do it if you want to change
        the timeout parameter used by pyvisa.

        Parameters
        ----------
        timeout: pint Quantity (time)
           Timeout to set for communication with the device
        """
        self._timeout = timeout
        

    @property
    def model(self):
        """Returns the ID string provided by the device.
        """
        return self._model
    
    
    def open_communication(self, address=None):    
        """Initiate the communication with the device.
        """
        self.rm = visa.ResourceManager()
        if address is not None:
            self.set_address(address)

        try:
            self._connection = self.rm.open_resource(self._address,
                                            timeout=self._timeout.magnitude)
            self._model = self._connection.query("*IDN?").split(",")[1]
            self._command_wait("*CLS")
            self._command_wait("*RST")
        except:
            return False

        return True
    

    def close_communication(self):
        """Close properly the communication with the device.
        """
        self.rm.close()
        

    def _command_wait(self, command_str):
        """Writes the command in command_str via ressource manager and waits
        until the device has finished processing it.

        Parameters
        ----------
        command_str: str
            the command to send to the device
        """
        self._connection.write(command_str)
        self._connection.write("*WAI")
        while int(float(self._connection.query("*OPC?"))) != 1:
            time.sleep(0.2)
        return


    def off(self):
        """
        Switches off any microwave output.
        """
        mode, is_running = self.get_status()
        if not is_running: # already OFF
            return 

        self._command_wait("OUTP:STAT OFF")
        return 


    def get_status(self):
        """Gets the current status of the MW source, i.e. the mode
        (cw, list or sweep) and the output state.

        Returns
        --------
        str: either "cw", "list" or "sweep"
        bool: True if MW is on, False otherwise
        """
        is_running = bool(int(float(self._connection.query("OUTP:STAT?"))))
        mode = self._connection.query(":FREQ:MODE?").strip("\n").lower()
        if mode == "swe":
            mode = "sweep"
        return mode, is_running


    def get_power(self):
        """Gets the microwave output power.
         The function returns:
         - a single value if the device is in cw or sweep mode or
           if all the values are the same in list mode,
         - an array of values if different values are used in list mode.

        Returns
        --------
        [pint Quantity, or 1D ndarray of pint Quantities]
            Power set at the device in dBm, or array of values in list mode.
        """
        mode, is_running = self.get_status()
        # This case works for cw AND sweep mode
        if ("cw" in mode) or ("sweep" in mode):
            rep = float(self._connection.query(":POW?"))
        # for the list mode
        elif "list" in mode:
            pow_list =  self._connection.query("LIST:POW?")
            pow_list = pow_list.split(",")
            rep = np.array([float(x) for x in pow_list])
            if rep.all() == rep[0]:
                rep = rep[0]
        # multiplying does not work with log units
        return Q_(rep, ureg.dBm) 


    def get_frequency(self):
        """Gets the frequency of the microwave output.
        The function returns:
         - a single value if the device is in cw mode,
         - an array [start, stop, step] in sweep mode
         - an array of values in list mode.

        Returns
        --------
        [pint Quantity, or 1D ndarray of pint Quantities]: Frequencies
            currently set in the device, in Hz
        """
        mode, is_running = self.get_status()
        if "cw" in mode:
            rep = float(self._connection.query(":FREQ?"))
        elif "sweep" in mode:
            start = float(self._connection.query(":FREQ:STAR?"))
            stop = float(self._connection.query(":FREQ:STOP?"))
            step = float(self._connection.query(":SWE:STEP?"))
            rep = [start+step, stop, step]
        elif "list" in mode: 
            freq_str = self._connection.query(":LIST:FREQ?")
            freq_list = freq_str.split(",")
            rep = np.array([float(f) for f in freq_list]) # convert in Hz     
        return rep * ureg.Hz
    

    def cw_on(self):
        """Switch on the CW microwave output.
        """
        current_mode, is_running = self.get_status()
        if is_running:
            if current_mode == "cw": # CW is already ON
                return
            else: # already running in  another mode
                self.off()
                
        if current_mode != "cw":
            self._command_wait(":FREQ:MODE CW")

        self._command_wait(":OUTP:STAT ON")
        return


    def set_cw_params(self, frequency=None, power=None):
        """Configure the device for CW mode, with optional specification
        of frequency and power.

        Parameters
        ----------
        frequency: pint Quantity
            CW frequency to set (will be converted in Hz)
        power: pint Quantity
            CW power to set in dBm (will be converted in dBm)

        Returns
        --------
        str: current mode, should be "cw"
        pint Quantity: frequency currently set in the device
        pint Quantity: power currently set in the device
        """
        mode, is_running = self.get_status()
        if is_running:
            self.off()

        # Activate CW mode
        if mode != "cw":
            self._command_wait(":FREQ:MODE CW")

        # Set CW frequency if provided
        if frequency is not None:
            self._command_wait(":FREQ {:.6f~P}".format(
                frequency.to(ureg.GHz)))

        # Set CW power if provided
        if power is not None:
            self._command_wait(":POW {:.2f}".format(
                power.to(ureg.dBm).magnitude))

        # Return actually set values
        mode, is_running = self.get_status()
        return mode, self.get_frequency(), self.get_power()

    
    def list_on(self):
        """Switch on the microwave output in list mode.
        """
        current_mode, is_running = self.get_status()
        if is_running:
            if current_mode == "list": # List mode already on
                return 
            else:
                self.off() # already running in another mode
                
        if current_mode != "list":
            self._command_wait(":FREQ:MODE LIST")
            self._connection.write(':LIST:SEL "My_list"')
        self._command_wait(":OUTP:STAT ON")
        return


    def set_list(self, frequency=None, power=None):
        """Configure the device for list mode and optionally sets
        frequencies and/or power.

        Parameters
        ----------
        frequency : pint Quantity array
            list of the frequencies to set
        power : pint Quantity (can be an array)
            list of the power to set, or a unique value for the whole list

        Returns
        --------
        str: current mode, should be "list"
        pint Quantity array: frequency list currently set in the device
        pint Quantity array: power list currently set in the device
        """
        
        mode, is_running = self.get_status()
        if is_running:
            self.off()
        if frequency is not None and power is not None:
            if isinstance(power.magnitude, float) or \
                                      isinstance(power.magnitude, int):
                power = power*np.ones(len(frequency))
            if len(frequency) != len(power):
                print("Number of frequencies and power values not matching!")
                return
            
            self._connection.write(':LIST:SEL "My_list"')

            freq_str = ""
            for freq in frequency:
                freq_str += "{:.6f~P}, ".format(freq.to(ureg.GHz))
            self._connection.write("LIST:FREQ {:s}".format(freq_str[:-2]))
            
            power_str = ""
            for p in power:
                power_str += "{:.2f}, ".format(p.to(ureg.dBm).magnitude)
            self._connection.write("LIST:POW {:s}".format(power_str[:-2]))

        self._command_wait(":FREQ:MODE LIST")
        # trigger each value in the list separately
        self._connection.write("LIST:MODE STEP")
        # external trigger
        self._connection.write("LIST:TRIG:SOUR EXT") 

        # Return actually set values
        mode, is_running = self.get_status()
        return mode, self.get_frequency(), self.get_power()


    def reset_list_position(self):
        """Reset the list mode position to the starting point.
        """
        self._command_wait(":LIST:RES")
        return


    def sweep_on(self):
        """Switch on the microwave output in sweep mode.
        """
        current_mode, is_running = self.get_status()
        if is_running:
            if current_mode == "sweep": # sweep mode already on
                return 
            else:
                self.off() # already running in another mode
                
        if current_mode != "sweep":
            self._command_wait(":FREQ:MODE SWEEP")
        self._command_wait(":OUTP:STAT ON")
        return


    def set_sweep(self, start=None, stop=None, step=None,
                  points = None, power=None):
        """Configure the device for sweep mode, and optionally sets the
        frequencies, setting the range and the step width and/or the power. 

        Parameters
        ----------
        start : pint Quantity
            Sweep start frequency
        stop : pint Quantity
            Sweep stop frequency
        step : pint Quantity
            Sweep step size, specify either step or points
        power : pint Quantity
            MW power during the sweep

        Returns
        --------
        str: current mode, should be "list"
        pint Quantity: Sweep start frequency currently set in the device
        pint Quantity: Sweep stop frequency currently set in the device
        pint Quantity: Sweep frequency step currently set in the device
        pint Quantity: Power list currently set in the device
        """

        mode, is_running = self.get_status()
        if is_running:
            self.off()

        if mode != "sweep":
            self._command_wait(":FREQ:MODE SWEEP")

        if start is not None and stop is not None and step is not None:
            self._command_wait(":SWE:MODE STEP")
            self._command_wait(":SWE:SPAC LIN")
            self._command_wait(":FREQ:START {:.6f~P}".format(
                (start - step).to(ureg.GHz)))
            self._command_wait(":FREQ:STOP {:.6f~P}".format(stop.to(ureg.GHz)))
            self._command_wait(":SWE:STEP:LIN {:.6f~P}".format(
                step.to(ureg.GHz)))
            
        if power is not None:
            self._command_wait(":POW {:.2f}".format(
                power.to(ureg.dBm).magnitude))

        self._command_wait("TRIG:FSW:SOUR EXT")

        sweep_freqs = self.get_frequency() # start, stop, step
        return mode, sweeps_freqs[0], sweeps_freqs[1], sweeps_freqs[2], \
            self.get_power()

    
    def reset_sweep_position(self):
        """Reset the sweep mode position to the starting point.
        """
        self._command_wait(":ABOR:SWE")
        return


    def set_ext_trigger(self, trigger_edge):
        """Set the external trigger for sweep and list mode, specifying
        the proper edge (rising or falling).

        Parameters
        ----------
        trigger_edge : str
            "rising" or "falling"
        """

        mode, is_running = self.get_status()
        if is_running:
            self.off()

        if trigger_edge == "rising":
            polarity = "POS"
        elif trigger_edge == "falling":
            polarity = "NEG"
        else:
            print("Unknown trigger edge setting!")
            return

        self._command_wait(f":TRIG1:SLOP {polarity}")
        return

    
    def get_ext_trigger(self):
        """Get the edge set for the external trigger.

        Returns
        --------
        str: "rising" or "falling"
        """
        polarity = self._connection.query(":TRIG1:SLOP?")
        if "POS" in polarity:
            return "rising"
        else:
            return "falling"
