from dataclasses import dataclass
from logging import getLogger
import yaml
from typing import NamedTuple
import functools
import time

from cooethercat import EPOS4Motor
from cooethercat.helpers import make_pdo_mapping, EPOS4Obj, StatuswordStates, HomingMethods
from cooethercat import EPOS4Bus
# Re-exported so imports from lris2csu.hardware keep resolving
from lris2csu.geometry import BarConfig, BarPairConfig, CSUHardwareConfig  # noqa: F401
from lris2csu.slit import MaskConfig


class CSU_ECmax16_283828_config(NamedTuple):
    motor_type: int = 10  # 6-227
    nominal_current_ma: int = 456  # max continuous current
    output_current_limit_ma: int = 762
    number_of_pole_pairs: int = 1
    thermal_time_constant_winding_ms: int = 914
    torque_constant_uNm_A: int = 7800
    max_motor_speed_rpm: int = 20000


class CSU_ENC16EASY_499361_config(NamedTuple):
    number_of_pulses_per_turn: int = 1024
    direction: int = 0  #0=maxon 1=inverted (on output shaft)
    index: int = 1
    method: int = 1  # edges per control cycle, 0 is edges per time  6.152


class CSU_planetary_gearhead_GP16A_138342_config(NamedTuple):
    gear_reduction_numerator: int = 29198
    gear_reduction_denominator: int = 79
    gear_max_input_speed_rpm: int = 8000
    gear_orientation: int = 0  # 0: output = input


#pole length 2mm
#ssi+incremental, no line driver, 5v
#12bit period counter
#2048 interpolation factor 0.977um
#1us/1MHz minimum edge separation (I'd guess then 2mm/1us = 2m/s max speed so we are VERY safe)
class CSU_SSI_encoder_RLM2sJF11B_config(NamedTuple):
    data_rate_kbps: int = 2000  #encode min 50 max 4000 epos max 2000
    # number_of_bits: int = 13
    encoding_type: int = 0 #TODO 0=binary 1=gray
    direction: int = 1 #TODO  0=maxon 1=inverted or mounted on output shaft
    # check_frame: int = 1
    timeout_time_us: int = 20
    number_of_multi_turn_bits: int = 11 #TODO
    number_of_single_turn_bits: int = 12
    number_of_error_bits: int = 2
    power_up_time: int = 50


@dataclass
class CSU_PID_CONFIG:
    position_controller_p_gain: int
    position_controller_i_gain: int
    position_controller_d_gain: int
    position_controller_ff_velocity_gain: int
    position_controller_ff_acceleration_gain: int
    current_controller_p_gain: int
    current_controller_i_gain: int
    velocity_controller_p_gain: int
    velocity_controller_i_gain: int
    velocity_controller_ff_velocity_gain: int
    velocity_controller_ff_acceleration_gain: int


class BarMotor(EPOS4Motor):
    DUAL_LOOP_PID_PARAMS = CSU_PID_CONFIG(0,0,0,0,0,0,0,0,0,0,0)  #TODO
    SINGLE_LOOP_PID_PARAMS = CSU_PID_CONFIG(0,0,0,0,0,0,0,0,0,0,0)  #TODO

    def __init__(self, *args, use_ssi_encoder=False, **kwargs):
        super().__init__(*args)
        self.use_ssi_encoder = use_ssi_encoder

    def config_func(self, node_id):
        getLogger(__name__).debug(f"Configuring BarMotor device {self} via config_func"
                                  f" (EPOS4 Micro 24/5) at bus node {self.node}")
        assert node_id == self.node

        # Define the Process Data Objects for PPM (Rx and Tx)
        ppm_rx = [
            self.ADDRESS.CONTROLWORD,
            self.ADDRESS.TARGET_POSITION,
            self.ADDRESS.PROFILE_ACCELERATION,
            self.ADDRESS.PROFILE_DECELERATION,
            self.ADDRESS.PROFILE_VELOCITY,
            self.ADDRESS.MODES_OF_OPERATION,
            self.ADDRESS.PHYSICAL_OUTPUTS
        ]
        ppm_tx = [
            self.ADDRESS.STATUSWORD,
            self.ADDRESS.POSITION_ACTUAL_VALUE,
            self.ADDRESS.VELOCITY_ACTUAL_VALUE,
            self.ADDRESS.FOLLOWING_ERROR_ACTUAL_VALUE,
            self.ADDRESS.MODES_OF_OPERATION_DISPLAY,
            self.ADDRESS.DIGITAL_INPUTS
        ]

        # Create rx and tx map integers
        rx_address_ints = make_pdo_mapping(ppm_rx)
        tx_address_ints = make_pdo_mapping(ppm_tx)

        # Assign rx map
        self._sdo_write(self.ADDRESS.NUMBER_OF_MAPPED_OBJECTS_IN_RXPDO_1, 0)
        for i, addressInt in enumerate(rx_address_ints):
            self._sdo_write(EPOS4Obj(0x1600, i + 1, 'I', 32), addressInt)
        self._sdo_write(self.ADDRESS.NUMBER_OF_MAPPED_OBJECTS_IN_RXPDO_1, len(ppm_rx))

        # Assign tx map
        self._sdo_write(self.ADDRESS.NUMBER_OF_MAPPED_OBJECTS_IN_TXPDO_1, 0)
        for i, addressInt in enumerate(tx_address_ints):
            self._sdo_write(EPOS4Obj(0x1A00, i + 1, 'I', 32), addressInt)
        self._sdo_write(self.ADDRESS.NUMBER_OF_MAPPED_OBJECTS_IN_TXPDO_1, len(ppm_tx))

        self.currentRxPDOMap = ppm_rx
        self.currentTxPDOMap = ppm_tx

        # Configure Digital Inputs (example)
        self._sdo_write(self.ADDRESS.DIGITAL_INPUT_CONFIGURATION_DGIN_1, 255)
        self._sdo_write(self.ADDRESS.DIGITAL_INPUT_CONFIGURATION_DGIN_2, 1)
        self._sdo_write(self.ADDRESS.DIGITAL_INPUT_CONFIGURATION_DGIN_1, 0)

        # Set the home offset move distance
        getLogger(__name__).debug(f"Configuring device {self} complete.")

        # self.config_drive(enable_magnetic_tape=self.use_ssi_encoder)

    def config_drive(self, enable_magnetic_tape=False, motor_configuration=CSU_ECmax16_283828_config(),
                        gear_configuration=CSU_planetary_gearhead_GP16A_138342_config(),
                        digital_incremental_encoder_configuration=CSU_ENC16EASY_499361_config(),
                        ssi_encoder_configuration=CSU_SSI_encoder_RLM2sJF11B_config()):

        self._sdo_write(self.ADDRESS.NODE_ID, self.node)

        # Teach the EPOS about the motor
        self._set_motor_data(motor_configuration.nominal_current_ma, motor_configuration.output_current_limit_ma,
                       motor_configuration.thermal_time_constant_winding_ms, motor_configuration.torque_constant_uNm_A)
        self._set_gear_data(gear_configuration.gear_reduction_numerator,
                      gear_configuration.gear_reduction_denominator, gear_configuration.gear_max_input_speed_rpm,
                      gear_configuration.gear_orientation)
        self._set_incremental_encoder_data(digital_incremental_encoder_configuration.number_of_pulses_per_turn,
                                             digital_incremental_encoder_configuration.index,
                                             digital_incremental_encoder_configuration.direction,
                                             digital_incremental_encoder_configuration.method)
        self._set_ssi_encoder_data(ssi_encoder_configuration.data_rate_kbps,
                                  ssi_encoder_configuration.encoding_type, ssi_encoder_configuration.direction,
                                  ssi_encoder_configuration.timeout_time_us,
                                  ssi_encoder_configuration.number_of_multi_turn_bits,
                                  ssi_encoder_configuration.number_of_single_turn_bits)


        self._set_control_scheme(enable_magnetic_tape=enable_magnetic_tape)
        self.dc_sync(act=True, sync0_cycle_time=1000000)

    def _set_motor_data(self, nominal_current_ma, output_current_limit_ma, number_of_pole_pairs,
                       thermal_time_constant_winding_s, torque_constant_uNm_A):
        self._sdo_write(self.ADDRESS.NOMINAL_CURRENT_MA, nominal_current_ma)
        self._sdo_write(self.ADDRESS.OUTPUT_CURRENT_LIMIT_MA,  output_current_limit_ma)
        self._sdo_write(self.ADDRESS.NUMBER_OF_POLE_PAIRS, number_of_pole_pairs)
        self._sdo_write(self.ADDRESS.THERMAL_TIME_CONSTANT_WINDING_DS, thermal_time_constant_winding_s*10)
        self._sdo_write(self.ADDRESS.TORQUE_CONSTANT_UNM_A, torque_constant_uNm_A)

    def _set_incremental_encoder_data(self, number_of_pulses_per_turn, index, direction, method):
        direction_offset = 4
        method_offset = 9
        type = index | (direction << direction_offset) | (method << method_offset)
        self._sdo_write(self.ADDRESS.DIGITAL_INCREMENTAL_ENCODER_1, number_of_pulses_per_turn)
        self._sdo_write(self.ADDRESS.DIGITAL_INCREMENTAL_ENCODER_1_TYPE, type)

    def _set_gear_data(self, gear_reduction_numerator, gear_reduction_denominator,
                 gear_max_input_speed_rpm, gear_orientation):
        self._sdo_write(self.ADDRESS.GEAR_REDUCTION_NUMERATOR, gear_reduction_numerator)
        self._sdo_write(self.ADDRESS.GEAR_REDUCTION_DENOMINATOR, gear_reduction_denominator)
        self._sdo_write(self.ADDRESS.GEAR_MAX_INPUT_SPEED_RPM, gear_max_input_speed_rpm)
        self._sdo_write(self.ADDRESS.GEAR_ORIENTATION, gear_orientation)

    def _set_ssi_encoder_data(self, data_rate, encoding_type, direction, check_frame, timeout_time_us,
                             number_of_multiturn_bits, number_of_singleturn_bits, power_up_time_ms):

        direction_offset = 4
        check_frame_offset = 8
        encoding = encoding_type | (direction << direction_offset)

        multiturn_offset = 16
        singleturn_offset = 8
        position_bits = (number_of_multiturn_bits << multiturn_offset) | (number_of_singleturn_bits << singleturn_offset)

        self._sdo_write(self.ADDRESS.SSI_DATA_RATE_KBPS, data_rate)
        self._sdo_write(self.ADDRESS.SSI_NUMBER_OF_BITS, position_bits)
        self._sdo_write(self.ADDRESS.SSI_ENCODING_TYPE, encoding)
        self._sdo_write(self.ADDRESS.SSI_TIMEOUT_TIME_US , timeout_time_us)
        self._sdo_write(self.ADDRESS.SSI_POWER_UP_TIME_MS, power_up_time_ms)
        # self._sdo_write(self.ADDRESS.SSI_COMMUTATION_OFFSET_VALUE, commutation_offset)

    def _set_control_scheme(self, enable_magnetic_tape=False):

        sensor_type1 = 0x1  # 0=none 1=dig inc 1

        # 0=none, 1=dig inc 2, 2=analog, 3=ssi
        sensor_type2 = 0x3 if enable_magnetic_tape else 0x0

        sensor_type3 = 0x10 # 0=none 0x10=hall EC motors

        types = [sensor_type1, sensor_type2, sensor_type3]
        offsets = [0, 8, 16]
        sensor_type = 0
        for t, o in zip(types, offsets):
            sensor_type |= t << o

        self._sdo_write(self.ADDRESS.AXIS_SENSORS_CONFIG, sensor_type) #1048577 w/o ssi

        SENSOR_NONE = 0
        SENSOR1 = 1     #digital inc 1
        SENSOR2 = 2     #ssi mag tape
        SENSOR3 = 3     #motor hall sensor

        ON_MOTOR = 0
        ON_GEAR = 1

        #communtation sensors (SEN1&3) must be "on motor"
        #aux sensor must be "on shaft" if enabled
        #process ref val gear pos must be that of the main sensor
        aux_sen = SENSOR1 if enable_magnetic_tape else SENSOR_NONE  #cf. 6.2.49.2 must be on motor shaft
        main_sen = SENSOR2 if enable_magnetic_tape else SENSOR1

        position_control_structure = 2 if enable_magnetic_tape else 1
        velocity_control_structure = 1

        control = (ON_MOTOR<<28 | # sen3 position on motor
                   enable_magnetic_tape<<26 | # sen2 undefined or on gear
                   ON_MOTOR<<24 | #sen1 on motor
                   aux_sen << 20 |
                   main_sen << 16 |
                   (ON_GEAR if enable_magnetic_tape else ON_MOTOR) <<14 | # process value ref
                   1<<12 |#gear is present
                   position_control_structure << 8 |
                   velocity_control_structure <<4 |
                   1 # current_control_tructure )
                   )

        #w/o ssi (initial ishaft and hall only testing
        #control was 0x11111
        # main_sen = 1 = sensor 1 = digital encoder
        # aux_sen = 0
        # velocity_control_structure = 1
        # position_control_structure = 1
        # proc_val_ref = 0
        self._sdo_write(self.ADDRESS.AXIS_CONTROL_STRUCTURE, control) # 69905 w/o ssi

        #default is 0x31 which is what we want
        # self._sdo_write(self.ADDRESS.AXIS_COMMUTATION_SENSORS, 0x31) #0x31 w/o ssi

        clockwise_positive = False
        axis_polarity = 0x1 if clockwise_positive else 0x0
        axis_config_misc = axis_polarity # see 6.2.49.4
        self._sdo_write(self.ADDRESS.AXIS_CONFIG_MISC, axis_config_misc) # 0 w/o ssi

        pid_params = self.DUAL_LOOP_PID_PARAMS if enable_magnetic_tape else self.SINGLE_LOOP_PID_PARAMS

        self._sdo_write(self.ADDRESS.CURRENT_CONTROLLER_P_GAIN, pid_params.current_controller_p_gain)
        self._sdo_write(self.ADDRESS.CURRENT_CONTROLLER_I_GAIN, pid_params.current_controller_i_gain)
        self._sdo_write(self.ADDRESS.POSITION_CONTROLLER_P_GAIN, pid_params.position_controller_p_gain)
        self._sdo_write(self.ADDRESS.POSITION_CONTROLLER_I_GAIN, pid_params.position_controller_i_gain)
        self._sdo_write(self.ADDRESS.POSITION_CONTROLLER_D_GAIN, pid_params.position_controller_d_gain)
        self._sdo_write(self.ADDRESS.POSITION_CONTROLLER_FF_VELOCITY_GAIN, pid_params.position_controller_ff_velocity_gain)
        self._sdo_write(self.ADDRESS.POSITION_CONTROLLER_FF_ACCELERATION_GAIN, pid_params.position_controller_ff_acceleration_gain)
        self._sdo_write(self.ADDRESS.VELOCITY_CONTROLLER_P_GAIN, pid_params.velocity_controller_p_gain)
        self._sdo_write(self.ADDRESS.VELOCITY_CONTROLLER_I_GAIN, pid_params.velocity_controller_i_gain)
        self._sdo_write(self.ADDRESS.VELOCITY_CONTROLLER_FF_VELOCITY_GAIN, pid_params.velocity_controller_ff_velocity_gain)
        self._sdo_write(self.ADDRESS.VELOCITY_CONTROLLER_FF_ACCELERATION_GAIN, pid_params.velocity_controller_ff_acceleration_gain)


class BrakeMotor(EPOS4Motor):
    def __init__(self, *args, **kwargws):
        raise NotImplementedError

    def engage(self):
        raise NotImplementedError

    def disengage(self):
        raise NotImplementedError


class CSUHardware:
    def __init__(self, config:CSUHardwareConfig|str='csu.yaml', connect=False):

        if not isinstance(config, CSUHardwareConfig):
            # Load and parse the configuration YAML file
            try:
                with open(config, 'r') as f:
                    config: dict = yaml.full_load(config)['hardware']
            except Exception as e:
                raise ValueError(f"Failed to load configuration file '{config}': {e}")

        self.configuration :CSUHardwareConfig = config

        # self.left_brake = BrakeMotor(self.configuration.left_brake)
        # self.left_brake = BrakeMotor(self.configuration.right_brake)

        # TODO I'm not thrilled with implementing this via functools partial as it does require a better understanding
        #  of python. Its probably clear enough that it can serve as a teaching moment if necessary
        self.slave_types = {id: functools.partial(BarMotor, kwargs={'use_ssi_encoder':cfg.use_ssi_encoder})
                            for id, cfg in self.configuration.bar_configs.items()}

        # Create the bus
        self.bus = EPOS4Bus(self.configuration.ethercat_device)
        if connect:
            self.reset_bus()

    def reset_bus(self):
        self.bus.initialize(self.slave_types)
        #TODO check for all slaves present

    def calibrate(self, one_at_a_time=False):
        self.bus.disable_pdo()
        time.sleep(.5)
        for s in self.bus.slaves:
            if self.configuration.bar_by_dev_id(s.node).reversed:
                method = HomingMethods.CURRENT_THRESHOLD_POS_SPEED_AND_INDEX
            else:
                method = HomingMethods.CURRENT_THRESHOLD_NEG_SPEED_AND_INDEX
            s.home_via_method(method, current_threshold=450, monitor=None, timeout=30, setup_only=not one_at_a_time)
            time.sleep(.2)

        if not one_at_a_time:
            time.sleep(.5)
            self.bus.enable_pdo()
            time.sleep(.5)
            self.bus.execute_homing()

    def configure(self, mask_config:MaskConfig, speed=8000):
        bar_pos = self.configuration.compute_bar_count_positions(mask_config.to_dict())
        self.bus.enable_pdo()
        self.bus.move_to(bar_pos, blocking=False, speed=speed)
        self.bus.disable_pdo()

    def halt(self):
        self.bus.disable_pdo()
        for s in self.bus.slaves:
            s.halt()

    def status(self, verbose:bool=False)->dict:
        ret = {}
        status_func = 'debug_info_sdo' if verbose else 'info_sdo'
        status = {id: [getattr(self.bus.slaves[bp.left.bus_id], status_func),
                       getattr(self.bus.slaves[bp.right.bus_id], status_func)]
                for id, bp in self.configuration.bar_pairs.items()}
        x = {b['node']: b['position'] for bp in status.values() for b in bp}
        for k in status:
            status[k][0]['error_code'] = repr(status[k][0]['error_code'])
            status[k][1]['error_code'] = repr(status[k][1]['error_code'])
            try:
                status[k][0]['statusword'] = repr(status[k][0]['statusword'])
                status[k][1]['statusword'] = repr(status[k][1]['statusword'])
            except KeyError:
                pass
        ret['status'] = status
        ret['mask'] = self.configuration.compute_pos_width_dict(x)
        return ret

    def clear_faults(self):
        for s in self.bus.slaves:
            s.clear_faults()

    def terminate_control(self):
        self.bus.disable_pdo()
        self.bus.close()

