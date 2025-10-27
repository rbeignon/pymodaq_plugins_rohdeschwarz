# common set of parameters for all actuators
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, \
    comon_parameters_fun, main  
# object used to send info back  to the main thread
from pymodaq.daq_utils.daq_utils import ThreadCommand
from pymodaq.daq_utils.parameter import Parameter
# shared UnitRegistry from pint initialized in __init__.py
from pymodaq_plugins_rohdeschwarz import ureg, Q_
from pymodaq_plugins_rohdeschwarz.hardware.SMA_SMB_MW_sources import MWsource

class DAQ_Move_RSMWsource(DAQ_Move_base):
    """Plugin for the Rohde & Schwarz microwave sources of SMA and SMB series 
    This object inherits all functionality to communicate with PyMoDAQ Module
    through inheritance via DAQ_Move_base.
    It then implements the particular communication with the instrument.

    Attributes:
    -----------
    controller: MWsource
        Instance of the class defined to communicate with the device.
    """

    _controller_units = "Hz"
    is_multiaxes = False  
    axes_names = []
    _epsilon = 0.01

    params = [  {'title': 'Address:', 'name': 'address', 'type': 'str',
                 'value': '', 'readonly': False},
                {'title': 'Power (dBm):', 'name': 'power', 'type': 'float',
                 'value': 0, 'readonly': False}
                ] + comon_parameters_fun(is_multiaxes, axes_names)

    
    def ini_attributes(self):
        self.controller: MWsource = None

    def get_actuator_value(self):
        """Get the current value of the CW frequency from the hardware.
        Sends 0 if we are not in CW mode.

        Returns
        -------
        float: The CW frequency in Hz.
        """
        mode, is_running = self.controller.get_status()
        if mode == "cw":
            frequency = self.controller.get_frequency()
        else:
            self.emit_status("The device is not in CW mode!")
            frequency = 0 * ureg.Hz
        freq = self.get_position_with_scaling(frequency.to(ureg.Hz).magnitude)
        return freq
 
    def close(self):
        """Terminate the communication protocol.
        """
        self.controller.close_communication()  
        
    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the device settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has
            been changed by the user
        """
        if param.name() == "address":
            self.controller.set_address(param.value())
        elif param.name() == "power":
            power_to_set = Q_(param.value(), ureg.dBm)
            self.controller.set_cw_params(power=power_to_set)
        # timeout if in comon_parameters
        elif param.name() == "timeout":
            timeout_to_set = Q_(param.value(), ureg.second)
            self.controller.set_timeout(timeout=timeout_to_set)        

    def ini_stage(self, controller=None):
        """Communication initialization.

        Parameters
        ----------
        controller: MWsource
            Custom object of a PyMoDAQ plugin (Slave case).
            None if only one actuator by controller (Master case).

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """

        self.ini_stage_init(old_controller=controller,
                            new_controller=MWsource())
        
        initialized = self.controller.open_communication(
            address=self.settings.child("address").value())
        info = self.controller.model
        if initialized:
            # We go to CW mode
            self.controller.set_cw_params()
            # read the params
            self.settings.child("address").setValue(
                self.controller.get_address())
            self.settings.child("power").setValue(
                self.controller.get_power().magnitude)
            self.settings.child("timeout").setValue(
             self.controller.get_timeout().to(ureg.second).magnitude)
            
        return info, initialized
    
    def move_abs(self, value):
        """ Move the actuator to the absolute target defined by value.

        Parameters
        ----------
        value: (float) value of the absolute target frequency, in Hz
        """
        # if user checked bounds, the defined bounds are applied here
        value = self.check_bound(value) 
        self.target_value = value
        # apply scaling if the user specified one
        value = self.set_position_with_scaling(value)  

        freq_to_set = value * ureg.Hz
        self.controller.set_cw_params(frequency=freq_to_set)
        self.controller.cw_on()
        
        self.emit_status(ThreadCommand('Update_Status',
                [f'CW frequency set to {freq_to_set:.3f~P}']))
        
        self.target_position = value

    def move_rel(self, value):
        """ Move the actuator to the relative target actuator value
        defined by value

        Parameters
        ----------
        value: (float) value of the relative target positioning frequency, in Hz
        """
        value = self.check_bound(self.current_position + value) - \
            self.current_position
        self.target_value = value + self.current_position
        value = self.set_position_relative_with_scaling(value)

        freq_to_set = self.target_value * ureg.Hz
        self.controller.set_cw_params(frequency=freq_to_set)
        self.controller.cw_on()
        self.emit_status(ThreadCommand('Update_Status',
                [f'CW frequency set to {freq_to_set:.3f~P}.']))

    def move_home(self):
        """Does nothing, there is no specific home value."""
        pass
        
    def stop_motion(self):
      """Turn off the MW signal"""
      self.controller.off()
      self.emit_status(ThreadCommand('Update_Status',
                                     ['MW output turned off.']))

if __name__ == '__main__':
    main(__file__)
