from ..engine import PatchEngine


def patch_unlimited_stamina(engine: PatchEngine):
    """Disables stamina depletion for unlimited sprinting."""
    return engine.apply_gameplay_patch(
        "unlimited_stamina", "StaminaData", {"staminaMax": 1000, "staminaSprintDrain": 0}
    )


def patch_enable_container_damage(engine: PatchEngine):
    """Enables damage to containers (tents, barrels, etc)."""
    return engine.apply_gameplay_patch("enable_container_damage", "GeneralData", {"disableContainerDamage": False})


def patch_no_fog(engine: PatchEngine):
    """Removes fog completely from the server."""
    return engine.apply_xml_patch(
        "no_fog",
        "cfgweather.xml",
        [
            {"xpath": ".//fog/limits", "values": {"min": "0.0", "max": "0.0"}},
            {"xpath": ".//fog/current", "values": {"actual": "0.0"}},
        ],
    )


def patch_disable_dynamic_gas(engine: PatchEngine):
    """Disables dynamic gas/contamination zones."""
    return engine.apply_xml_patch(
        "disable_dynamic_gas",
        "db/events.xml",
        [
            {
                "xpath": ".//event[@name='StaticContaminatedArea']",
                "values": {"active": "0", "nominal": "0", "min": "0", "max": "0"},
            }
        ],
    )


def patch_boost_heli_crashes(engine: PatchEngine, nominal=15):
    """Boosts helicopter crash spawns."""
    return engine.apply_xml_patch(
        "boost_heli_crashes",
        "db/events.xml",
        [
            {
                "xpath": ".//event[@name='StaticHeliCrash']",
                "values": {"nominal": str(nominal), "min": str(max(1, nominal - 5)), "max": str(nominal + 5)},
            }
        ],
    )


def patch_lock_containers_event(engine: PatchEngine):
    """Injects the StaticContainerLocked event definition."""
    xml_content = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<events>
    <event name="StaticContainerLocked">
        <nominal>50</nominal>
        <min>25</min>
        <max>0</max>
        <lifetime>3888000</lifetime>
        <restock>0</restock>
        <saferadius>0</saferadius>
        <distanceradius>0</distanceradius>
        <cleanupradius>0</cleanupradius>
        <flags deletable="0" init_random="0" remove_damaged="0"/>
        <position>fixed</position>
        <limit>custom</limit>
        <active>1</active>
        <children>
            <child lootmax="0" lootmin="0" max="50" min="25" type="Land_Container_1Aoh"/>
        </children>
    </event>
</events>
"""
    return engine.apply_xml_patch("add_locked_containers_event", "db/events.xml", [], data_xml=xml_content)


def patch_custom_layout_ezstreet(engine: PatchEngine):
    """Registers ScaleSpeeder/Tony 1.28 custom object layouts for EZStreet."""
    layouts = [
        "EZStreet_NovoCustom_Hippie.json",
        "EZStreet_BuildTrailer_Zeleno.json",
        "EZStreet_BuildTrailer_Ropka.json",
        "EZStreet_TopoCustom_Dylan.json",
        "EZStreet_Trader.json",
        "EZStreet_FightCage_Nwaf.json",
        "EZStreet_AdminBase.json",
        "EZStreet_BuildTrailer_Zap.json",
        "EZStreet_bm_Trader.json",
        "EZStreet_Loadout_Fresh.json",
        "rescue.json",
    ]
    results = []
    for layout in layouts:
        res = engine.apply_raw_copy(f"layout_{layout}", f"backend/patcher/patches/{layout}", f"custom/{layout}")
        results.append(res)
    return any(results)


def patch_loot_pool_removals(engine: PatchEngine):
    """Removes unwanted items from loot pool (nominal=0)."""
    items_to_remove = []
    # Wildcards for Chemlights and Flags needs explicit expansion or multiple queries
    # Since we can't easily do wildcard expansion without reading file first, let's use list of likely names
    # OR use XPath contains()
    tasks = []

    # Exact matches
    for item in items_to_remove:
        tasks.append({"xpath": f".//type[@name='{item}']", "values": {"nominal": "0", "min": "0"}})

    # Wildcards via XPath
    # Wildcards removed due to ElementTree limitations
    # tasks.append({
    #     "xpath": ".//type[starts-with(@name, 'Chemlight_')]",
    #     "values": {"nominal": "0", "min": "0"}
    # })
    # tasks.append({
    #     "xpath": ".//type[starts-with(@name, 'Flag_')]",
    #     "values": {"nominal": "0", "min": "0"}
    # })

    return engine.apply_xml_patch("loot_pool_removals", "db/types.xml", tasks)


def patch_lower_misc_clothes_spawn(engine: PatchEngine):
    """Lowers spawn rates for Misc (tools) and Clothes."""
    return engine.apply_xml_patch(
        "lower_misc_clothes_spawn",
        "db/types.xml",
        [
            {
                "xpath": ".//type[category/@name='tools']",
                "values": {"nominal_multiplier": "0.3", "min_multiplier": "0.2"},
            },
            {
                "xpath": ".//type[category/@name='clothes']",
                "values": {"nominal_multiplier": "0.3", "min_multiplier": "0.2"},
            },
        ],
    )
