from ..public.scenarioDataObj import *
from .taxiMap import TaxiMap
from .flightPlanGen import FlightPlanGen
from .flightPlan import FlightPlan
from ..public.dataManage import DataManager
from math import *
from ..public.config import ConfigReader

class FlightPlanMgr(object):
    def __init__(self, pDataManager):
        self.FlightPlanDic = {} ##所有生成的飞行计划数据 格式{ id, 'FlightPlan'}
        self.curFlightPlanDic = {} ##当前需要参加运算的飞行计划集合
        self.iCurFlanID = -1
        self.pTaxiMap = TaxiMap(self, pDataManager)
        self.pDataManage = pDataManager
    ##brief 创建飞行计划
    def createFlightPlan(self, iSeq):
        pFlightPlanLst = FlightPlanGen.geneFlightPlan(iSeq, self.pDataManage)
        for i in range(len(pFlightPlanLst)):
            self.FlightPlanDic.setdefault(pFlightPlanLst[i].getFlightPlanID(), pFlightPlanLst[i])

    ##1、获取下一个飞行计划，如果为空表示该episode结束，时间根据ID递增
    ##2、判断是否该飞行计划时候是否有飞行计划已经结束并置位
    ##3、如果开始为-1证明从头开始取
    def getNextFlightPlan(self, iStartID = -1):
        iNextPlanID = -1
        if iStartID == -1:
            iNextPlanID = 1
        else:
            iNextPlanID = iStartID + 1
        pFlightPlan = self.FlightPlanDic.get(iNextPlanID)
        if pFlightPlan == None:
            return  None
        else:
            return  pFlightPlan

    def setCurFlightPlanID(self, iFPlanID):
        self.iCurFlanID = iFPlanID

    ##更新未来的飞行计划看是否结束
    def updateFutureFlightPlan(self):
        pass

    ##更新飞行计划状态
    def updateFlightPlan(self, iTime):
        for k in self.curFlightPlanDic:
            pFlightPlan = self.curFlightPlanDic.get(k)
            pFlightPlan.updateTaxState(iTime)


    ##brief 获取指定ID的飞行计划
    def getFlightPlanByID(self, iFPlanID):
        return self.FlightPlanDic.get(iFPlanID)

    def getAllFlightPlanBestPath(self):
        PathIDLst = []
        for i in self.FlightPlanDic:
            pFlightPlan = self.FlightPlanDic.get(i)
            FPPathData = pFlightPlan.getFlightPlanPath()
            PathIDLst.append(FPPathData.iPathID)
        return PathIDLst

    def addCurPath2TaxMap(self):
        pCurFlightPlan = self.curFlightPlanDic.get(self.iCurFlanID)
        self.pTaxiMap.addFlightPlanPath(pCurFlightPlan)

    def addFutureFlightPlan(self, iTime):
        ##当前计划
        pCurFlightPlan = self.getFlightPlanByID(self.iCurFlanID)
        if self.curFlightPlanDic.get(self.iCurFlanID) == None:
            self.curFlightPlanDic.setdefault(self.iCurFlanID, pCurFlightPlan)

        ##后续计划
        pFlightPlan = self.getNextFlightPlan(self.iCurFlanID)
        while pFlightPlan != None:
            iFutureFlightPlanID = pFlightPlan.getFlightPlanID()
            iStartTime = pFlightPlan.getFlightPlanStartTime()
            ##开始时间大于未来时间时候直接退出循环
            if  iStartTime <= iTime:
                if self.curFlightPlanDic.get(iFutureFlightPlanID) == None:
                    self.curFlightPlanDic.setdefault(iFutureFlightPlanID, pFlightPlan)
                    ##添加当前从没加入到未来航班汇总的计划到滑行地图中
                    self.pTaxiMap.addFlightPlanPath(pFlightPlan)
            else:
                break
            iFutureFlightPlanID += 1
            pFlightPlan = self.getNextFlightPlan(iFutureFlightPlanID)

    def refreshFlightPlan(self):
        delKeyLst = []
        for k in self.curFlightPlanDic:
            pFlightPlan = self.FlightPlanDic.get(k)
            if k < self.iCurFlanID:
                if pFlightPlan.isFlightPlanFin():
                    ##删除taxiMap滑行路线
                    self.pTaxiMap.delFlightPlanPath(pFlightPlan.getFlightPlanID())
                    ##删除飞行计划
                    delKeyLst.append(k)
                    # del self.curFlightPlanDic[k]
            elif k == self.iCurFlanID:
                pFlightPlan.updateFPStatus(ENUM_FP_STATUS.E_STATUS_ACTIVE)
                pFlightPlan.clearPath()
                ##删除当前的滑行数据
                self.pTaxiMap.delFlightPlanPath(self.iCurFlanID)
            else:
                pFlightPlan.updateFPStatus(ENUM_FP_STATUS.E_STATUS_FUTURE)

        for i in range(len(delKeyLst)):
            del self.curFlightPlanDic[delKeyLst[i]]

    def isFlightPlanStartByID(self, iFlightPlanID):
        return  self.FlightPlanDic.get(iFlightPlanID).isFplightPlanStart()

    ##重置飞行计划状态，主要用于显示查看
    def resetFlightPlanData(self):
        for i in self.FlightPlanDic:
            pFlightPlan = self.FlightPlanDic.get(i)
            pFlightPlan.updateFPStatus(ENUM_FP_STATUS.E_STATUS_FUTURE)

    def updateFlightPlanData(self, iTime):
        for i in self.FlightPlanDic:
            pFlightPlan = self.FlightPlanDic.get(i)
            pFlightPlan.updateTaxState(iTime)

    def getActiveFlightPlanLst(self, iTime):
        ActiveFightPlanLst = []
        for i in self.FlightPlanDic:
            pFlightPlan = self.FlightPlanDic.get(i)
            eFPSTatus = pFlightPlan.getFlightFPStatus()
            if eFPSTatus == ENUM_FP_STATUS.E_STATUS_FUTURE or eFPSTatus == ENUM_FP_STATUS.E_STATUS_FIN:
                continue
            else:
                ActiveFightPlanLst.append(pFlightPlan)
        return ActiveFightPlanLst

    ##判断经过学习后仍然后冲突
    def judgeIsHasConflict(self, bAll = False):

        PntPassTimeDic = {}
        if bAll == True:
            self.resetFlightPlanData()
            FlightPlanDic = self.FlightPlanDic
        else:
            FlightPlanDic = self.curFlightPlanDic
        ##过节点时间小于则规定值则仍为有冲突
        ##如果为未来计划则不管
        for k in self.FlightPlanDic:
            pFlightPlan = self.FlightPlanDic.get(k)
            eStatus = pFlightPlan.getFlightFPStatus()
            if eStatus == ENUM_FP_STATUS.E_STATUS_FUTURE:
                continue
            elif eStatus == ENUM_FP_STATUS.E_STATUS_FIN:
                print('Error:当前飞行计划集合中存在已经完成的计划')
            stFPPathData = pFlightPlan.getFlightPlanPath()
            for m in range(len(stFPPathData.vFPPassPntData)):
                stPassFixData = stFPPathData.vFPPassPntData[m]
                if PntPassTimeDic.get(stPassFixData.iFixID) == None:
                    PntPassTimeDic.setdefault(stPassFixData.iFixID, [stPassFixData.iRealPassTime])
                else:
                    for i in range(len(PntPassTimeDic.get(stPassFixData.iFixID))):
                        iRealPassTime = PntPassTimeDic.get(stPassFixData.iFixID)[i]
                        if  fabs(stPassFixData.iRealPassTime - iRealPassTime) < ConfigReader.iResolveConfilictTime:
                            print('warning:仍然存在过点时间冲突，当前时间阈值{0}'.format(ConfigReader.iResolveConfilictTime))
                    PntPassTimeDic.get(stPassFixData.iFixID).append(stPassFixData.iRealPassTime)
