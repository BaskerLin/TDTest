# coding:utf-8

import pymel.core as pm
from maya import OpenMaya
import time
import math
from maya.app.general.mayaMixin import MayaQWidgetBaseMixin

# from PySide2 import QtWidgets, QtCore
# from PySide2.QtUiTools import QUiLoader

from Qt import QtWidgets, QtGui
from Qt.QtCompat import loadUi

from functools import partial

import os

# 获取当前文件所在路径
CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(CURRENT_PATH, "Exam3.ui")


class CheckIntersectionWin(MayaQWidgetBaseMixin, QtWidgets.QWidget):
    def __init__(self):
        super(CheckIntersectionWin, self).__init__()

        self.show()
        pos = self.pos()

        loadUi(UI_PATH, self)

        self.move(pos)

        self.setWindowTitle(u"maya模型穿插检测")

        # 避免出现重复的窗口
        object_name = "TopologyDetectionWin"
        if pm.window(object_name, ex=1):
            pm.deleteUI(object_name)
        self.setObjectName(object_name)

        # 设置默认值
        self.lineEdit_time.setReadOnly(True)
        self.textEdit_Pos.setReadOnly(True)

        # 滚动条
        self.ver_scr1 = self.listWidget_ID.verticalScrollBar()
        self.ver_scr2 = self.textEdit_Pos.verticalScrollBar()
        # NOTE 添加保护 flag
        self.ver_scr1.protected = True
        self.ver_scr2.protected = True
        self.ver_scr1.valueChanged.connect(partial(self.move_scrollbar, self.ver_scr1))
        self.ver_scr2.valueChanged.connect(partial(self.move_scrollbar, self.ver_scr2))

        self.listWidget_ID.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # 消息响应
        self.btn_other.clicked.connect(self.do_check_other)
        self.btn_self.clicked.connect(self.do_check_self)
        self.btn_select_all.clicked.connect(self.select_all)

        self.listWidget_ID.itemSelectionChanged.connect(self.item_click_multiple)

        self.hitface_list = []  # 储存穿插面

    # 滚动条同步
    def move_scrollbar(self, scroll, value):
        # NOTE 保护 flag 避免互相调用 影响滚动
        if scroll.protected:
            scroll.protected = False
        else:
            return
        scroll.setValue(value)
        ratio = float(value) / scroll.maximum()
        sync_scroll = self.ver_scr1 if scroll is self.ver_scr2 else self.ver_scr2
        val = int(ratio * sync_scroll.maximum())
        sync_scroll.setValue(val)
        scroll.protected = True

    # 两个模型穿插检测
    def find_intersection_other(self, mesh1, mesh2):

        mesh1_dagPath = mesh1.__apimdagpath__()  # mesh的节点路径
        mesh2_dagPath = mesh2.__apimdagpath__()

        mesh1_itr = OpenMaya.MItMeshEdge(mesh1_dagPath)  # MItMeshEdge 多边形边迭代器
        mesh2_mesh = OpenMaya.MFnMesh(mesh2_dagPath)

        util = OpenMaya.MScriptUtil()  # MScriptUtil 实用程序类，用于在Python中使用指针和引用
        edge_len_ptr = util.asDoublePtr()  # asDoublePtr() 返回指向此类数据的双指针。

        edge_list = set()
        while not mesh1_itr.isDone():
            mesh1_itr.getLength(edge_len_ptr)  # getLength()返回当前边的长度。
            edge_len = util.getDouble(edge_len_ptr)  # getDouble() 获取Double型参数的值

            start_pt = mesh1_itr.point(0, OpenMaya.MSpace.kWorld)  # point()返回当前边的指定顶点的位置。
            end_pt = mesh1_itr.point(1, OpenMaya.MSpace.kWorld)  # MSpace 空间转换标识符
            # kWorld 对象世界坐标系的数据

            raySource = OpenMaya.MFloatPoint(start_pt)  # MFloatPoint 以浮点类型来实现处理点
            rayDirection = OpenMaya.MFloatVector(end_pt - start_pt)  # MFloatVector  浮点数向量的向量类
            faceIds = None
            triIds = None
            idsSorted = False  # 不排序
            space = OpenMaya.MSpace.kWorld
            maxParam = edge_len  # 边长度、搜索半径
            testBothDirections = False  #
            accelParams = mesh2_mesh.autoUniformGridParams()  # autoUniformGridParams创建一个MMeshIsectAccelParams配置对象
            sortHits = False
            hitPoints = OpenMaya.MFloatPointArray()  # MFloatPoint数据类型的矩阵
            hitRayParams = None
            hitFaces = OpenMaya.MIntArray()  # int数据类型矩阵
            hitTriangles = None
            hitBary1s = None
            hitBary2s = None

            rayDirection.normalize()  # 单位化

            gotHit = mesh2_mesh.allIntersections(
                raySource, rayDirection, faceIds, triIds, idsSorted, space, maxParam, testBothDirections, accelParams,
                sortHits, hitPoints, hitRayParams, hitFaces, hitTriangles, hitBary1s, hitBary2s)
            # allIntersections 查找从raySource开始并与mesh在rayDirection中传播的射线的所有交点。
            # 如果faceIds和triIds均为NULL，则将考虑网格中的所有三角形面片。
            # 返回值True、False

            if gotHit:
                edge_list.add(mesh1_itr.index())  # 把边的序号存入edge_list

            mesh1_itr.next()

        # 获取碰撞的边再通过边转面
        edge_list = ["%s.e[%s]" % (mesh1_dagPath.fullPathName(), edge_id) for edge_id in edge_list]

        facelist = pm.polyListComponentConversion(edge_list, fe=True, tf=True)
        # polyListComponentConversion 将多边形组件从一种或多种类型转换为另一种或多种类型
        # fromEdge（fe）toFace（tf）

        # 展平序号
        return pm.ls(facelist, flatten=True)

    # 单个模型穿插检测
    def find_intersection_self(self):
        thersold = 0.0001

        face_list = OpenMaya.MSelectionList()  # MSelectionList 全局选择列表,MObject的列表。
        hitface_list = []  # 用于储存穿插面

        sel_list = OpenMaya.MSelectionList()
        OpenMaya.MGlobal.getActiveSelectionList(sel_list)  # 选择存储的列表

        path = OpenMaya.MDagPath()
        comp = OpenMaya.MObject()
        util = OpenMaya.MScriptUtil(0)  # MScriptUtil 实用程序类，用于在Python中使用指针和引用。
        space = OpenMaya.MSpace.kWorld

        for num in range(sel_list.length()):
            sel_list.getDagPath(num, path, comp)  # 获得DAG路径
            node = OpenMaya.MFnDagNode(path)  # 获得DAG节点

            itr1 = OpenMaya.MItMeshPolygon(path)  # 多边形迭代器
            itr2 = OpenMaya.MItMeshPolygon(path)

            while not itr1.isDone():

                count = itr1.index()

                point_list1 = OpenMaya.MPointArray()  # Mpoint类型的矩阵
                index_list1 = OpenMaya.MIntArray()  # int类型矩阵

                itr1.getTriangles(point_list1, index_list1, space)  # 获取三角形面片中所有顶点和顶点位置
                tri_num_1 = point_list1.length() / 3  # 顶点数除以3，三角面片的数量

                while count < itr2.count() - 1:  # 最后是同一个对象，所以减一
                    count += 1
                    itr2.setIndex(count, util.asIntPtr())

                    point_list2 = OpenMaya.MPointArray()
                    index_list2 = OpenMaya.MIntArray()

                    itr2.getTriangles(point_list2, index_list2, space)
                    tri_num_2 = point_list2.length() / 3

                    p1 = [1, 2, 3]
                    for i in range(tri_num_1):
                        # 获取第一个三角面的点和法线
                        p1[0] = point_list1[i * 3]
                        p1[1] = point_list1[i * 3 + 1]
                        p1[2] = point_list1[i * 3 + 2]
                        u1 = p1[0] - p1[1]
                        v1 = p1[0] - p1[2]
                        n1 = u1 ^ v1
                        n1.normalize()

                        p2 = [1, 2, 3]
                        for j in range(tri_num_2):

                            # 另一个三角面的点和法线
                            p2[0] = point_list2[j * 3]
                            p2[1] = point_list2[j * 3 + 1]
                            p2[2] = point_list2[j * 3 + 2]
                            u2 = p2[0] - p2[1]
                            v2 = p2[0] - p2[2]
                            n2 = u2 ^ v2
                            n2.normalize()

                            u = n1 ^ n2  # 法线差乘 平面交线方向
                            x = abs(u.x)
                            y = abs(u.y)
                            z = abs(u.z)  # 各个方向夹角
                            # 两个面几乎平行，不考虑

                            if (x + y + z) < thersold:
                                continue

                            v1 = n2 * (p1[0] - p2[0])
                            v2 = n2 * (p1[1] - p2[0])
                            v3 = n2 * (p1[2] - p2[0])  # 点乘
                            # 如果有两个点几乎重合,跳过
                            if abs(v1) < thersold:
                                continue
                            if abs(v2) < thersold:
                                continue
                            if abs(v3) < thersold:
                                continue

                            # 其中一个正负不同，即为不在同一边，说明与三角形与平面穿插
                            if not (v1 > 0 and v2 > 0 and v3 > 0) or not (v1 < 0 and v2 < 0 and v3 < 0):

                                # p1[0]是穿插点
                                if (v1 > 0 and v2 < 0 and v3 < 0) or (v1 < 0 and v2 > 0 and v3 > 0):
                                    hp1 = self.getHitPoint(p1[1], p1[0], p2[0], n2)
                                    hp2 = self.getHitPoint(p1[2], p1[0], p2[0], n2)
                                # p1[1]是穿插点
                                elif (v1 < 0 and v2 > 0 and v3 < 0) or (v1 > 0 and v2 < 0 and v3 > 0):
                                    hp1 = self.getHitPoint(p1[0], p1[1], p2[0], n2)
                                    hp2 = self.getHitPoint(p1[2], p1[1], p2[0], n2)
                                # p1[2]是穿插点
                                elif (v1 < 0 and v2 < 0 and v3 > 0) or (v1 > 0 and v2 > 0 and v3 < 0):
                                    hp1 = self.getHitPoint(p1[0], p1[2], p2[0], n2)
                                    hp2 = self.getHitPoint(p1[1], p1[2], p2[0], n2)
                                else:
                                    continue

                                if self.triangleInside(hp1, p2[0], p2[1], p2[2]) or \
                                        self.triangleInside(hp2, p2[0], p2[1], p2[2]):
                                    face_list.add("%s.f[%s]" % (node.fullPathName(), itr1.index()))
                                    face_list.add("%s.f[%s]" % (node.fullPathName(), itr2.index()))

                                    hitface_list.append(["%s.f[%s]" % (node.fullPathName(), itr1.index())])
                                    hitface_list.append(["%s.f[%s]" % (node.fullPathName(), itr2.index())])

                                    break

                            else:
                                continue

                            break

                        else:
                            continue

                        break

                itr1.next()

        OpenMaya.MGlobal.setActiveSelectionList(face_list)

        return hitface_list

    # 获得碰撞点
    def getHitPoint(self, p1, p2, p3, n):
        dir1 = p1 - p2
        w = p3 - p2
        a = w * n
        b1 = dir1 * n
        r1 = a / b1
        return p2 + dir1 * r1

    # 判断碰撞点是否在三角面当中
    def triangleInside(self, hitpoint, p0, p1, p2):
        u = p1 - p0
        v = p2 - p0
        uu = u * u
        uv = u * v
        vv = v * v
        w = hitpoint - p0
        wu = w * u
        wv = w * v
        D = uv * uv - uu * vv
        s = (uv * wv - vv * wu) / D
        t = (uv * wu - uu * wv) / D
        if (s <= 0.0 or s >= 1.0) or (t <= 0.0 or (s + t) >= 1.0):
            return False
        return True

    # 执行两个模型穿插检测
    def do_check_other(self):

        self.hitface_list = []
        self.listWidget_ID.clear()
        self.textEdit_Pos.clear()

        curr = time.time()

        sellist = [mesh for mesh in pm.ls(pm.pickWalk(d="down"), type="mesh")]

        if len(sellist) >= 2:

            for i in range(len(sellist)):
                for j in range(i + 1, len(sellist)):
                    f = self.find_intersection_other(sellist[i], sellist[j])

                    self.hitface_list += f
                    if f != None:
                        self.hitface_list += self.find_intersection_other(sellist[j], sellist[i])  # 两个对象都需要

            centerpos = [0, 1, 2]
            for face in self.hitface_list:

                self.listWidget_ID.addItem(str(face))

                pos = pm.xform(face, q=1, ws=1, t=1)
                for i in range(3):
                    centerpos[i] = (pos[i] + pos[i + 3] + pos[i + 6] + pos[i + 9]) / 4  # 求面中心点位置
                self.textEdit_Pos.append(str(centerpos))

            pm.select(self.hitface_list)
            self.lineEdit_time.setText(str(time.time() - curr))

    # 执行单个模型穿插检测
    def do_check_self(self):

        self.hitface_list = []
        self.listWidget_ID.clear()
        self.textEdit_Pos.clear()

        curr = time.time()
        hitface_list = self.find_intersection_self()

        centerpos = [0, 1, 2]
        for face in hitface_list:
            name = str(face).split("u'|")[-1].split("'")[0]
            self.hitface_list.append(name)
            self.listWidget_ID.addItem(name)

            pos = pm.xform(face, q=1, ws=1, t=1)
            for i in range(3):
                centerpos[i] = (pos[i] + pos[i + 3] + pos[i + 6] + pos[i + 9]) / 4  # 求面中心点位置
            self.textEdit_Pos.append(str(centerpos))

        pm.select(self.hitface_list)
        self.lineEdit_time.setText(str(time.time() - curr))

    # 选择所有穿插面
    def select_all(self):
        pm.select(self.hitface_list)

    # QListWidget 响应函数
    def item_click_multiple(self):
        items = self.listWidget_ID.selectedItems()
        hitface_list = []
        for item in items:
            face = item.text()
            hitface_list.append(face)

        pm.select(hitface_list)


def main():
    win = CheckIntersectionWin()
    return win


if __name__ == "main":
    main()