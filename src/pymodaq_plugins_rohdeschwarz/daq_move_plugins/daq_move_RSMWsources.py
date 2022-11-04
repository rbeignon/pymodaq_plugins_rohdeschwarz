# common set of parameters for all actuators
from pymodaq.control_modules.move_utility_classes import DAQ_Move_base, \
    comon_parameters_fun, main  
# object used to send info back  to the main thread
from pymodaq.utils.daq_utils import ThreadCommand
from pymodaq.utils.parameter import Parameter
# shared UnitRegistry from pint initialized in __init__.py
from . import ureg, Q_
from pymodaq_plugins_rohdeschwarz.hardware.SMA_SMB_MW_sources import MWsource

class DAQ_Move_RSMWsource(DAQ_Move_base):
    """Plugin for the Rohde & Schwarz microwave sources of SMA and SMB series 
    This object inherits all functionality to communicate with PyMoDAQ Module
    through inheritance via DAQ_Move_base
    It then implements the particular communication with the instrument.

    Attributes:
    -----------
    controller: MWsource
        Instance of the class defined to communicate with the device.
    # TODO add your particular attributes here if any
    """
    _controller_units = "Hz"
    is_multiaxes = False  
    axes_names = [] 

    params = [   # TODO for your custom plugin: elements to be added here as dicts in order to control your custom stage
                ] + comon_parameters_fun(is_multiaxes, axes_names)

    def ini_attributes(self):
        self.controller: MWsource = None

        #TODO declare here attributes you want/need to init with a default value
        pass

    
    def get_actuator_value(self):
        """Get the current value of the CW frequency from the hardware.
        Sends 0 if we are not in CW mode.

        Returns
        -------
        float: The CW frequency in Hz.
        """
        mode, is_running = self._controller.get_status()
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
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        ## TODO for your custom plugin
        if param.name() == "a_parameter_you've_added_in_self.params":
           self.controller.your_method_to_apply_this_param_change()
        else:
            pass
        

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

        raise NotImplemented  # TODO when writing your own plugin remove this line and modify the one below
        self.ini_stage_init(old_controller=controller,
                            new_controller=PythonWrapperOfYourInstrument())

        info = "Whatever info you want to log"
        initialized = self.controller.a_method_or_atttribute_to_check_if_init()  # todo
        return info, initialized

    def move_abs(self, value):
        """ Move the actuator to the absolute target defined by value

        Parameters
        ----------
        value: (float) value of the absolute target positioning
        """

        value = self.check_bound(value)  #if user checked bounds, the defined bounds are applied here
        self.target_value = value
        value = self.set_position_with_scaling(value)  # apply scaling if the user specified one
        ## TODO for your custom plugin
        raise NotImplemented  # when writing your own plugin remove this line
        self.controller.your_method_to_set_an_absolute_value(value)  # when writing your own plugin replace this line
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))


    def move_rel(self, value):
        """ Move the actuator to the relative target actuator value defined by value

        Parameters
        ----------
        value: (float) value of the relative target positioning
        """
        value = self.check_bound(self.current_position + value) - self.current_position
        self.target_value = value + self.current_position
        value = self.set_position_relative_with_scaling(value)

        ## TODO for your custom plugin
        raise NotImplemented  # when writing your own plugin remove this line
        self.controller.your_method_to_set_a_relative_value(value)  # when writing your own plugin replace this line
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))


    def move_home(self):
        """Call the reference method of the controller"""

        ## TODO for your custom plugin
        raise NotImplemented  # when writing your own plugin remove this line
        self.controller.your_method_to_get_to_a_known_reference()  # when writing your own plugin replace this line
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))


    def stop_motion(self):
      """Stop the actuator and emits move_done signal"""

      ## TODO for your custom plugin
      raise NotImplemented  # when writing your own plugin remove this line
      self.controller.your_method_to_stop_positioning()  # when writing your own plugin replace this line
      self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))


if __name__ == '__main__':
    main(__file__)
