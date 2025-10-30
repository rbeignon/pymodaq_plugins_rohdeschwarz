
import numpy as np
from typing import Union, List, Dict
from pymodaq.control_modules.move_utility_classes import (DAQ_Move_base, comon_parameters_fun,
                                                          main, DataActuatorType, DataActuator)

from pymodaq_utils.utils import ThreadCommand  # object used to send info back to the main thread
from pymodaq_gui.parameter import Parameter

from pymodaq_plugins_rohdeschwarz import ureg, Q_
from pymodaq_plugins_rohdeschwarz.hardware.SMA_SMB_MW_sources import MWsource



class DAQ_Move_MultiRSMWsource(DAQ_Move_base):
    """Plugin for the Rohde & Schwarz microwave sources of SMA and SMB series 
    This object inherits all functionality to communicate with PyMoDAQ Module
    through inheritance via DAQ_Move_base. Power of the MWSource.
    It then implements the particular communication with the instrument.

    Attributes:
    -----------
    controller: MWsource
        Instance of the class defined to communicate with the device.
    """
    is_multiaxes = True  
    _axis_names: Union[List[str], Dict[str, int]] = ['Frequency', 'Power'] 
    _controller_units: Union[str, List[str]] = ['Hz', 'dBm'] 
    _epsilon: Union[float, List[float]] = 0.01  
    data_actuator_type = DataActuatorType.DataActuator 
    params = [  {'title': 'Address:', 'name': 'address', 'type': 'str',
                 'value': '', 'readonly': False}
                ] + comon_parameters_fun(is_multiaxes, axis_names=_axis_names, epsilon=_epsilon)
  

    def ini_attributes(self):
        self.controller: MWsource = None


    def get_actuator_value(self):
        """Get the current value from the hardware with scaling conversion.

        Returns
        -------
        float: The position obtained after scaling conversion.
        """
        mode, is_running = self.controller.get_status()
        if self.axis_name == 'Frequency' :
            if mode =='cw' :
                pos = DataActuator(data=np.array([self.controller.get_frequency().to(ureg.Hz).magnitude]), units=self.axis_unit)
            else :
                self.emit_status("The device is not in CW mode!")
                pos = DataActuator(data=np.array([0]), units=self.axis_unit)
            pos = self.get_position_with_scaling(pos)
        elif self.axis_name == 'Power' :
            if mode =='cw' :
                pos = DataActuator(data=np.array([self.controller.get_power().to(ureg.dBm).magnitude]), units=self.axis_unit)
            else :
                self.emit_status("The device is not in CW mode!")
                pos = DataActuator(data=np.array([0]), units=self.axis_unit)
            pos = self.get_position_with_scaling(pos)
        return pos


    def close(self):
        """Terminate the communication protocol.
        """
        if self.is_master:
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
        # timeout if in comon_parameters
        elif param.name() == "timeout":
            timeout_to_set = Q_(param.value(), ureg.second)
            self.controller.set_timeout(timeout=timeout_to_set) 


    def ini_stage(self, controller=None):
        """Actuator communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator by controller (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """
        
        if self.is_master:  # is needed when controller is master
            self.controller = MWsource()
            initialized = self.controller.open_communication(address=self.settings.child("address").value())  
        else:
            self.controller = controller
            initialized = True
        if initialized:
            # We go to CW mode
            self.controller.set_cw_params()
            # read the params
            self.settings.child("address").setValue(self.controller.get_address())
            self.settings.child("timeout").setValue(self.controller.get_timeout().to(ureg.second).magnitude)        
        info = self.controller.model
        return info, initialized


    def move_abs(self, value: DataActuator):
        """ Move the actuator to the absolute target defined by value

        Parameters
        ----------
        value: (float) value of the absolute target positioning
        """

        value = self.check_bound(value)  #if user checked bounds, the defined bounds are applied here
        self.target_value = value
        value = self.set_position_with_scaling(value)  # apply scaling if the user specified one
        if self.axis_name == 'Frequency' :
            freq_to_set = value.value() * ureg.Hz
            self.controller.set_cw_params(frequency=freq_to_set)
            self.controller.cw_on()
            self.emit_status(ThreadCommand('Update_Status', [f'CW frequency set to {freq_to_set:.3f~P}']))
        elif self.axis_name == 'Power' :
            pow_to_set = Q_(value.value(), ureg.dBm)
            self.controller.set_cw_params(power=pow_to_set)
            self.controller.cw_on()
            self.emit_status(ThreadCommand('Update_Status', [f'CW power set to {pow_to_set:.3f~P}']))

    def move_rel(self, value: DataActuator):
        """ Move the actuator to the relative target actuator value defined by value

        Parameters
        ----------
        value: (float) value of the relative target positioning
        """
        value = self.check_bound(self.current_position + value) - self.current_position
        self.target_value = value + self.current_position
        value = self.set_position_relative_with_scaling(value)
        if self.axis_name == 'Frequency' :
            freq_to_set = self.target_value.value() * ureg.Hz
            self.controller.set_cw_params(frequency=freq_to_set)
            self.controller.cw_on()
            self.emit_status(ThreadCommand('Update_Status', [f'CW frequency set to {freq_to_set:.3f~P}']))
        elif self.axis_name == 'Power' :
            pow_to_set = Q_(self.target_value.value(), ureg.dBm)
            self.controller.set_cw_params(power=pow_to_set)
            self.controller.cw_on()
            self.emit_status(ThreadCommand('Update_Status', [f'CW power set to {pow_to_set:.3f~P}']))

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
