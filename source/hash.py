import logging

from enum import Enum, unique
from exceptions import RuntimeError


_LOGGER = logging.getLogger('mme')


@unique
class Hash(Enum):
    KeyState                = '0716:411F:key_state'
    InferredKey             = '0726:417D:inferred_key'
    EvseType                = '07E4:4851:evse_type'
    ChargingStatus          = '07E4:484D:charging_status'
    GearCommanded           = '07E2:1E12:gear_commanded'
    ChargePlugConnected     = '07E2:4843:charge_plug_connected'

    HiresSpeed              = '07E0:1505:hires_speed'
    HiresOdometer           = '0720:404C:hires_odometer'
    LoresOdometer           = '07E4:DD01:lores_odometer'

    EngineStartNormal       = '0726:41B9:engine_start_normal'
    EngineStartDisable      = '0726:41B9:engine_start_disable'
    EngineStartRemote       = '0726:41B9:engine_start_remote'
    EngineStartExtended     = '0726:41B9:engine_start_extended'

    HvbVoltage              = '07E4:480D:hvb_voltage'
    HvbCurrent              = '07E4:48F9:hvb_current'
    HvbPower                = 'FFFF:8000:hvb_power'
    HvbEnergy               = 'FFFF:8000:hvb_energy'
    HvbEnergyLost           = 'FFFF:8000:hvb_energy_lost'
    HvbEnergyGained         = 'FFFF:8000:hvb_energy_gained'
    HvbSoC                  = '07E4:4801:hvb_soc'
    HvbSoCD                 = '07E4:4845:hvb_socd'
    HvbEtE                  = '07E4:4848:hvb_ete'
    HvbTemp                 = '07E4:4800:hvb_temp'
    HvbCHOp                 = '07E7:48DF:hvb_chop'
    HvbCHP                  = '07E7:48DE:hvb_chp'

    LvbVoltage              = '0726:402A:lvb_voltage'
    LvbCurrent              = '0726:402B:lvb_current'
    LvbPower                = 'FFFF:8001:lvb_power'
    LvbEnergy               = 'FFFF:8001:lvb_energy'
    LvbSoC                  = '0726:4028:lvb_soc'

    ChargerInputVoltage     = '07E2:485E:charger_input_voltage'
    ChargerInputCurrent     = '07E2:485F:charger_input_current'
    ChargerInputPower       = 'FFFF:8002:charger_input_power'
    ChargerInputPowerMax    = 'FFFF:8002:charger_input_power_max'
    ChargerInputEnergy      = 'FFFF:8002:charger_input_energy'

    ChargerOutputVoltage    = '07E2:484A:charger_output_voltage'
    ChargerOutputCurrent    = '07E2:4850:charger_output_current'
    ChargerOutputPower      = 'FFFF:8003:charger_output_power'
    ChargerOutputPowerMax   = 'FFFF:8003:charger_output_power_max'
    ChargerOutputEnergy     = 'FFFF:8003:charger_output_energy'

    GpsLatitude             = '07D0:8012:gps_latitude'
    GpsLongitude            = '07D0:8012:gps_longitude'
    GpsElevation            = '07D0:8012:gps_elevation'
    GpsSpeed                = '07D0:8012:gps_speed'
    GpsBearing              = '07D0:8012:gps_bearing'
    GpsFix                  = '07D0:8012:gps_fix'

    InteriorTemperature     = '07E2:DD04:interior_temp'
    ExteriorTemperature     = '07E6:DD05:exterior_temp'


def get_hash(hash_str: str) -> Hash:
    try:
        return Hash(hash_str)
    except ValueError:
        return None #raise RuntimeError(f"Hash error: no entry for hash string '{hash_str}'")
