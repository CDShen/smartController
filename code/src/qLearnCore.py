from ..public.dataObj import *
from .utility import UtilityTool
from ..public.dataManage import DataManager
from ..public.config import ConfigReader
from ..public.baseDataDef import BaseData
from ..public.dataObj import *
from .flightPlan import FlightPlan
from enum import Enum

# class E_QDataStateType(Enum):
# 	E_QDATA_STATE_MODIFY = 1 ##修改
# 	E_QDATA_STATE_ADD    = 2 ##新加


# class QStateActionScoreData(BaseData):
# 	_fields = ['QStateActionScoreData', 'eQDataStateType']

# 1、回报函数R(s,a)
# 2、动作A
# 3、评价函数Q(s,a)
# 4、解决冲突函数
# 5、预测时间函数

class LearnFunction(object):
	pass



class QLearnFunction(LearnFunction):
	def __init__(self, pDataManager):
		self.dBeta =ConfigReader.dBeta
		self.QStateActionScoreDataLst = None
		self.pDataManager = pDataManager
		self.pFlightPlan = FlightPlan

	def setCurFlightPlan(self, pFlightPlan):
		self.pFlightPlan = pFlightPlan
	# state[in] 冲突状态
	# path[out] 最高分数的滑行路线
	# return 最高分数
	def getScore(self, state, path):
		pass
	##breif:Q学习回报函数
	##remark:目前Q只是回报只处理当前飞机的滑行路线
	def _reward(self, QStateData, eActionType, PathData, pConFlightPlan, ConflictData):
		FPPath = None
		dReward = 0.0
		dScore = 0.0 ##分数等于计划路线乘以系数
		iOrgTotalTime = UtilityTool.getTotalPathTaxiTime(PathData)
		curFPathData = self.pFlightPlan.getFlightPlanPath()
		iStartTime = self.pFlightPlan.getFlightPlanStartTime()
		conFPPathData = pConFlightPlan.getFlightPlanPath()
		dTheta = ConfigReader.dTheta

		FPPath = UtilityTool.resolveConflictByAction(curFPathData, conFPPathData, ConflictData, eActionType)


		if FPPath == None:
			dReward = ConfigReader.dNonePathFine
		else:
			iConflictTime = UtilityTool.getTotalFPTaxiTime(iStartTime,FPPath)
			dRatio = dTheta*(iConflictTime/iOrgTotalTime) + (1-dTheta)*self.pDataManager.getPathAverageRatio(PathData.iPathID)
			dReward = 1/dRatio
			dScore  = iOrgTotalTime * dReward




		return  dReward, FPPath, dScore
	##brief 更新Q值并返回分数和路线
	##warn:注意是否能通过引用方式更新值
	def _updateQValue(self, QStateActionScoreData, PathData,pConFlightPlan, ConflictData):
		ScorePathDic = {'score': None, 'orgPath': None, 'FPPath':None, 'qscore':None}
		score = 0.0
		orgPath = PathData
		FPPath = None
		QStateData = QStateActionScoreData.QStateData
		eActionType = QStateActionScoreData.QActionData
		dReward ,FPPath, score = self._reward(QStateData, eActionType, PathData, pConFlightPlan ,ConflictData)

		QStateActionScoreData.dScore = QStateActionScoreData.dScore *(1.0-self.beta) + self.beta*dReward
		ScorePathDic['score'] = score
		ScorePathDic['path'] = orgPath
		ScorePathDic['FPPath'] = FPPath
		ScorePathDic['qscore'] = QStateActionScoreData.dScore


		return ScorePathDic

	def _getQValue(self, state, action):
		dScore=0.0
		return dScore

	##brief 本地是否存有QState数据
	##bFind[out]:是否查找到最新缓存池中数据
	##QStateActionScoreDataLst[out]:返回该状态所有动作对应数据
	##remark 如果找到，数量和动作数量一致
	def _findQStateLocal(self, QStateData):
		bFind = False
		QStateActionScoreDataLst = []
		iCount = 0
		for i in range(len(self.QStateActionScoreDataLst)):
			stQStateData = self.QStateActionScoreDataLst[i].QStateActionScoreData.QStateData
			if stQStateData == QStateData:
				QStateActionScoreDataLst.append(QStateActionScoreDataLst[i])
				iCount+=1
				if iCount == 2:
					bFind = True
					return bFind, QStateActionScoreDataLst

		return bFind, QStateActionScoreDataLst

	def _findQState(self, QStateData):
		bFind, QStateActionScoreDataLst = self._findQStateLocal(QStateData)
		if bFind == False:
			bFind, QStateActionScoreDataLst = self.pDataManager.findQState(QStateData)
			if bFind == True:
				for i in range(len(QStateActionScoreDataLst)):
					self.QStateActionScoreDataLst.append(QStateActionScoreDataLst[i])
			else:
				for eAction in  ENUM_QACTION_TYPE:
					stQStateData = QStateData
					eActionType = eAction
					dScore = 1.0
					QStateActionScoreData = QStateActionScoreData(stQStateData,eActionType,dScore)
					self.QStateActionScoreDataLst.append(QStateActionScoreData)
					QStateActionScoreDataLst.append(QStateActionScoreData)

		return 	QStateActionScoreDataLst

	@classmethod
	def __transData2QState(cls,pFlightPlan, PathData, pConFlightPlan, ConflictData):

		iStartFixID = PathData.vPassPntData[0].iFixID
		iEndFixID = PathData.vPassPntData[len(PathData.vPassPntData) - 1].iFixID
		iConflictFixID = ConflictData.iConflictFixID
		efixPntType = ConflictData.efixPntType
		eCurFlightType = pFlightPlan.getFlightType()
		eConFlightType = pConFlightPlan.getFlightType()
		eConflictType = ConflictData.eConfType
		iPathID = PathData.iPathID
		iConPathID = pConFlightPlan.getFlightPlanPath().iPathID

		return QStateData(iStartFixID, iEndFixID, iConflictFixID, eCurFlightType, eCurFlightType, \
		                  eConFlightType, eConflictType, iPathID, iConPathID)

	def pathSelect(self, pFlightPlan, PathData, pConFlightPlan, ConflictData):
		QStateData = QLearnFunction.__transData2QState(pFlightPlan, PathData, pConFlightPlan, ConflictData)
		QStateActionScoreDataLst = self._findQState(QStateData)
		ScorePathDicLst = []
		for i in range(len(QStateActionScoreDataLst)):
			ScorePathDic = self._updateQValue(self, QStateActionScoreDataLst[i], PathData,pConFlightPlan, ConflictData)
			ScorePathDicLst.append(ScorePathDic)


		##路线排序,冒泡分数由大到小
		for i in range(len(ScorePathDicLst) - 1):
			bOK = True
			for j in range(0, len(ScorePathDicLst) - 1 - i):
				item = ScorePathDicLst[j]
				itemNext = ScorePathDicLst[j + 1]
				if item.get('qscore') < itemNext.get('qscore'):
					itemTmp = itemNext
					ScorePathDicLst[j + 1] = item
					ScorePathDicLst[j] = itemTmp
					bOK = False
			if bOK:
				break

		dMaxScore = ScorePathDicLst[0].get('score')
		bestPath = ScorePathDicLst[0].get('path')
		dFPPath = None
		return dMaxScore,bestPath,dFPPath








