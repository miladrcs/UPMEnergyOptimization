from Functions import *
from pyomo.environ import *
import json

class LinearOptimization:

    def Gurobidays(self, AgentNames, lostPermeter, AgentSellingCoefficient, dayNumber, BatteryDegMat, SoCMat):
        AgentsetSending = []
        AgentsetReceiving = []
        for i in range(0, len(AgentNames)):
            AgentsetSending.append(AgentNames[i])
            AgentsetReceiving.append(AgentNames[i])


        with open("data/price/BuyfromGrid/price2022.json", "r") as json_file:
            data1 = json.load(json_file)


        with open("data/price/SellToGrid/price2022.json", "r") as json_file:
            data2 = json.load(json_file)

        BuyingFromGrid = []
        SellToGrid = []

        start = (dayNumber - 1) * 24
        end = (dayNumber * 24)

        for i in range(start, end):
            BuyingFromGrid.append(data1[i] / 1000) # Changing MWh to KWh
            SellToGrid.append(data2[i] / 1000)
        timeMatrix1 = []
        for i in range(0, len(BuyingFromGrid)):
            timeMatrix1.append(i + 1)
        timeMatrix = timeMatrix1

        capacityMatrix = []
        cRatingMatrix = []
        SoCinitialMatrix = SoCMat
        MaximumDegradationMatrix = []
        DegradationCostMatrix = []
        BatteryPriceMatrix = []

        for i in range(0, len(AgentNames)):
            with open("data/storage/" + str(AgentNames[i]) + "/BProperties.json", "r") as json_file:
                databattery = json.load(json_file)

            capacityMatrix.append(databattery['BProperties']['Capacity'])
            cRatingMatrix.append(databattery['BProperties']['C_Rating'])
            MaximumDegradationMatrix.append(databattery['BProperties']['Maximum Degradation'])
            BatteryPriceMatrix.append(databattery['BProperties']['Price'])
            DegradationCostMatrix.append(databattery['BProperties']['Price'] / (databattery['BProperties']['Capacity'] * databattery['BProperties']['Maximum Degradation'])) # The cost of degradation for each unit of the lost capacity

        # The model
        model = ConcreteModel()

        # Variables of the model

        # Variables for Internal Transfer of the microgrid
        ###########################################################################################################################
        model.InternalTransferSending = Var(AgentsetSending, AgentsetReceiving, timeMatrix,
                                            domain=NonNegativeReals) # Sending energy inside the microgrid.
        model.InternalTransferReceiving = Var(AgentsetSending, AgentsetReceiving, timeMatrix,
                                            domain=NonNegativeReals)  # Receiving energy inside the microgrid.
        model.InternalTransferBinary = Var(AgentsetSending, AgentsetReceiving, timeMatrix, domain=Binary) # Binary variable to control power flow between agents
        model.InternalTransferCost = Var(AgentsetReceiving, timeMatrix, domain=Reals) # measuring the balance between sending and receiving of each agent
        ###########################################################################################################################

        # Variables for External Transfer of the microgrid
        ###########################################################################################################################
        model.ExternalTransferSelling = Var(AgentsetSending, timeMatrix, domain=NonNegativeReals) # Sell energy to the grid.
        model.ExternalTransferBuying = Var(AgentsetSending, timeMatrix, domain=NonNegativeReals)  # Buy energy from the grid.
        model.ExternalTransferBinary = Var(AgentsetSending, timeMatrix, domain=Binary) # Binary variable to control power flow between grid and agents
        model.ExternalTransferCost = Var(AgentsetReceiving, timeMatrix, domain=Reals)  # measuring the balance between each agent and the grid
        ###########################################################################################################################

        # Variables for Storage units
        ###########################################################################################################################
        model.SoC = Var(AgentsetSending, timeMatrix, domain=NonNegativeReals) # SoC of the batteries
        model.InsertToBattery = Var(AgentsetSending, timeMatrix, domain=NonNegativeReals) # insert energy into the batteries
        model.ExtractFromBattery = Var(AgentsetSending, timeMatrix, domain=NonNegativeReals)  # extract energy from the batteries
        model.PowerBatteryBinary = Var(AgentsetSending, timeMatrix, domain=Binary) # Binary variable to control power flow in the battery
        model.Degradation = Var(AgentsetSending, timeMatrix, domain=NonNegativeReals) # measuring degradation of the battery at each time step
        model.MaximumPower = Var(AgentsetSending, timeMatrix, domain=NonNegativeReals) # The maximum power is needed for degradation bucket model
        model.BatteryChange = Var(AgentsetSending, timeMatrix, domain=Binary) # If a battery is degraded, then it must be substituted with a new one
        model.BatteryBinary = Var(AgentsetSending, timeMatrix, domain=Binary) # helps to find the time of changing battery for an agent
        model.BatteryNotChange = Var(AgentsetSending, timeMatrix, domain=Reals) # helps to find the time of changing battery for an agent
        model.DegradationCost = Var(AgentsetSending, timeMatrix, domain=NonNegativeReals)  # measuring degradation of the battery at each time step
        model.OveralDegradation = Var(AgentsetSending, timeMatrix, domain=NonNegativeReals) # measuring overal degradation of the battery at each time step
        ###########################################################################################################################

        # Additional Variables
        ###########################################################################################################################
        model.StatusMatrix = Var(AgentsetSending, timeMatrix, domain=Reals) # Energy Status of each agent. Negative (needs energy) / Positive (has extra energy)
        model.Earning = Var(AgentsetSending, timeMatrix, domain=Reals) # negative (earning) / positive (paying)
        model.LostEnergyMatrix = Var(AgentsetSending, AgentsetReceiving, domain=NonNegativeReals) # The lost energy in the process of transferring between agents
        model.EnergyTransaction = Var(AgentsetSending, timeMatrix, domain=Reals) # Measuring the energy transaction of the agents
        model.EnergyBalance = Var(AgentsetSending, timeMatrix, domain=Reals) # it measures the balance between existance energy and transaction of energy
        ###########################################################################################################################

        # Objective Function
        def Obj(model):

            OveralEarning = sum(model.Earning[A,T] for A in AgentsetSending for T in timeMatrix)

            return OveralEarning

        model.obj = Objective(rule=Obj, sense=maximize)

        # Constraints
        ###########################################################################################################################
        # 1 defining status matrix
        def Limit1(model, AS, T):
            return model.StatusMatrix[AS, T] == StatusfunctionDay(T, AS, dayNumber)

        model.limit1 = Constraint(AgentsetSending, timeMatrix, rule=Limit1)

        # 2 measuring the lost of energy in between the agents
        def Limit2(model, AS, AR):
            return model.LostEnergyMatrix[AS, AR] == Lostfunction(AS, AR, lostPermeter)

        model.limit2 = Constraint(AgentsetSending, AgentsetReceiving, rule=Limit2)

        # Internal Transfer Constraints
        ###########################################################################################################################
        # 3 Sending energy between A1 and A1 is 0
        def Limit3(model, AS, AR, T):
            if AS == AR:
                return model.InternalTransferSending[AS, AR, T] == 0
            else:
                return Constraint.Skip

        model.limit3 = Constraint(AgentsetSending, AgentsetReceiving, timeMatrix, rule=Limit3)

        # 4 , 5 If A1 is sending energy to A2, then InternalTransferSending[A2, A1, T] must be equal to 0
        # 4
        def Limit4(model, AS, AR, T):
            return model.InternalTransferSending[AS, AR, T] == model.InternalTransferBinary[AS, AR, T] * model.InternalTransferSending[AS, AR, T]

        model.limit4 = Constraint(AgentsetSending, AgentsetReceiving, timeMatrix, rule=Limit4)

        # 5
        def Limit5(model, AS, AR, T):
            return model.InternalTransferSending[AR, AS, T] == (1 - model.InternalTransferBinary[AS, AR, T]) * model.InternalTransferSending[AR, AS, T]

        model.limit5 = Constraint(AgentsetSending, AgentsetReceiving, timeMatrix, rule=Limit5)

        # 6 Receiving energy between A1 and A1 is 0
        def Limit6(model, AS, AR, T):
            if AS == AR:
                return model.InternalTransferReceiving[AS, AR, T] == 0
            else:
                return Constraint.Skip

        model.limit6 = Constraint(AgentsetSending, AgentsetReceiving, timeMatrix, rule=Limit6)

        # 7 , 8 Internal Transfer (Received Energy). If A1 sends energy to A2 so, receiving matrix (A2,A1) must get a value regarding the loosing energy.
        # 7
        def Limit7(model, AS, AR, T):
            return model.InternalTransferReceiving[AS, AR, T] == (1 - model.InternalTransferBinary[AS, AR, T]) * ((model.InternalTransferSending[AR, AS, T]) - model.LostEnergyMatrix[AS, AR])

        model.limit7 = Constraint(AgentsetSending, AgentsetReceiving, timeMatrix, rule=Limit7)

        # 8
        def Limit8(model, AS, AR, T):
            return model.InternalTransferReceiving[AR, AS, T] == (model.InternalTransferBinary[AS, AR, T]) * ((model.InternalTransferSending[AS, AR, T]) - model.LostEnergyMatrix[AS, AR])

        model.limit8 = Constraint(AgentsetSending, AgentsetReceiving, timeMatrix, rule=Limit8)

        # 9 The variable InternalBinarytrasnfer between A1 and A1 must be 0
        def Limit9(model, AS, AR, T):
            if AS == AR:
                return model.InternalTransferBinary[AS, AR, T] == 0
            else:
                return Constraint.Skip

        model.limit9 = Constraint(AgentsetSending, AgentsetReceiving, timeMatrix, rule=Limit9)

        # 10 makes sure the transferred energy for each agent at each time is less than generated plus extracted energy from the battery
        def Limit10(model, AS, T):
            if StatusfunctionDay(T, AS, dayNumber) >= 0:
                return sum(model.InternalTransferSending[AS, AR, T] for AR in AgentsetSending) + model.ExternalTransferSelling[AS, T] <= model.StatusMatrix[AS, T] + model.ExtractFromBattery[AS, T]
            else:
                return sum(model.InternalTransferSending[AS, AR, T] for AR in AgentsetSending) == 0 #Constraint.Skip

        model.limit10 = Constraint(AgentsetSending, timeMatrix, rule=Limit10)

        ###########################################################################################################################

        # External Transfer Constraints
        ###########################################################################################################################

        # 11 if an agent buys energy while it has enough generation, the energy must be saved in its battery
        def Limit11(model, AS, T):
            if StatusfunctionDay(T, AS, dayNumber) >= 0:
                return sum(model.InternalTransferReceiving[AS, AR, T] for AR in AgentsetSending) == model.InsertToBattery[AS, T]
            else:
                return model.ExternalTransferBinary[AS, T] == 1#Constraint.Skip

        model.limit11 = Constraint(AgentsetSending, timeMatrix, rule=Limit11)

        # 12 , 13. It is impossible to sell and buy energy to/from the grid at a same time
        # 12
        def Limit12(model, AS, T):
            return model.ExternalTransferSelling[AS, T] == (1 - model.ExternalTransferBinary[AS, T]) * model.ExternalTransferSelling[AS, T]

        model.limit12 = Constraint(AgentsetSending, timeMatrix, rule=Limit12)

        # 13
        def Limit13(model, AS, T):
            return model.ExternalTransferBuying[AS, T] <= model.ExternalTransferBinary[AS, T] * model.ExternalTransferBuying[AS, T]

        model.limit13 = Constraint(AgentsetSending, timeMatrix, rule=Limit13)

        ###########################################################################################################################

        # Storage Constraints
        ###########################################################################################################################
        # 14, 15 make sure we either insert or extract energy into / from the battery at each time step
        # 14
        def Limit14(model, AS, T):
            return model.InsertToBattery[AS, T] == model.PowerBatteryBinary[AS, T] * model.InsertToBattery[AS, T]

        model.limit14 = Constraint(AgentsetSending, timeMatrix, rule=Limit14)

        # 15
        def Limit15(model, AS, T):
            return model.ExtractFromBattery[AS, T] == (1 - model.PowerBatteryBinary[AS, T]) * model.ExtractFromBattery[AS, T]

        model.limit15 = Constraint(AgentsetSending, timeMatrix, rule=Limit15)

        # 16, 17 The Power flow into/from the battery must be always less than C-Rating of the battery
        # 16
        def Limit16(model, AS, T):
            return model.ExtractFromBattery[AS, T] <= cRatingMatrix[AgentsetSending.index(AS)]

        model.limit16 = Constraint(AgentsetSending, timeMatrix, rule=Limit16)

        # 17
        def Limit17(model, AS, T):
            return model.InsertToBattery[AS, T] <= cRatingMatrix[AgentsetSending.index(AS)]

        model.limit17 = Constraint(AgentsetSending, timeMatrix, rule=Limit17)

        # 16 - 22 measures the degradation of the battery based on power flow
        # 16, 17, 18 find the maximum power
        """def Limit16(model, AS, T):
            return model.MaximumPower[AS, T] >= (1 - model.BatteryChange[AS, T]) * model.InsertToBattery[AS, T]

        model.limit16 = Constraint(AgentsetSending, timeMatrix, rule=Limit16)

        # 17 If model.BatteryChange[AS, T] is equal to 1, it meas the battery must be changed and the maximum power must be 0
        def Limit17(model, AS, T):
            return model.MaximumPower[AS, T] >= (1 - model.BatteryChange[AS, T]) * model.ExtractFromBattery[AS, T]

        model.limit17 = Constraint(AgentsetSending, timeMatrix, rule=Limit17)

        # 18
        def Limit18(model, AS, T):
            if T > 1:
                return model.MaximumPower[AS, T] >= (1 - model.BatteryChange[AS, T]) * model.MaximumPower[AS, T - 1]
            else:
                return Constraint.Skip

        model.limit18 = Constraint(AgentsetSending, timeMatrix, rule=Limit18)"""

        # 19 capacity degradation based on bucket model. if the degradation reaches MaximumDegradation of the battery, the battery must be changed with a new one and the degradation must be set to 0
        """def Limit19(model, AS, T):
            if T > 1:
                if T == len(timeMatrix):
                    return model.Degradation[AS, T] == (model.Degradation[AS, T - 1] + ((2.5 * 0.0001 * model.MaximumPower[AS, T]) + (1.25 * 0.00001 * ((model.InsertToBattery[AS, T]) + (model.ExtractFromBattery[AS, T]))))) - ((model.BatteryChange[AS, T - 1]) * ((MaximumDegradationMatrix[AgentsetSending.index(AS)] * capacityMatrix[AgentsetSending.index(AS)])))
                else:
                    return model.Degradation[AS, T] == (model.Degradation[AS, T - 1] + ((1.25 * 0.00001 * ((model.InsertToBattery[AS, T]) + (model.ExtractFromBattery[AS, T]))))) - ((model.BatteryChange[AS, T - 1]) * ((MaximumDegradationMatrix[AgentsetSending.index(AS)] * capacityMatrix[AgentsetSending.index(AS)])))
            else:
                return model.Degradation[AS, T] == BatteryDegMat[AgentsetSending.index(AS)]

        model.limit19 = Constraint(AgentsetSending, timeMatrix, rule=Limit19)"""

        # 18 measures the degradation of each battery
        def Limit18(model, AS, T):
            if T > 1:
                return model.Degradation[AS, T] == ((1.25 * 0.00001 * ((model.InsertToBattery[AS, T]) + (model.ExtractFromBattery[AS, T])))) - ((model.BatteryChange[AS, T - 1]) * ((MaximumDegradationMatrix[AgentsetSending.index(AS)] * capacityMatrix[AgentsetSending.index(AS)])))
            else:
                return model.Degradation[AS, T] == BatteryDegMat[AgentsetSending.index(AS)]

        model.limit18 = Constraint(AgentsetSending, timeMatrix, rule=Limit18)

        # 19 measures the overall degradation. This variable is used to find the number of batteries that must be changed
        def Limit19(model, AS, T):
            if T > 1:
                return model.OveralDegradation[AS, T] == (model.OveralDegradation[AS, T - 1] + model.Degradation[AS, T]) * (1 - model.BatteryChange[AS, T - 1])
            else:
                return model.OveralDegradation[AS, T] == model.Degradation[AS, T]

        model.limit19 = Constraint(AgentsetSending, timeMatrix, rule=Limit19)

        # 20 - 23 find whether the battery must be changed or not. The change of the batteries is based on the overal degradation level
        # 20
        def Limit20(model, AS, T):
            return ((model.OveralDegradation[AS, T] / (MaximumDegradationMatrix[AgentsetSending.index(AS)] * capacityMatrix[AgentsetSending.index(AS)])) - 1) <= model.BatteryChange[AS, T]

        model.limit20 = Constraint(AgentsetSending, timeMatrix, rule=Limit20)

        # 21
        def Limit21(model, AS, T):
            return ((model.OveralDegradation[AS, T] / (MaximumDegradationMatrix[AgentsetSending.index(AS)] * capacityMatrix[AgentsetSending.index(AS)])) - 1) >= model.BatteryNotChange[AS, T]

        model.limit21 = Constraint(AgentsetSending, timeMatrix, rule=Limit21)

        # 22
        def Limit22(model, AS, T):
            return (model.BatteryChange[AS, T] - model.BatteryNotChange[AS, T]) == 1

        model.limit22 = Constraint(AgentsetSending, timeMatrix, rule=Limit22)

        # 23
        def Limit23(model, AS, T):
            return model.BatteryNotChange[AS, T] <= (-1) * model.BatteryBinary[AS, T]

        model.limit23 = Constraint(AgentsetSending, timeMatrix, rule=Limit23)

        # 24 - 26 update SoC and make sure the SoC is in the interval of [0.05, 0.95].
        # 24 measures SoC
        def Limit24(model, AS, T):
            if T == 1:
                return model.SoC[AS, T] == (SoCinitialMatrix[AgentsetSending.index(AS)] + ((model.InsertToBattery[AS, T] - model.ExtractFromBattery[AS, T] - (model.Degradation[AS, T])) / capacityMatrix[AgentsetSending.index(AS)])) * (1 - model.BatteryChange[AS, T])
            else:
                return model.SoC[AS, T] == (model.SoC[AS, T - 1] + ((model.InsertToBattery[AS, T] - model.ExtractFromBattery[AS, T] - (model.Degradation[AS, T])) / capacityMatrix[AgentsetSending.index(AS)])) * (1 - model.BatteryChange[AS, T])

        model.limit24 = Constraint(AgentsetSending, timeMatrix, rule=Limit24)

        # 25 SoC interval
        def Limit25(model, AS, T):
            return model.SoC[AS, T] <= 0.95

        model.limit25 = Constraint(AgentsetSending, timeMatrix, rule=Limit25)

        # 26 SoC interval
        def Limit26(model, AS, T):
            return model.SoC[AS, T] >= 0.05

        model.limit26 = Constraint(AgentsetSending, timeMatrix, rule=Limit26)

        ###########################################################################################################################

        # Measuring energy transactions of the agents
        ###########################################################################################################################
        # 27 The energy transaction of each agent at each time step is measured by this constraint
        def Limit27(model, AS, T):
            return model.EnergyTransaction[AS, T] == (sum(model.InternalTransferReceiving[AS, i, T] for i in AgentsetSending)) \
                   - (sum(model.InternalTransferSending[AS, i, T] for i in AgentsetSending)) \
                   + model.ExternalTransferBuying[AS, T] - model.ExternalTransferSelling[AS, T] \
                   + model.ExtractFromBattery[AS, T] - model.InsertToBattery[AS, T]

        model.limit27 = Constraint(AgentsetSending, timeMatrix, rule=Limit27)

        ###########################################################################################################################

        # If Status(T) - Energy Transaction(T) for an Agent is less than 0 it means a load shedding happened.
        # On the other hand, if the balance is greater than or equal to 0, then load shedding did not happen. (An Agent can buy energy even it has additional energy)
        ###########################################################################################################################
        # 28 Measures the energy balance of the agents at each time period.
        def Limit28(model, AS, T):
            return model.EnergyBalance[AS, T] == model.StatusMatrix[AS, T] + model.EnergyTransaction[AS, T]

        model.limit28 = Constraint(AgentsetSending, timeMatrix, rule=Limit28)

        # 29 make sure all the schools have enough energy
        def Limit29(model, AS, T):
            return model.EnergyBalance[AS, T] >= 0

        model.limit29 = Constraint(AgentsetSending, timeMatrix, rule=Limit29)

        ###########################################################################################################################

        # Measuring the cost of energy flow in the microgrid
        ###########################################################################################################################
        # 30 measures the price of degradation
        def Limit30(model, AS, T):
            return model.DegradationCost[AS, T] == (model.Degradation[AS, T] * DegradationCostMatrix[AgentsetSending.index(AS)])

        model.limit30 = Constraint(AgentsetSending, timeMatrix, rule=Limit30)

        # 31 Measure the cost of internal transferring of energy
        def Limit31(model, AS, T): #(The cost of transferring energy is equal to a% of grid price)
            return model.InternalTransferCost[AS, T] == (sum(model.InternalTransferSending[AS, i, T] for i in AgentsetSending) - sum(model.InternalTransferReceiving[AS, i, T] for i in AgentsetSending)) * BuyingFromGrid[T - 1] * AgentSellingCoefficient

        model.limit31 = Constraint(AgentsetSending, timeMatrix, rule=Limit31)

        # 32 Measure the cost of external transferring of energy
        def Limit32(model, AS, T):
            return model.ExternalTransferCost[AS, T] == (model.ExternalTransferSelling[AS, T] * SellToGrid[T - 1]) - (model.ExternalTransferBuying[AS, T] * BuyingFromGrid[T - 1])

        model.limit32 = Constraint(AgentsetSending, timeMatrix, rule=Limit32)

        ###########################################################################################################################

        # Earning of the Agents
        ###########################################################################################################################

        def Limit33(model, AS, T):
            return model.Earning[AS,T] == model.InternalTransferCost[AS, T] + model.ExternalTransferCost[AS, T] - model.DegradationCost[AS, T]

        model.limit33 = Constraint(AgentsetSending, timeMatrix, rule=Limit33)

        solver = SolverFactory('gurobi')
        solver.options['timelimit'] = 60
        results = solver.solve(model) # , tee=True, logfile="GUROBI.log"

        varEarning = {key: {index: model.Earning[key, index]() for index in timeMatrix} for key in AgentsetSending}
        varDeg = {key: {index: model.OveralDegradation[key, index]() for index in timeMatrix} for key in AgentsetSending}
        varSoC = {key: {index: model.SoC[key, index]() for index in timeMatrix} for key in AgentsetSending}
        varsending = {key1: {index: {key2: model.InternalTransferSending[key1, key2, index]() for key2 in AgentsetSending} for index in timeMatrix}for key1 in AgentsetSending}
        varreceiving = {key1: {index: {key2: model.InternalTransferReceiving[key1, key2, index]() for key2 in AgentsetSending} for index in timeMatrix} for key1 in AgentsetSending}
        varSellGrid = {key: {index: model.ExternalTransferSelling[key, index]() for index in timeMatrix} for key in AgentsetSending}
        varBuyGrid = {key: {index: model.ExternalTransferBuying[key, index]() for index in timeMatrix} for key in AgentsetSending}
        varInsertBattery = {key: {index: model.InsertToBattery[key, index]() for index in timeMatrix} for key in AgentsetSending}
        varExtractBattery = {key: {index: model.ExtractFromBattery[key, index]() for index in timeMatrix} for key in AgentsetSending}
        varChangeBattery = {key: {index: model.BatteryChange[key, index]() for index in timeMatrix} for key in AgentsetSending}
        varStatus = {key: {index: model.StatusMatrix[key, index]() for index in timeMatrix} for key in AgentsetSending}

        xlsxFile(varStatus, varsending, varreceiving, varSellGrid, varBuyGrid, varInsertBattery, varExtractBattery, varDeg, varSoC, varChangeBattery, varEarning ,dayNumber, 8, 2022,AgentsetSending)
        #model.EnergyBalance.display()
        return varEarning, varDeg, varSoC



