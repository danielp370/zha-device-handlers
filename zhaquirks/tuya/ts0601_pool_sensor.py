"""Tuya pool sensor."""

import asyncio

from zigpy.quirks.v2 import CustomDeviceV2
from zigpy.quirks.v2.homeassistant import UnitOfElectricPotential, UnitOfTime
from zigpy.quirks.v2.homeassistant.number import NumberDeviceClass
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t

from zhaquirks.tuya import TUYA_QUERY_DATA, EnchantedDevice, TuyaNewManufCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import TuyaMCUCluster, TuyaPowerConfigurationCluster

# Create a quirks v2 of Tuya's EnchantedDevice as we need Tuya spells
EnchantedDevice.__bases__ = (CustomDeviceV2,)


class EnchantedDeviceV2(EnchantedDevice):
    """Updated version of EnchantedDevice based on CustomDeviceV2."""

    tuya_spell_data_query: bool = True  # Enable data query spell


class TuyaPoolManufCluster(TuyaMCUCluster):
    """Tuya Manufacturer cluster with automatic data point refresh logic."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._update_timer_handle = None
        self.check_interval = 60
        self.next_refresh_interval = 0
        self._loop = asyncio.get_running_loop()
        self.handle_auto_update_check_change()

    def handle_auto_update_cancel(self):
        """Auto update timer cancel."""
        if self._update_timer_handle:
            self._update_timer_handle.cancel()
            self._update_timer_handle = None

    def handle_auto_update_setup_next_call(self, force_new_interval=False):
        """Auto update schedule next update."""
        tuya_cluster = self.endpoint.device.endpoints[1].in_clusters.get(
            TuyaMCUCluster.cluster_id, None
        )
        if tuya_cluster and "auto_refresh_interval" in tuya_cluster.attributes_by_name:
            interval = tuya_cluster.get("auto_refresh_interval", 0) * 60
            # Check for a change to auto refresh number
            if interval != self.next_refresh_interval:
                self.handle_auto_update_cancel()
                self.next_refresh_interval = interval
                force_new_interval = True

        if force_new_interval and self.next_refresh_interval > 0:
            self.debug(
                "using refresh interval of %d minutes", self.next_refresh_interval
            )
            self._update_timer_handle = self._loop.call_later(
                self.next_refresh_interval, self.handle_auto_update_timer_wrapper
            )

    def handle_auto_update_check_change(self):
        """Auto update schedule next interval check."""
        self.handle_auto_update_setup_next_call()
        self._loop.call_later(self.check_interval, self.handle_auto_update_check_change)

    def handle_auto_update_timer_wrapper(self):
        """Auto update handle refresh and schedule next update."""
        self.create_catching_task(self.handle_auto_update())
        self.handle_auto_update_setup_next_call(force_new_interval=True)

    async def handle_auto_update(self):
        """Auto update invoke data refresh command."""
        tuya_cluster = self.endpoint.device.endpoints[1].in_clusters[
            TuyaMCUCluster.cluster_id
        ]
        self.debug("sending refresh query command")
        await tuya_cluster.command(TUYA_QUERY_DATA)


(
    TuyaQuirkBuilder("_TZE200_v1jqz5cy", "TS0601")
    .device_class(EnchantedDeviceV2)
    .replaces(TuyaPoolManufCluster)
    .tuya_battery(dp_id=7, power_cfg=TuyaPowerConfigurationCluster, scale=1)
    .tuya_temperature(dp_id=2, scale=10)
    .tuya_sensor(
        dp_id=10,
        attribute_name="ph_measured_value",
        divisor=100,
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PH,
        translation_key="ph_measured_value",
        fallback_name="pH",
    )
    .tuya_sensor(
        dp_id=1,
        attribute_name="total_dissolved_solids",
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="total_dissolved_solids",
        fallback_name="Total Dissolved Solids",
    )
    .tuya_sensor(
        dp_id=11,
        attribute_name="ec_measured_value",
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="ec_measured_value",
        fallback_name="Electrical Conductivity",
    )
    .tuya_sensor(
        dp_id=117,
        attribute_name="salt_measured_value",
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="salt_measured_value",
        fallback_name="Salt Concentration",
    )
    .tuya_sensor(
        dp_id=101,
        attribute_name="redox_potential",
        type=t.uint16_t,
        unit=UnitOfElectricPotential.MILLIVOLT,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="redox_potential",
        fallback_name="ORP Level",
    )
    .tuya_sensor(
        dp_id=102,
        attribute_name="cl_measured_value",
        type=t.uint16_t,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="cl_measured_value",
        fallback_name="Chlorine Concentration",
    )
    # TODO: 103 enum ?  pH Calibration
    # TODO: 104 bool ?
    # TODO: 105 uint16
    .tuya_number(
        dp_id=106,
        attribute_name="ph_max_value",
        type=t.uint16_t,
        multiplier=0.1,
        step=0.1,
        min_value=0,
        max_value=14,
        mode="box",
        device_class=NumberDeviceClass.PH,
        translation_key="ph_max_value",
        fallback_name="pH Maximum Value",
    )
    .tuya_number(
        dp_id=107,
        attribute_name="ph_min_value",
        type=t.uint16_t,
        multiplier=0.1,
        step=0.1,
        min_value=0,
        max_value=14,
        mode="box",
        device_class=NumberDeviceClass.PH,
        translation_key="ph_min_value",
        fallback_name="pH Minimum Value",
    )
    .tuya_number(
        dp_id=108,
        attribute_name="ec_max_value",
        type=t.uint16_t,
        multiplier=11,
        step=1,
        min_value=0,
        max_value=20000,
        mode="box",
        translation_key="ec_max_value",
        fallback_name="EC Maximum Value",
    )
    .tuya_number(
        dp_id=109,
        attribute_name="ec_min_value",
        type=t.uint16_t,
        multiplier=1,
        step=1,
        min_value=0,
        max_value=20000,
        mode="box",
        translation_key="ec_min_value",
        fallback_name="EC Minimum Value",
    )
    .tuya_number(
        dp_id=110,
        attribute_name="orp_max_value",
        type=t.uint16_t,
        multiplier=1,
        step=1,
        min_value=-999,
        max_value=999,
        mode="box",
        unit=UnitOfElectricPotential.MILLIVOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        translation_key="orp_max_value",
        fallback_name="ORP Maximum Value",
    )
    .tuya_number(
        dp_id=111,
        attribute_name="orp_min_value",
        type=t.uint16_t,
        multiplier=1,
        step=1,
        min_value=-999,
        max_value=999,
        mode="box",
        unit=UnitOfElectricPotential.MILLIVOLT,
        device_class=NumberDeviceClass.VOLTAGE,
        translation_key="orp_min_value",
        fallback_name="ORP Minimum Value",
    )
    .tuya_number(
        dp_id=112,
        attribute_name="cl_max_value",
        type=t.uint16_t,
        multiplier=0.1,
        step=0.1,
        min_value=0,
        max_value=4,
        mode="box",
        translation_key="cl_max_value",
        fallback_name="Cl Maximum Value",
    )
    .tuya_number(
        dp_id=113,
        attribute_name="cl_min_value",
        type=t.uint16_t,
        multiplier=0.1,
        step=0.1,
        min_value=0,
        max_value=4,
        mode="box",
        translation_key="cl_min_value",
        fallback_name="Cl Minimum Value",
    )
    # TODO: 114 uint16_t payload=0  pH Calibration
    # TODO: 115 uint16_t payload=0  EC Calibration
    # TODO: 116 uint16_t payload=0  ORP Calibration
    # TODO: 118 bool payload=0 (false)
    # Press button to manually refresh sensor data.
    .command_button(
        command_name="query_data",
        cluster_id=TuyaNewManufCluster.cluster_id,
        translation_key="Update",
        fallback_name="Update",
    )
    # Automatic refresh interval in minutes. Set to 0 to disable.
    .tuya_number(
        dp_id=0x09,
        attribute_name="auto_refresh_interval",
        type=t.uint16_t,
        translation_key="auto_refresh_interval",
        fallback_name="Refresh Interval",
        unit=UnitOfTime.MINUTES,
        step=5,
        min_value=0,
        max_value=1440,
    )
    .add_to_registry()
)
