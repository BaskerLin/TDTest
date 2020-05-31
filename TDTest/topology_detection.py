# coding:utf-8

import pymel.core as pm
import maya.cmds as mc

from maya.app.general.mayaMixin import MayaQWidgetBaseMixin

# from PySide2 import QtWidgets, QtCore
# from PySide2.QtUiTools import QUiLoader

from Qt import QtWidgets
from Qt.QtCompat import loadUi

import os
import time

#获取当前文件所在路径
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(CURRENT_PATH, "Exam2.ui")

class TopologyDetectionWin(MayaQWidgetBaseMixin,QtWidgets.QWidget):
    def __init__(self):
        super(TopologyDetectionWin, self).__init__()

        self.show()
        pos = self.pos()

        loadUi(UI_PATH, self)

        self.move(pos)
        self.setWindowTitle(u"模型拓扑对比")

        # 避免出现重复的窗口
        object_name = "TopologyDetectionWin"
        if pm.window(object_name,ex=1):
            pm.deleteUI(object_name)
        self.setObjectName(object_name)


        #默认值
        self.lineEdit_pointNum.setReadOnly(True)
        self.lineEdit_edgeNum.setReadOnly(True)
        self.lineEdit_faceNum.setReadOnly(True)
        self.lineEdit_time.setReadOnly(True)
        self.lineEdit_result.setReadOnly(True)
        self.textEdit_transInfor1.setReadOnly(True)
        self.textEdit_transInfor2.setReadOnly(True)


        #消息响应
        self.btn_detect.clicked.connect(self.detect_topology)


    def detect_topology(self):
        curr = time.time()

        sellist = [mesh for mesh in pm.ls(pm.pickWalk(d="down"), type="mesh")]  # pm.ls  返回场景中被选中的对象
        # pickWalk命令允许您相对于当前选定的节点快速更改选择列表


        if len(sellist) != 2:
            pm.headsUpMessage(u"请选中两个对象")
            return 0

        self.lineEdit_pointNum.clear()
        self.lineEdit_edgeNum.clear()
        self.lineEdit_faceNum.clear()
        self.textEdit_transInfor1.clear()
        self.textEdit_transInfor2.clear()

        W = True
        numlist = [(sel.numVertices(), sel.numEdges(), sel.numFaces()) for sel in sellist]  # num_list是2*3的列表


        # 点、线、面数量不一至，拓扑肯定不一样
        if numlist[0][0] != numlist[1][0]:
            W = False
            x = numlist[0][0] - numlist[1][0]
            self.lineEdit_pointNum.setText(str(x))
        if numlist[0][1] != numlist[1][1]:
            W = False
            x = numlist[0][0] - numlist[1][0]
            self.lineEdit_edgeNum.setText(str(x))
        if numlist[0][2] != numlist[1][2]:
            W = False
            x = numlist[0][0] - numlist[1][0]
            self.lineEdit_faceNum.setText(str(x))


        if numlist[0][1] > numlist[1][1]:
            sellist.reverse()
            edgenum = numlist[1][1]
        else:
            edgenum = numlist[0][1]
        # 把数量小的换到前面


        res_list = []
        dif_list1 = []
        dif_list2 = []
        for i, sel in enumerate(sellist):  # enumerate() 列出数据和数据下标 (0, mesh1)

            edgeLoop_list = []
            edge_list = set(range(edgenum))

            while len(edge_list) > 1:
                idx = next(iter(edge_list), None)  # iter() 函数用来生成迭代器  next()返回迭代器的下一个项目

                if idx is None: break
                edge_loop_1 = pm.polySelect(sel, edgeLoop=idx, ns=1)  #

                edgeLoop_list.append(edge_loop_1)  # 遍历过的边的列表添加进循环边的表
                edge_list -= set(edge_loop_1)      # 遍历过的边删去

                # NOTE 这里先判断一下同一个边序号获取的循环边数组是否一致
                if i != 0: continue


                edge_loop_2 = pm.polySelect(sellist[1].e[edge_loop_1[0]], edgeLoop=idx, ns=1)
                # 第二个对象的第idx条循环边

                if edge_loop_2 != edge_loop_1:
                    dif_list1.append(edge_loop_1)
                    dif_list2.append(edge_loop_2)



            res_list.append(edgeLoop_list)

        W = (res_list[0] == res_list[1])


        if not W:

            for edgeloops in dif_list1:
                self.textEdit_transInfor1.append(str(edgeloops))
                self.textEdit_transInfor1.append(u"  ")

            for edgeloops in dif_list2:
                self.textEdit_transInfor2.append(str(edgeloops))
                self.textEdit_transInfor2.append(u"  ")

            pm.select(["%s.e[%s]" % (sellist[0],e)  for sel in dif_list1 for e in sel],r=1)
            pm.select(["%s.e[%s]" % (sellist[1],e)  for sel in dif_list2 for e in sel],add=1)
            self.lineEdit_result.setText(u"拓扑不一致")
        else:
            self.lineEdit_result.setText(u"拓扑一致")

        self.lineEdit_time.setText(str(time.time() - curr))





def main():
    win = TopologyDetectionWin()
    return win



