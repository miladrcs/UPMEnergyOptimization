from LinearOpt import *
import json

G = LinearOptimization()

AgentNames = ['ETSAM', 'ETSE', 'ETSIAE', 'ETSICCP', 'ETSIN', 'ETSIT', 'INEF', 'RECTORATE']

ETSAMMat = []
ETSEMat = []
ETSIAEMat = []
ETSICCPMat = []
ETSINMat = []
ETSITMat = []
INEFMat = []
RECTORATEMat = []
BatteryDegMat = []
for i in range(0, len(AgentNames)):
    BatteryDegMat.append(0)

SoCMat = []
for i in range(0, len(AgentNames)):
    with open("data/storage/" + str(AgentNames[i]) + "/BProperties.json", "r") as json_file:
        databattery = json.load(json_file)

    SoCMat.append(databattery['BProperties']['SoC'])

for dayNumber in range(1, 2):

    # Run optimization algorithm. result1 has payment information, result2 includes degredation, and result3 shows SoC
    result1, result2, result3 = G.Gurobidays(AgentNames, 0, 0.8, dayNumber, BatteryDegMat, SoCMat)
    ########### calculate the daily payment of the schools#################
    for key, values in result1.items():
        totalsum = 0
        if key == 'ETSAM':
            for index, value in values.items():
                totalsum += value
            ETSAMMat.append(totalsum)

        if key == 'ETSE':
            for index, value in values.items():
                totalsum += value
            ETSEMat.append(totalsum)

        if key == 'ETSIAE':
            for index, value in values.items():
                totalsum += value
            ETSIAEMat.append(totalsum)

        if key == 'ETSICCP':
            for index, value in values.items():
                totalsum += value
            ETSICCPMat.append(totalsum)

        if key == 'ETSIN':
            for index, value in values.items():
                totalsum += value
            ETSINMat.append(totalsum)

        if key == 'ETSIT':
            for index, value in values.items():
                totalsum += value
            ETSITMat.append(totalsum)

        if key == 'INEF':
            for index, value in values.items():
                totalsum += value
            INEFMat.append(totalsum)

        if key == 'RECTORATE':
            for index, value in values.items():
                totalsum += value
            RECTORATEMat.append(totalsum)
    #######################################################################

    ########### Extract the degradation and SoC of schools' batteries #############
    BatteryDegMat = [result2[key][24] for key in AgentNames]
    SoCMat = [result3[key][24] for key in AgentNames]
    #######################################################################
print('The overall cost = ',sum(ETSAMMat) + sum(ETSEMat) + sum(ETSIAEMat) + sum(ETSICCPMat) + sum(ETSINMat) + sum(ETSITMat) + sum(INEFMat) + sum(RECTORATEMat))
print('The ETSAM cost = ',sum(ETSAMMat))
print('The ETSE cost = ',sum(ETSEMat))
print('The ETSIAE cost = ',sum(ETSIAEMat))
print('The ETSICCP cost = ',sum(ETSICCPMat))
print('The ETSIN cost = ',sum(ETSINMat))
print('The ETSIT cost = ',sum(ETSITMat))
print('The INEF cost = ',sum(INEFMat))
print('The RECTORATE cost = ',sum(RECTORATEMat))
