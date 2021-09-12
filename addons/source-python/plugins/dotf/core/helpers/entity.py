"""
================================================================
    * core/helpers/entity.py
    *
    * Copyright (c) 2021 Lauri Räsänen
    * ================================

    ...
================================================================
"""

# =============================================================================
# >> IMPORTS
# =============================================================================
# dotf
from ..log import Logger


def dump_entity_attributes(entity):
    Logger.instance().log_debug(f"class '{entity.classname}' attributes:")
    for x in range(100):
        try:
            def_idx = entity.get_property_ushort(
                f"m_AttributeList.m_Attributes.00{x}.m_iAttributeDefinitionIndex"
            )
            raw_val = entity.get_property_int(
                f"m_AttributeList.m_Attributes.00{x}.m_iRawValue32"
            )
            ref_cur = entity.get_property_int(
                f"m_AttributeList.m_Attributes.00{x}.m_nRefundableCurrency"
            )
            Logger.instance().log_debug(f"  m_AttributeList.m_Attributes.00{x}:")
            Logger.instance().log_debug(f"    m_iAttributeDefinitionIndex: {def_idx}")
            Logger.instance().log_debug(f"    m_iRawValue32: {raw_val}")
            Logger.instance().log_debug(f"    m_nRefundableCurrency: {ref_cur}")
        except ValueError:
            break


def dump_entity_properties(entity):
    Logger.instance().log_debug(f"class '{entity.classname}' properties:")
    for key in entity.properties.keys():
        Logger.instance().log_debug(f"  {key}: {entity.properties[key]}")
