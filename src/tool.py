# -*- coding: utf-8 -*-


def gression_300(value: int):
    value &= 0xFF
    value |= (1 << 8) | (1 << 9)
    return value


def check_gression_700(value: int):
    return value & 0x700 == 0x700


if __name__ == '__main__':
    print(hex(gression_300(0x55)))
    print(check_gression_700(0x701))
