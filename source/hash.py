import logging

from enum import Enum, unique
from typing import Tuple


_LOGGER = logging.getLogger('mme')


@unique
class Hash(Enum):
    Vehicle                 = 'FFFF:9002:vehicle'
    KeyState                = '0716:411F:key_state'
    InferredKey             = '0726:417D:inferred_key'
    EvseType                = '07E4:4851:evse_type'
    ChargingStatus          = '07E4:484D:charging_status'
    GearCommanded           = '07E2:1E12:gear_commanded'
    ChargePlugConnected     = '07E2:4843:charge_plug_connected'

    HiresSpeed              = '07E0:1505:hires_speed'
    HiresSpeedMax           = 'FFFF:1505:hires_speed_max'
    HiresOdometer           = '0720:404C:hires_odometer'
    LoresOdometer           = '07E4:DD01:lores_odometer'

    EngineStartNormal       = '0726:41B9:engine_start_normal'
    EngineStartDisable      = '0726:41B9:engine_start_disable'
    EngineStartRemote       = '0726:41B9:engine_start_remote'
    EngineStartExtended     = '0726:41B9:engine_start_extended'

    HvbVoltage              = '07E4:480D:hvb_voltage'
    HvbCurrent              = '07E4:48F9:hvb_current'
    HvbPower                = 'FFFF:8000:hvb_power'
    HvbPowerMax             = 'FFFF:8000:hvb_power_max'
    HvbPowerMin             = 'FFFF:8000:hvb_power_min'
    HvbEnergy               = 'FFFF:8000:hvb_energy'
    HvbEnergyLost           = 'FFFF:8000:hvb_energy_lost'
    HvbEnergyGained         = 'FFFF:8000:hvb_energy_gained'
    HvbSoC                  = '07E4:4801:hvb_soc'
    HvbSoCD                 = '07E4:4845:hvb_socd'
    HvbEtE                  = '07E4:4848:hvb_ete'
    HvbTemp                 = '07E4:4800:hvb_temp'
    HvbCHOp                 = '07E7:48DF:hvb_chop'
    HvbCHP                  = '07E7:48DE:hvb_chp'
    HvbChargeCurrentRequested  = '07E4:4842:hvb_charge_current_requested'
    HvbMaxChargeCurrent     = '07E4:48BC:hvb_max_charge_current'

    LvbVoltage              = '0726:402A:lvb_voltage'
    LvbCurrent              = '0726:402B:lvb_current'
    LvbPower                = 'FFFF:8001:lvb_power'
    LvbEnergy               = 'FFFF:8001:lvb_energy'
    LvbSoC                  = '0726:4028:lvb_soc'
    LvbDcdcLvCurrent        = '07E4:4836:lvb_dcdc_lv_current'
    LvbDcdcHvCurrent        = '07E4:483A:lvb_dcdc_hv_current'
    LvbDcdcEnable           = '0746:483D:lvb_dcdc_enable'

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
    GpsElapsed              = '07D0:8012:gps_elapsed'
    GpsSource               = '07D0:8012:gps_source'
    GpsElevationMin         = '07D0:8012:gps_elevation_min'
    GpsElevationMax         = '07D0:8012:gps_elevation_max'

    InteriorTemperature     = '07E2:DD04:interior_temp'
    ExteriorTemperature     = '07E6:DD05:exterior_temp'

    CS_ChargerType          = 'FFFF:9000:cs_charger_type'
    CS_TimeStart            = 'FFFF:9000:cs_time_start'
    CS_TimeEnd              = 'FFFF:9000:cs_time_end'
    CS_StartSoCD            = 'FFFF:9000:cs_start_socd'
    CS_EndSoCD              = 'FFFF:9000:cs_end_socd'
    CS_StartEtE             = 'FFFF:9000:cs_start_ete'
    CS_EndEte               = 'FFFF:9000:cs_end_ete'
    CS_Odometer             = 'FFFF:9000:cs_odometer'
    CS_Latitude             = 'FFFF:9000:cs_latitude'
    CS_Longitude            = 'FFFF:9000:cs_longitude'
    CS_MaxInputPower        = 'FFFF:9000:cs_max_input_power'
    CS_ChargingEfficiency   = 'FFFF:9000:cs_charging_efficiency'
    CS_WhAdded              = 'FFFF:9000:cs_wh_added'
    CS_WhUsed               = 'FFFF:9000:cs_wh_used'

    TR_TimeStart            = 'FFFF:9001:tr_time_start'
    TR_TimeEnd              = 'FFFF:9001:tr_time_end'
    TR_Distance             = 'FFFF:9001:tr_distance'
    TR_ElevationChange      = 'FFFF:9001:tr_elevation_change'

    TR_MaxElevation         = 'FFFF:9001:tr_elevation_max'
    TR_MinElevation         = 'FFFF:9001:tr_elevation_min'
    TR_EnergyUsed           = 'FFFF:9001:tr_wh_used'
    TR_Efficiency           = 'FFFF:9001:tr_efficiency'
    TR_EnergyGained         = 'FFFF:9001:tr_wh_gained'
    TR_EnergyLost           = 'FFFF:9001:tr_wh_lost'
    TR_EnergyEfficiency     = 'FFFF:9001:tr_energy_efficiency'
    TR_MaxSpeed             = 'FFFF:9001:tr_max_speed'
    TR_AverageSpeed         = 'FFFF:9001:tr_average_speed'

    TR_OdometerStart        = 'FFFF:9001:tr_odometer_start'
    TR_OdometerEnd          = 'FFFF:9001:tr_odometer_end'
    TR_LatitudeStart        = 'FFFF:9001:tr_latitude_start'
    TR_LatitudeEnd          = 'FFFF:9001:tr_latitude_end'
    TR_LongitudeStart       = 'FFFF:9001:tr_longitude_start'
    TR_LongitudeEnd         = 'FFFF:9001:tr_longitude_end'
    TR_ElevationStart       = 'FFFF:9001:tr_elevation_start'
    TR_ElevationEnd         = 'FFFF:9001:tr_elevation_end'
    TR_SocDStart            = 'FFFF:9001:tr_socd_start'
    TR_SocDEnd              = 'FFFF:9001:tr_socd_end'
    TR_EtEStart             = 'FFFF:9001:tr_ete_start'
    TR_EtEEnd               = 'FFFF:9001:tr_ete_end'
    TR_ExteriorStart        = 'FFFF:9001:tr_exterior_start'
    TR_ExteriorEnd          = 'FFFF:9001:tr_exterior_end'


_db_stuff = {
    Hash.KeyState:                  {'db_name': 'key_state',                'type': 'int'},
    Hash.InferredKey:               {'db_name': 'inferred_key',             'type': 'int'},
    Hash.EvseType:                  {'db_name': 'evse_type',                'type': 'int'},
    Hash.ChargingStatus:            {'db_name': 'charging_status',          'type': 'int'},
    Hash.GearCommanded:             {'db_name': 'gear_commanded',           'type': 'int'},
    Hash.ChargePlugConnected:       {'db_name': 'charge_plug_connected',    'type': 'int'},

    Hash.HiresSpeed:                {'db_name': 'hires_speed',              'type': 'float'},
    Hash.HiresSpeedMax:             {'db_name': 'hires_speed_max',          'type': 'float'},
    Hash.HiresOdometer:             {'db_name': 'hires_odometer',           'type': 'float'},
    Hash.LoresOdometer:             {'db_name': 'lores_odometer',           'type': 'float'},

    Hash.EngineStartNormal:         {'db_name': 'engine_start_normal',       'type': 'int'},
    Hash.EngineStartDisable:        {'db_name': 'engine_start_disable',      'type': 'int'},
    Hash.EngineStartRemote:         {'db_name': 'engine_start_remote',       'type': 'int'},
    Hash.EngineStartExtended:       {'db_name': 'engine_start_extended',     'type': 'int'},

    Hash.HvbVoltage:                {'db_name': 'hvb_voltage',               'type': 'float'},
    Hash.HvbCurrent:                {'db_name': 'hvb_current',               'type': 'float'},
    Hash.HvbPower:                  {'db_name': 'hvb_power',                 'type': 'int'},
    Hash.HvbPowerMax:               {'db_name': 'hvb_power_max',             'type': 'int'},
    Hash.HvbPowerMin:               {'db_name': 'hvb_power_min',             'type': 'int'},
    Hash.HvbEnergy:                 {'db_name': 'hvb_energy',                'type': 'int'},
    Hash.HvbEnergyLost:             {'db_name': 'hvb_energy_lost',           'type': 'int'},
    Hash.HvbEnergyGained:           {'db_name': 'hvb_energy_gained',         'type': 'int'},
    Hash.HvbSoC:                    {'db_name': 'hvb_soc',                   'type': 'float'},
    Hash.HvbSoCD:                   {'db_name': 'hvb_socd',                  'type': 'float'},
    Hash.HvbEtE:                    {'db_name': 'hvb_ete',                   'type': 'int'},
    Hash.HvbTemp:                   {'db_name': 'hvb_temp',                  'type': 'int'},
    Hash.HvbCHOp:                   {'db_name': 'hvb_chop',                  'type': 'int'},
    Hash.HvbCHP:                    {'db_name': 'hvb_chp',                   'type': 'int'},

    Hash.LvbVoltage:                {'db_name': 'lvb_voltage',               'type': 'float'},
    Hash.LvbCurrent:                {'db_name': 'lvb_current',               'type': 'float'},
    Hash.LvbPower:                  {'db_name': 'lvb_power',                 'type': 'int'},
    Hash.LvbEnergy:                 {'db_name': 'lvb_energy',                'type': 'int'},
    Hash.LvbSoC:                    {'db_name': 'lvb_soc',                   'type': 'float'},
    Hash.LvbDcdcLvCurrent:          {'db_name': 'lvb_dcdc_lv_current',       'type': 'int'},
    Hash.LvbDcdcHvCurrent:          {'db_name': 'lvb_dcdc_hv_current',       'type': 'int'},
    Hash.LvbDcdcEnable:             {'db_name': 'lvb_dcdc_enable',           'type': 'int'},

    Hash.ChargerInputVoltage:       {'db_name': 'charger_input_voltage',     'type': 'float'},
    Hash.ChargerInputCurrent:       {'db_name': 'charger_input_current',     'type': 'float'},
    Hash.ChargerInputPower:         {'db_name': 'charger_input_power',       'type': 'int'},
    Hash.ChargerInputPowerMax:      {'db_name': 'charger_input_power_max',   'type': 'int'},
    Hash.ChargerInputEnergy:        {'db_name': 'charger_input_energy',      'type': 'int'},

    Hash.ChargerOutputVoltage:      {'db_name': 'charger_output_voltage',    'type': 'float'},
    Hash.ChargerOutputCurrent:      {'db_name': 'charger_output_current',    'type': 'float'},
    Hash.ChargerOutputPower:        {'db_name': 'charger_output_power',      'type': 'int'},
    Hash.ChargerOutputPowerMax:     {'db_name': 'charger_output_power_max',  'type': 'int'},
    Hash.ChargerOutputEnergy:       {'db_name': 'charger_output_energy',     'type': 'int'},

    Hash.GpsLatitude:               {'db_name': 'gps_latitude',              'type': 'float'},
    Hash.GpsLongitude:              {'db_name': 'gps_longitude',             'type': 'float'},
    Hash.GpsElevation:              {'db_name': 'gps_elevation',             'type': 'int'},
    Hash.GpsSpeed:                  {'db_name': 'gps_speed',                 'type': 'float'},
    Hash.GpsBearing:                {'db_name': 'gps_bearing',               'type': 'int'},
    Hash.GpsFix:                    {'db_name': 'gps_fix',                   'type': 'int'},
    Hash.GpsElapsed:                {'db_name': 'gps_elapsed',               'type': 'float'},
    Hash.GpsSource:                 {'db_name': 'gps_source',                'type': 'int'},
    Hash.GpsElevationMin:           {'db_name': 'gps_elevation_min',         'type': 'int'},
    Hash.GpsElevationMax:           {'db_name': 'gps_elevation_max',         'type': 'int'},

    Hash.InteriorTemperature:       {'db_name': 'interior_temp',             'type': 'int'},
    Hash.ExteriorTemperature:       {'db_name': 'exterior_temp',             'type': 'int'},

    Hash.Vehicle:                   {'db_name': 'vehicle',                   'type': 'str'},

    Hash.CS_ChargerType:            {'db_name': 'charger_type',              'type': 'str'},
    Hash.CS_TimeStart:              {'db_name': 'cs_time_start',             'type': 'int'},
    Hash.CS_TimeEnd:                {'db_name': 'cs_time_end',               'type': 'int'},
    Hash.CS_StartSoCD:              {'db_name': 'cs_start_socd',             'type': 'float'},
    Hash.CS_EndSoCD:                {'db_name': 'cs_end_socd',               'type': 'float'},
    Hash.CS_StartEtE:               {'db_name': 'cs_start_ete',              'type': 'int'},
    Hash.CS_EndEte:                 {'db_name': 'cs_end_ete',                'type': 'int'},
    Hash.CS_Odometer:               {'db_name': 'cs_odometer',               'type': 'float'},
    Hash.CS_Latitude:               {'db_name': 'cs_latitude',               'type': 'float'},
    Hash.CS_Longitude:              {'db_name': 'cs_longitude',              'type': 'float'},
    Hash.CS_MaxInputPower:          {'db_name': 'cs_max_input_power',        'type': 'int'},
    Hash.CS_ChargingEfficiency:     {'db_name': 'cs_efficiency',             'type': 'float'},
    Hash.CS_WhAdded:                {'db_name': 'cs_wh_added',               'type': 'int'},
    Hash.CS_WhUsed:                 {'db_name': 'cs_wh_used',                'type': 'int'},

    Hash.TR_TimeStart:              {'db_name': 'tr_time_start',             'type': 'int'},
    Hash.TR_TimeEnd:                {'db_name': 'tr_time_end',               'type': 'int'},
    Hash.TR_Distance:               {'db_name': 'tr_distance',               'type': 'float'},
    Hash.TR_ElevationChange:        {'db_name': 'tr_elevation_change',       'type': 'int'},
    Hash.TR_MaxElevation:           {'db_name': 'tr_elevation_max',          'type': 'int'},
    Hash.TR_MinElevation:           {'db_name': 'tr_elevation_min',          'type': 'int'},
    Hash.TR_EnergyUsed:             {'db_name': 'tr_wh_used',                'type': 'int'},
    Hash.TR_EnergyGained:           {'db_name': 'tr_wh_gained',              'type': 'int'},
    Hash.TR_EnergyEfficiency:       {'db_name': 'tr_energy_efficiency',      'type': 'float'},
    Hash.TR_EnergyLost:             {'db_name': 'tr_wh_lost',                'type': 'int'},
    Hash.TR_MaxSpeed:               {'db_name': 'tr_max_speed',              'type': 'float'},
    Hash.TR_AverageSpeed:           {'db_name': 'tr_average_speed',          'type': 'float'},

    Hash.TR_OdometerStart:          {'db_name': 'tr_odometer_start',         'type': 'float'},
    Hash.TR_OdometerEnd:            {'db_name': 'tr_odometer_end',           'type': 'float'},
    Hash.TR_LatitudeStart:          {'db_name': 'tr_latitude_start',         'type': 'float'},
    Hash.TR_LatitudeEnd:            {'db_name': 'tr_latitude_end',           'type': 'float'},
    Hash.TR_LongitudeStart:         {'db_name': 'tr_longitude_start',        'type': 'float'},
    Hash.TR_LongitudeEnd:           {'db_name': 'tr_longitude_end',          'type': 'float'},
    Hash.TR_ElevationStart:         {'db_name': 'tr_elevation_start',        'type': 'int'},
    Hash.TR_ElevationEnd:           {'db_name': 'tr_elevation_end',          'type': 'int'},
    Hash.TR_ExteriorStart:          {'db_name': 'tr_exterior_start',         'type': 'int'},
    Hash.TR_ExteriorEnd:            {'db_name': 'tr_exterior_end',           'type': 'int'},
    Hash.TR_SocDStart:              {'db_name': 'tr_socd_start',             'type': 'float'},
    Hash.TR_SocDEnd:                {'db_name': 'tr_socd_end',               'type': 'float'},
    Hash.TR_EtEStart:               {'db_name': 'tr_ete_start',              'type': 'int'},
    Hash.TR_EtEEnd:                 {'db_name': 'tr_ete_end',                'type': 'int'},
    Hash.TR_EnergyGained:           {'db_name': 'tr_energy_gained',          'type': 'int'},
    Hash.TR_EnergyLost:             {'db_name': 'tr_energy_lost',            'type': 'int'},
}

def get_hash(hash_str: str) -> Hash:
    try:
        return Hash(hash_str)
    except ValueError:
        _LOGGER.error(f"Hash error: no hash defined for hash string '{hash_str}'")
        return None


def get_hash_fields(hash: Hash) -> Tuple[int, int, str]:
    hash_fields = hash.value.split(':')
    return int(hash_fields[0], base=16), int(hash_fields[1], base=16), hash_fields[2]


def get_db_fields(hash: Hash) -> Tuple[str, type]:
    db_type = _db_stuff.get(hash).get('type')
    db_name = _db_stuff.get(hash).get('db_name')
    return db_name, db_type
