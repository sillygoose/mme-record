import logging

from enum import Enum, unique
from typing import Tuple


_LOGGER = logging.getLogger('mme')


@unique
class Hash(Enum):
    Vehicle                     = 'FFFF:9002:vehicle:str'
    KeyState                    = '0716:411F:key_state:int'
    InferredKey                 = '0726:417D:inferred_key:int'
    EvseType                    = '07E4:4851:evse_type:int'
    ChargingStatus              = '07E4:484D:charging_status:int'
    GearCommanded               = '07E2:1E12:gear_commanded:int'
    ChargePlugConnected         = '07E2:4843:charge_plug_connected:bool'

    HiresSpeed                  = '07E0:1505:hires_speed:float'
    HiresSpeedMax               = 'FFFF:1505:hires_speed_max:float'
    HiresOdometer               = '0720:404C:hires_odometer:float'
    LoresOdometer               = '07E4:DD01:lores_odometer:float'

    EngineStartNormal           = '0726:41B9:engine_start_normal:bool'
    EngineStartDisable          = '0726:41B9:engine_start_disable:bool'
    EngineStartRemote           = '0726:41B9:engine_start_remote:bool'
    EngineStartExtended         = '0726:41B9:engine_start_extended:bool'

    HvbVoltage                  = '07E4:480D:hvb_voltage:float'
    HvbCurrent                  = '07E4:48F9:hvb_current:float'
    HvbPower                    = 'FFFF:8000:hvb_power:int'
    HvbPowerMax                 = 'FFFF:8000:hvb_power_max:int'
    HvbPowerMin                 = 'FFFF:8000:hvb_power_min:int'
    HvbEnergy                   = 'FFFF:8000:hvb_energy:int'
    HvbEnergyLost               = 'FFFF:8000:hvb_energy_lost:int'
    HvbEnergyGained             = 'FFFF:8000:hvb_energy_gained:int'
    HvbSoH                      = '07E4:490C:hvb_soh:float'
    HvbSoC                      = '07E4:4801:hvb_soc:float'
    HvbSoCD                     = '07E4:4845:hvb_socd:float'
    HvbEtE                      = '07E4:4848:hvb_ete:int'
    HvbTemp                     = '07E4:4800:hvb_temp:int'
    HvbCHOp                     = '07E7:48DF:hvb_chop:int'
    HvbCHP                      = '07E7:48DE:hvb_chp:int'
    HvbChargeCurrentRequested   = '07E4:4842:hvb_charge_current_requested:float'
    HvbMaxChargeCurrent         = '07E4:48BC:hvb_max_charge_current:float'

    LvbVoltage                  = '0726:402A:lvb_voltage:float'
    LvbCurrent                  = '0726:402B:lvb_current:float'
    LvbPower                    = 'FFFF:8001:lvb_power:int'
    LvbEnergy                   = 'FFFF:8001:lvb_energy:int'
    LvbSoC                      = '0726:4028:lvb_soc:float'
    LvbDcdcLvCurrent            = '07E4:4836:lvb_dcdc_lv_current:float' # not implemented
    LvbDcdcHvCurrent            = '07E4:483A:lvb_dcdc_hv_current:float' # not implemented
    LvbDcdcEnable               = '0746:483D:lvb_dcdc_enable:bool'

    ChargerInputVoltage         = '07E2:485E:charger_input_voltage:float'
    ChargerInputCurrent         = '07E2:485F:charger_input_current:float'
    ChargerInputPower           = 'FFFF:8002:charger_input_power:int'
    ChargerInputPowerMax        = 'FFFF:8002:charger_input_power_max:int'
    ChargerInputEnergy          = 'FFFF:8002:charger_input_energy:int'

    ChargerOutputVoltage        = '07E2:484A:charger_output_voltage:float'
    ChargerOutputCurrent        = '07E2:4850:charger_output_current:float'
    ChargerOutputPower          = 'FFFF:8003:charger_output_power:int'
    ChargerOutputPowerMax       = 'FFFF:8003:charger_output_power_max:int'
    ChargerOutputEnergy         = 'FFFF:8003:charger_output_energy:int'

    GpsLatitude                 = '07D0:8012:gps_latitude:float'
    GpsLongitude                = '07D0:8012:gps_longitude:float'
    GpsElevation                = '07D0:8012:gps_elevation:int'
    GpsSpeed                    = '07D0:8012:gps_speed:float'
    GpsBearing                  = '07D0:8012:gps_bearing:int'
    GpsFix                      = '07D0:8012:gps_fix:int'
    GpsElapsed                  = '07D0:8012:gps_elapsed:float'
    GpsSource                   = '07D0:8012:gps_source:int'
    GpsElevationMin             = '07D0:8012:gps_elevation_min:int'
    GpsElevationMax             = '07D0:8012:gps_elevation_max:int'

    InteriorTemperature         = '07E2:DD04:interior_temp:int'
    ExteriorTemperature         = '07E6:DD05:exterior_temp:int'
    ExtTemperatureSum           = '07E6:DD05:exterior_temp_sum:int'
    ExtTemperatureCount         = '07E6:DD05:exterior_temp_count:int'

    WhPerKilometerOdometerStart = 'AAAA:0000:wh_per_kilometer_odometer_start:float'
    WhPerKilometerStart         = 'AAAA:0001:wh_per_kilometer_wh_start:int'
    WhPerKilometer              = 'AAAA:0002:wh_per_kilometer:int'
    WhPerGpsSegmentStart        = 'AAAA:0003:wh_per_gps_segment_start:int'
    WhPerGpsSegment             = 'AAAA:0004:wh_per_gps_segment:int'

    CS_ChargerType              = 'FFFF:9000:cs_charger_type:str'
    CS_ChargingEfficiency       = 'FFFF:9000:cs_charging_efficiency:float'
    CS_Odometer                 = 'FFFF:9000:cs_odometer:float'
    CS_Latitude                 = 'FFFF:9000:cs_latitude:float'
    CS_Longitude                = 'FFFF:9000:cs_longitude:float'
    CS_ChargeLocation           = 'FFFF:9000:cs_charge_location:str'
    CS_TimeStart                = 'FFFF:9000:cs_time_start:int'
    CS_TimeEnd                  = 'FFFF:9000:cs_time_end:int'
    CS_MaxInputPower            = 'FFFF:9000:cs_max_input_power:int'
    CS_WhAdded                  = 'FFFF:9000:cs_wh_added:int'
    CS_WhUsed                   = 'FFFF:9000:cs_wh_used:int'

    CS_HvbSoCStart              = 'FFFF:9000:cs_hvb_soc_start:float'
    CS_HvbSoCEnd                = 'FFFF:9000:cs_hvb_soc_end:float'
    CS_HvbEtEStart              = 'FFFF:9000:cs_hvb_ete_start:int'
    CS_HvbEteEnd                = 'FFFF:9000:cs_hvb_ete_end:int'
    CS_HvbSoH                   = 'FFFF:9000:cs_hvb_soh:float'
    CS_HvbTempStart             = 'FFFF:9000:cs_hvb_temp_start:int'
    CS_HvbTempEnd               = 'FFFF:9000:cs_hvb_temp_end:int'
    CS_HvbWhAdded               = 'FFFF:9000:cs_hvb_wh_added:int'

    CS_LvbSoCStart              = 'FFFF:9000:cs_lvb_soc_start:float'
    CS_LvbSoCEnd                = 'FFFF:9000:cs_lvb_soc_end:float'
    CS_LvbWhAdded               = 'FFFF:9000:cs_lvb_wh_added:int'

    TR_TimeStart                = 'FFFF:9001:tr_time_start:int'
    TR_TimeEnd                  = 'FFFF:9001:tr_time_end:int'
    TR_LocationStarting         = 'FFFF:9001:tr_location_start:str'
    TR_LocationEnding           = 'FFFF:9001:tr_location_end:str'
    TR_Distance                 = 'FFFF:9001:tr_distance:float'
    TR_ElevationChange          = 'FFFF:9001:tr_elevation_change:int'

    TR_MaxElevation             = 'FFFF:9001:tr_elevation_max:int'
    TR_MinElevation             = 'FFFF:9001:tr_elevation_min:int'
    TR_HvbPowerMin              = 'FFFF:9001:tr_hvb_power_min:int'
    TR_HvbPowerMax              = 'FFFF:9001:tr_hvb_power_max:int'
    TR_EnergyUsed               = 'FFFF:9001:tr_wh_used:int'
    TR_EnergyGained             = 'FFFF:9001:tr_wh_gained:int'
    TR_EnergyLost               = 'FFFF:9001:tr_wh_lost:int'
    TR_EnergyEfficiency         = 'FFFF:9001:tr_energy_efficiency:float'
    TR_MaxSpeed                 = 'FFFF:9001:tr_max_speed:float'
    TR_AverageSpeed             = 'FFFF:9001:tr_average_speed:float'

    TR_OdometerStart            = 'FFFF:9001:tr_odometer_start:float'
    TR_OdometerEnd              = 'FFFF:9001:tr_odometer_end:float'
    TR_LatitudeStart            = 'FFFF:9001:tr_latitude_start:float'
    TR_LatitudeEnd              = 'FFFF:9001:tr_latitude_end:float'
    TR_LongitudeStart           = 'FFFF:9001:tr_longitude_start:float'
    TR_LongitudeEnd             = 'FFFF:9001:tr_longitude_end:float'
    TR_ElevationStart           = 'FFFF:9001:tr_elevation_start:int'
    TR_ElevationEnd             = 'FFFF:9001:tr_elevation_end:int'
    TR_SocDStart                = 'FFFF:9001:tr_socd_start:float'
    TR_SocDEnd                  = 'FFFF:9001:tr_socd_end:float'
    TR_EtEStart                 = 'FFFF:9001:tr_ete_start:int'
    TR_EtEEnd                   = 'FFFF:9001:tr_ete_end:int'
    TR_ExteriorStart            = 'FFFF:9001:tr_exterior_start:int'
    TR_ExteriorEnd              = 'FFFF:9001:tr_exterior_end:int'
    TR_ExteriorAverage          = 'FFFF:9001:tr_exterior_average:int'


def get_hash(hash: str) -> Hash:
    try:
        hash_int = hash + ':int'
        return Hash(hash_int)
    except ValueError:
        try:
            hash_float = hash + ':float'
            return Hash(hash_float)
        except ValueError:
            try:
                hash_str = hash + ':str'
                return Hash(hash_str)
            except ValueError:
                try:
                    hash_str = hash + ':bool'
                    return Hash(hash_str)
                except ValueError:
                    _LOGGER.error(f"Hash error: no hash defined for hash string '{hash_str}'")
                    return None


def get_hash_fields(hash: Hash) -> Tuple[int, int, str, str]:
    hash_fields = hash.value.split(':')
    return int(hash_fields[0], base=16), int(hash_fields[1], base=16), hash_fields[2]


def get_db_fields(hash: Hash) -> Tuple[str, type]:
    hash_fields = hash.value.split(':')
    db_type = hash_fields[3]
    db_name = hash_fields[2]
    return db_name, db_type
