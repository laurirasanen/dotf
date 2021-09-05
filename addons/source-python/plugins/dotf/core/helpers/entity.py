def dump_entity_attributes(entity):
    print(f"class '{entity.classname}' attributes:")
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
            print(f"  m_AttributeList.m_Attributes.00{x}:")
            print(f"    m_iAttributeDefinitionIndex: {def_idx}")
            print(f"    m_iRawValue32: {raw_val}")
            print(f"    m_nRefundableCurrency: {ref_cur}")
        except ValueError:
            break


def dump_entity_properties(entity):
    print(f"class '{entity.classname}' properties:")
    for key in entity.properties.keys():
        print(f"  {key}: {entity.properties[key]}")
