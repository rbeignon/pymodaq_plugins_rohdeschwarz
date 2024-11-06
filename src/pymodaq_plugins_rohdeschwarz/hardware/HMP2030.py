"""
This file is the wrapper for power supply HMP from Rohde & Schwarz.
Basic function have been tested on the models HMP2030.
(open_communication(), close_communication(), set_control_value())
This file is adapted from a Qudi hardware module

Things concerning the error management should be modified.
"""
import pyvisa
from pymodaq.utils.logger import set_logger, get_module_name

logger = set_logger(get_module_name(__file__))


class HMP2030:


    _model = ""
    _address = ''
    _modclass = 'PowerSupply'
    _modtype = 'hardware'
    _inst = None
    _voltage_max_1 = 32
    _current_max_1 = 5
    _voltage_max_2 = 32
    _current_max_2 = 5
    _voltage_max_3 = 32
    _current_max_3 = 5

    def open_communication(self, address=None):
        """ Startup the module """

        self.rm = pyvisa.ResourceManager()
        if address is not None:
            self.set_address(address)

        try:
            self._inst = self.rm.open_resource(self._address)
        except:
            logger.error('Could not connect to hardware. Please check the wires and the address.')
            return False

        return True

    def close_communication(self):
        """ Stops the module """
        self._set_all_off()
        self._inst.close()

    def _set_channel(self, channel):
        """sets the channel 1, 2 or 3"""
        if channel in [1, 2, 3]:
            self._inst.write('INST OUT{}'.format(channel))
        else:
            logger.error('Wrong channel number. Chose 1, 2 or 3.')

    def _get_channel(self):
        """ query the selected channel"""
        channel = int(self._inst.query('INST:NSEL?'))
        return channel

    def _get_status_channel(self, channel):
        """ Gets the current status of the selected channel (CC or CV)"""
        state = int(self._inst.query('STAT:QUES:INST:ISUM{}:COND?'.format(channel)))
        status = 'CC' if state == 1 else 'CV'
        return status

    def _set_voltage(self, value, channel=None):
        """ Sets the voltage to the desired value"""
        if channel is not None:
            self._set_channel(channel)
        mini, maxi = self.get_control_limit(channel=channel)
        if mini <= value <= maxi:
            self._inst.write("VOLT {}".format(value))
        else:
            logger.error('Voltage value {} out of range'.format(value))

    def _get_voltage(self, channel=None):
        """ Get the measured the voltage """
        if channel is not None:
            self._set_channel(channel)
        voltage = float(self._inst.query('MEAS:VOLT?'))
        return voltage
        
    def _set_current(self, value, channel=None):
        """ Sets the current to the desired value """

        mini, maxi = self._get_control_limit_current(channel=channel)
        if mini <= value <= maxi:
            self._inst.write("CURR {}".format(value))
        else:
            logger.error('Current value {} out of range'.format(value))

    def _get_current(self, channel=None):
        """ Get the measured the current  """
        if channel is not None:
            self._set_channel(channel)
        current = float(self._inst.query('MEAS:CURR?'))
        return current

    def _set_on(self, channel=None):
        """ Turns the output from the chosen channel on """
        if channel is not None:
            self._set_channel(channel)
        self._inst.write('OUTP ON')

    def _set_off(self, channel=None):
        """ Turns the output from the chosen channel off """
        if channel is not None:
            self._set_channel(channel)
        self._inst.write('OUTP OFF')

    def _set_all_off(self):
        """ Stops the output of all channels """
        self._set_off(1)
        self._set_off(2)
        self._set_off(3)

    def _reset(self):
        """ Reset the whole system"""
        self._inst.write('*RST')  # resets the device
        self._inst.write('SYST:REM')  # sets the instrument to remote control

    def _beep(self):
        """ gives an acoustical signal from the device """
        self._inst.write('SYST:BEEP')

    def _error_list(self):
        """ Get all errors from the error register """
        error = str(self._inst.query('SYST:ERR?'))
        return error

    def _set_over_voltage(self, maxi, channel=None):
        """ Sets the over voltage protection for a selected channel"""
        if channel is not None:
            self._set_channel(channel)
        self._inst.write('VOLT:PROT {}'.format(maxi))

    def _set_over_current(self, maxi, channel=None):
        """ Sets the over current protection for a selected channel"""
        if channel is not None:
            self._set_channel(channel)
        self._inst.write('FUSE ON') # The FUSE is never set off ?
        self._inst.write('CURR {}'.format(maxi))

# Interface methods
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

    def get_address(self):
        """Gets the visa address used to communicate with  the device.

        Returns
        -------
        str: the visa address currently set.
        """
        return self._address

    def set_control_value(self, value, channel=1, ctrparam="VOLT"):
        """ Set control value

            @param (float) value: control value
            @param (int) channel: channel to control
            @param (str) ctrparam: control parameter ("VOLT" or "CURR")
        """
        if channel is not None:
            self._set_channel(channel)
        mini, maxi = self.get_control_limit(channel, ctrparam)
        if mini <= value <= maxi:
            self._inst.write("{} {}".format(ctrparam, value))
        else:
            logger.error('Control value {} out of range'.format(value))

    def get_control_value(self, ctrparam="VOLT"):
        """ Get current control value, here heating power

            @param (str) ctrparam: control parameter ("VOLT" or "CURR")
            @return float: current control value
        """
        return float(self._inst.query("{}?".format(ctrparam)).split('\r')[0])

    def get_control_unit(self, ctrparam="VOLT"):
        """ Get unit of control value.

            @param (str) ctrparam: control parameter ("VOLT" or "CURR")
            @return tuple(str): short and text unit of control value
        """
        if ctrparam == "VOLT":
            return 'V', 'Volt'
        else:
            return 'A', 'Ampere'

    def get_control_limit(self, channel=None, ctrparam="VOLT"):
        """ Get minimum and maximum of control value.

            @param (str) ctrparam: control parameter ("VOLT" or "CURR")
            @return tuple(float, float): minimum and maximum of control value
        """
        if channel is None:
            channel = self._get_channel()
        maxi = 0
        if ctrparam == "VOLT":
            maxi = self._voltage_max_1 if channel == 1 else maxi
            maxi = self._voltage_max_2 if channel == 2 else maxi
            maxi = self._voltage_max_3 if channel == 3 else maxi
        else:
            maxi = self._current_max_1 if channel == 1 else maxi
            maxi = self._current_max_2 if channel == 2 else maxi
            maxi = self._current_max_3 if channel == 3 else maxi
        return 0, maxi

    def process_control_supports_multiple_channels(self):
        """ Function to test if hardware support multiple channels """
        return True

    def process_control_get_number_channels(self):
        """ Function to get the number of channels available for control """
        return 3

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
