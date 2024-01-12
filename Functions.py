from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import math

def BatteryCharge(power, cRating, Capacity, SoC):
    if power >= cRating:
        potential = cRating
        if potential + SoC <= Capacity:
            SoC += potential
            remainedPower = power - cRating
            inserted = potential
        else:
            remainedPower = power - (Capacity - SoC)
            inserted = Capacity - SoC
            SoC = Capacity
    else:
        potential = power
        if potential + SoC <= Capacity:
            SoC += potential
            remainedPower = 0
            inserted = potential
        else:
            remainedPower = power - (Capacity - SoC)
            inserted = Capacity - SoC
            SoC = Capacity
    return [SoC, remainedPower, inserted]

def BatteryDegradation(BatteryTransaction):
    DegCap = 1.25 * 0.00001 * BatteryTransaction

    return DegCap

def BatteryDisCharge(power, cRating, SoC):
    if power >= cRating:
        potential = cRating
        if SoC - potential >= 0:
            SoC -= potential
            remainedPower = power - potential
            extracted = potential
        else:
            remainedPower = power - SoC
            extracted = SoC
            SoC = 0
    else:
        potential = power
        if SoC - potential >= 0:
            SoC -= potential
            remainedPower = 0
            extracted = potential
        else:
            remainedPower = power - SoC
            extracted = SoC
            SoC = 0

    return [SoC, remainedPower, extracted]


def DateFind(year, dayNumber):
    start_date = datetime(year, 1, 1)

    # Calculate the target date by adding the appropriate number of days
    target_date = start_date + timedelta(days=dayNumber - 1)

    return target_date.strftime('%Y-%m-%d')



def xlsxFile(varStatus, varsending, varreceiving, varSellGrid, varBuyGrid, varInsertBattery, varExtractBattery, varDeg, varSoC, varChangeBattery, varEarning ,dayNumber, NumberofSchools, year, AgentsetSending):
    date = DateFind(year, dayNumber)
    result = []
    # Open the CSV file in read mode

    excel_file_path = 'FinalFile.xlsx'

    # Read the Excel file into a pandas DataFrame
    df = pd.read_excel(excel_file_path, header=None)
    result = df.values

    for i in range(0, 24):
        for j in range(0, NumberofSchools):
            row = []
            row.append(date)
            if i < 10:
                row.append('0'+str(i)+':00')
            else:
                row.append(str(i)+':00')

            row.append(str(AgentsetSending[j]))
            row.append(float(varStatus[str(AgentsetSending[j])][i + 1]))

            for jj in range(0, NumberofSchools):
                row.append(varsending[str(AgentsetSending[j])][i+1][str(AgentsetSending[jj])])

            for jj in range(0, NumberofSchools):
                row.append(varreceiving[str(AgentsetSending[j])][i+1][str(AgentsetSending[jj])])

            row.append(float(varSellGrid[str(AgentsetSending[j])][i + 1]))
            row.append(float(varBuyGrid[str(AgentsetSending[j])][i + 1]))
            row.append(float(varInsertBattery[str(AgentsetSending[j])][i + 1]))
            row.append(float(varExtractBattery[str(AgentsetSending[j])][i + 1]))
            row.append(float(varDeg[str(AgentsetSending[j])][i + 1]))
            row.append(float(varSoC[str(AgentsetSending[j])][i + 1]))
            row.append(float(varChangeBattery[str(AgentsetSending[j])][i + 1]))
            row.append(float(varEarning[str(AgentsetSending[j])][i + 1]))

            result = np.vstack([result, row])

    df = pd.DataFrame(result)
    file_path = "FinalFile.xlsx"
    df.to_excel(file_path, index=False, header=False)

def StatusfunctionSeason(time, AgentName, season):

    with open("data/generation/" + str(AgentName) + "/pvProfile" + str(season) + ".json", "r") as json_file:
        datagen = json.load(json_file)
    with open("data/consumption/" + str(AgentName) + "/conProfile" + str(season) + ".json", "r") as json_file:
        datacon = json.load(json_file)

    gen = datagen[time - 1]
    con = datacon[time - 1]

    return gen - con


def StatusfunctionDay(time, AgentName, dayNumber):

    with open("data/generation/" + str(AgentName) + "/pvProfile.json", "r") as json_file:
        datagen = json.load(json_file)
    with open("data/consumption/" + str(AgentName) + "/conProfile.json", "r") as json_file:
        datacon = json.load(json_file)

    newtime = ((dayNumber - 1) * 24) + time
    gen = datagen[newtime - 1]
    con = datacon[newtime - 1]

    return gen - con

def Lostfunction(Agent1, Agent2, lostPermeter):

    with open("data/location/" + str(Agent1) + "/location.json", "r") as json_file:
        Loc1 = json.load(json_file)
    Long1 = Loc1['AgentLocation']['Longitude']
    Lat1 = Loc1['AgentLocation']['Latitude']
    with open("data/location/" + str(Agent2) + "/location.json", "r") as json_file:
        Loc2 = json.load(json_file)
    Long2 = Loc2['AgentLocation']['Longitude']
    Lat2 = Loc2['AgentLocation']['Latitude']

    R = 6371  # Earth radius in kilometers

    lat1, lon1, lat2, lon2 = map(math.radians, [Lat1, Long1, Lat2, Long2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    Distance = R * c

    return Distance * lostPermeter
