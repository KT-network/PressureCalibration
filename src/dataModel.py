# -*- coding: utf-8 -*-
from pydantic import BaseModel
from typing import List


class SensorCalParam(BaseModel):
    adValue: int = 0
    rangeValue: int = 0


class SensorCalParamList(BaseModel):
    sensorCalParam: List[SensorCalParam] = []

    def sort(self):
        self.sensorCalParam.sort(key=lambda x: x.adValue)


if __name__ == '__main__':
    params = SensorCalParamList()
    params.sensorCalParam.append(SensorCalParam(adValue=300, rangeValue=10))
    params.sensorCalParam.append(SensorCalParam(adValue=200, rangeValue=10))
    params.sensorCalParam.append(SensorCalParam(adValue=100, rangeValue=10))
    params.sensorCalParam.append(SensorCalParam(adValue=500, rangeValue=10))

    print(params)
    params.sort()
    print(params)
