# -*- coding: utf-8 -*-


def can_id_generate_gression_300(value: int):
    """将CanId的高三位设置位011"""
    value &= 0xFF
    value |= (1 << 8) | (1 << 9)
    return value


def can_id_check_gression_700(value: int):
    '''判断CanId值的高三位是否为1'''
    return value & 0x700 == 0x700


def can_id_remove_gression(value: int):
    """移除CanId高三位"""
    return value & 0x0FF


def remove_gression_high_3(low,high):
    """将两个uint8合并为uint16并且移除值的高三位"""
    value = (high << 8) | low
    return value & 0x1FFF
    # return (data[3] << 24) | (data[2] << 16) | (data[1] << 8) | data[0]

def merge_int8_to_int32(data):
    """将4个uint8合并为uint32"""
    return (data[3] << 24) | (data[2] << 16) | (data[1] << 8) | data[0]


def merge_int8_to_int16(low, high):
    return (high << 8) | low


if __name__ == '__main__':
    print(hex(can_id_generate_gression_300(0xFF)))
    print(can_id_check_gression_700(0x301))
    print(hex(can_id_remove_gression(0x355)))
