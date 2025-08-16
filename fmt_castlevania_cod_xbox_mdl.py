#
# Castlevania curse of darkness XBox Model loader
# alanm1
#
# v0.1 initial release

#
#Based on:
#Tomb Raider: Underworld/Lara Croft and The Guardian Of Light [PC/X360] - ".tr8mesh" Loader
#By Gh0stblade
#v2.4
#Special thanks: Chrrox
debug = 0                       #Prints debug info (1 = on, 0 = off)

from inc_noesis import *
import math
import glob
import re
import copy
from operator import itemgetter, attrgetter
from collections import deque, namedtuple
from io import *
    
def registerNoesisTypes():
    handle = noesis.register("Castlevania C of D: 3D Mesh [XBox]", ".mdl")
    noesis.setHandlerTypeCheck(handle, meshCheckType)
    noesis.setHandlerLoadModel(handle, meshLoadModel)

    #noesis.logPopup()
    return 1
    
def meshCheckType(data):
    bs = NoeBitStream(data)
    uiMagic = bs.read("I")
    
    if uiMagic[0] == 0xFFFF0003:
        return 1      
    return 0

class meshFile(object):
    
    def __init__(self, data):
        self.inFile = None
        self.texExtension = ""
        
        self.inFile = NoeBitStream(data)
            
        self.fileSize = int(len(data))
        
        self.meshGroupIdx = 0
        self.offsetMeshStart = -1
        self.offsetStart = -1
        self.offsetMatInfo = -1
        self.numBones = -1
        self.numMeshes = 0
        self.offsetBones = 0
        self.offsetMeshes = 0
        self.offsetMeshes2 = 0
        self.numMeshes2 = 0

        self.offsetVertex = 0
        self.offsetFaceIdx = 0
        self.numVertices = 0
        self.offsetSkel = 0
        self.numBones2 = 0
        self.offsetSkel2 = 0
        self.offsetBones2 = 0
        self.morph_base_cnt = 0
        self.morph_base_offs = 0
        self.morph_data_cnt = 0
        self.morph_data_offs = 0
        
        self.bonePair = []
        self.meshOffsets = []
        self.boneList = []
        self.boneMap = []
        self.matList = []
        self.matNames = []
        self.texList = []
        self.texNames = []
        self.boneTrans = []
        self.boneMat = []
        self.boneMat2 = []
        self.matTable = []
        self.matHash = {}
        self.morph_targets = []
        

    def loadMesh(self):
        self.offsetMeshStart = 0
        bs = self.inFile
        uiMagic = bs.readUInt()
        uiUnk = bs.readUInt()
        self.offsetBones = bs.readUInt()
        self.numBones = bs.readUInt();
        self.offsetSkel = bs.readUInt();
        self.numBones2 = bs.readUInt()
        self.offsetBonePair = bs.readUInt()
        self.offsetBones2 = bs.readUInt()

        self.numMeshes = bs.readUInt();
        self.offsetMeshes = bs.readUInt()
        self.numMeshes2 = bs.readUInt()
        self.offsetMeshes2 = bs.readUInt()
        self.num_Material = bs.readUInt()
        bs.seek(4,NOESEEK_REL);
        self.num_matTableEntry = bs.readUInt()
        self.offset_matTable = bs.readUInt()
        bs.readUInt()  # unknown
        self.morph_base_cnt = bs.readUInt()
        self.morph_base_offs = bs.readUInt()
        self.morph_data_cnt = bs.readUInt()
        self.morph_data_offs = bs.readUInt()
        
        bs.seek( self.offsetMeshStart + self.offset_matTable);
        # build matID to texture mapping
        for i in range(self.num_matTableEntry):
            self.matTable.append( [bs.readUInt(),bs.readUInt()]) # texture ID, unknownID
              
        self.buildSkeleton() 
        # second bone list is a bonepair list, each entry is [main bone_id, secondary bone_id]
        # don't know why going through this trouble to store 2nd and third bone id.
        bs.seek( self.offsetMeshStart + self.offsetBonePair);
        for i in range(self.numBones2):
            self.bonePair.append([bs.readUShort(),bs.readUShort()])
        print ("bonepair table",self.bonePair)
        
        # build morph targets
        # Code based on Murugo's Misc-Game-Research github artifacts ,PS2 SH2/3 import_mod.py
        bs.seek(self.offsetMeshStart + self.morph_base_offs,NOESEEK_ABS)
        base_pos_int16 = []
        base_norm_int16 = []
        for i in range(self.morph_base_cnt):        
             base_pos_int16.append([bs.readShort(),bs.readShort(),bs.readShort()])             
             base_norm_int16.append([bs.readShort(),bs.readShort(),bs.readShort()])   

        bs.seek(self.offsetMeshStart + self.morph_data_offs,NOESEEK_ABS)
        morph_target_desc=[(bs.readUInt(),bs.readUInt()) for _ in range(self.morph_data_cnt)]        
        normList= []      
        for vcnt, offs in morph_target_desc:  
            print ("vcnt",vcnt,hex(offs))
            bs.seek(self.offsetMeshStart + offs,NOESEEK_ABS)
            pos_int16 = copy.deepcopy(base_pos_int16)
            norm_int16 = copy.deepcopy(base_norm_int16)

            for i in range(vcnt):
                a,b,c = (bs.readShort(),bs.readShort(),bs.readShort())
                d,e,f = (bs.readShort(),bs.readShort(),bs.readShort())
                delta_xyz = [a,b,c]
                delta_norm= [d,e,f]
                vidx = bs.readUShort()
                pos_int16[vidx][0]= base_pos_int16[vidx][0]+ delta_xyz[0]
                pos_int16[vidx][1]= base_pos_int16[vidx][1]+ delta_xyz[1]
                pos_int16[vidx][2]= base_pos_int16[vidx][2]+ delta_xyz[2]
                norm_int16[vidx][0]=base_norm_int16[vidx][0]+ delta_norm[0]
                norm_int16[vidx][1]=base_norm_int16[vidx][1]+ delta_norm[1]
                norm_int16[vidx][2]=base_norm_int16[vidx][2]+ delta_norm[2]  
 
            self.morph_targets.append((pos_int16,norm_int16))

        # main meshes           
        self.loadMeshes(bs,0,self.numMeshes,self.offsetMeshes)
        #
		# second meshes if exists
        self.loadMeshes(bs,1,self.numMeshes2,self.offsetMeshes2)
        
    def loadMeshes(self, bs, meshGroup, numMeshes, offsetMeshes):
        cur_pos = self.offsetMeshStart + offsetMeshes;        
        for i in range(numMeshes):        
            bs.seek(cur_pos, NOESEEK_ABS)
            mesh_size = bs.readUInt()
            unk =  bs.readUInt()
            header_size = bs.readUInt()
            unk = bs.readUInt()
            unk = bs.readUInt()
            morph_ref_cnt = bs.readUInt()
            morph_ref_offs = bs.readUInt()
            num_bones = bs.readUInt()
            bonemap_offset = bs.readUInt()
            
            num_bones2 = bs.readUInt()
            bonemap_offset2 = bs.readUInt()
            
            bs.seek(3*4,NOESEEK_REL)
            
            mat_id_offset = bs.readUInt()

            bs.seek(cur_pos + header_size , NOESEEK_ABS)
            vert_header_id = bs.readUInt()
            unk2 = bs.readUInt()
            face_header_offset = bs.readUInt()
            face_header_id = bs.readUInt()
            bs.seek(cur_pos + header_size + 0x24, NOESEEK_ABS)
            numFidx = bs.readUInt()
            num_vertex = bs.readUInt()
            vertex_offset = bs.readUInt()
            unk3 = bs.readUInt()
            fidx_offset = bs.readUInt()
            unk4 = bs.readUInt()
            bmID_Map_offset = bs.readUInt()

            if debug:
                print ("mesh ",meshGroup,i,hex(mesh_size),hex(header_size),num_bones,num_bones2,hex(num_vertex),hex(fidx_offset))
            bs.seek(cur_pos + bonemap_offset, NOESEEK_ABS)

            # construct bonemap            
            self.boneMap = []
            # mesh first bonemap, contains first bone b_id
            for b in range(num_bones):
                boneId = bs.readUShort()            
                self.boneMap.append(boneId)
            # mesh 2nd bonemap , contain bonepair index, use it to find bone pair and the real bond id
            bs.seek(cur_pos + bonemap_offset2, NOESEEK_ABS)    
            bonePairList =[]
            print ("bonemap",self.boneMap)

            for b in range(num_bones2):
                bonepair_idx = bs.readUShort()                
                # take the 2nd bone_id of the pair.
                bp = self.bonePair[bonepair_idx]
                bonePairList.append(bp)                
                self.boneMap.append(bp[1])
                

            # bone map index id to bone map index tranlation table
            bs.seek(cur_pos + header_size + face_header_offset + bmID_Map_offset , NOESEEK_ABS)         
            self.bmID_to_Idx = []
            for b in range(len(self.boneMap)):
                self.bmID_to_Idx.append(bs.readUInt())

            print ("bonePairList",bonePairList)
            print ("bonemap",self.boneMap)
            self.num_bones = num_bones
            self.num_bones2 = num_bones2

            rapi.rpgSetBoneMap(self.boneMap)
            
            bs.seek (cur_pos + mat_id_offset, NOESEEK_ABS)
            mat_id = bs.readUShort()
                        
            # set up material
            #self.setMaterial(mat_id)
            
            # advance to the vertex buffer
            bs.seek(cur_pos + header_size + vertex_offset, NOESEEK_ABS)
                        
            if debug:
                print("Mesh Info Start: " + str(bs.tell()))
                print("Bonemap ",i,self.boneMap)
            meshFile.buildMesh(self, [num_vertex, cur_pos + header_size + 0xc + fidx_offset, numFidx, meshGroup, morph_ref_cnt, cur_pos + morph_ref_offs], i, self.boneMap, self.offsetBones, self.offsetFaceIdx, self.numBones)
            if debug:
                print("Mesh Info End: " + str(bs.tell()))
            cur_pos = cur_pos + mesh_size
            
    def buildMesh(self, meshInfo, meshIndex, boneMap, uiOffsetBoneMap, uiOffsetFaceData, usNumBones):        
        bs = self.inFile        
        
        rapi.rpgSetName("Mesh_"+ str(meshInfo[3]) + "_" + str(meshIndex))
        rapi.rpgSetPosScaleBias((1.0,1.0,1.0), (0, 0, 0))
        
        print ("Mesh_"+ str(meshInfo[3]) + "_" + str(meshIndex))
        ucMeshVertStride = 0x40
        iMeshVertPos = 0
        iMeshNrmPos = 12
        iMeshBwPos = 48
        #iMeshBiPos = 32
        iMeshUV1Pos = 24
            
        cur_pos = bs.tell()
        vertBuff = bs.readBytes(meshInfo[0] *ucMeshVertStride)

        bs.seek( meshInfo[1], NOESEEK_ABS)
        faceBuff = bs.readBytes(meshInfo[2]*2)         
        
        # flip mesh along y-axis (vertial direction)
        rapi.rpgSetTransform(NoeMat43((NoeVec3((-1, 0, 0)), NoeVec3((0, -1, 0)), NoeVec3((0, 0, 1)), NoeVec3((0, 0, 0)))))     

        normList = []
        vertList = []
        bwList = []
        biList = []

        BidSet = set()
        BidSet2 = set()
        vertBoneChild = {} #  collect all bonemap index id
        for n in range(meshInfo[0]):
            vidx = ucMeshVertStride * n
            Bid1,Bid2,Bid3,Bid4 = struct.unpack('IIII',vertBuff[vidx+32:vidx+48])
            W = struct.unpack('ffff',vertBuff[vidx+48:vidx+64])
            BidSet.update([Bid1,Bid2,Bid3,Bid4])

        # sort bonemap index id, use them for lookup of bone id
        BidList = sorted(BidSet)              
            
        print ("Mesh",meshIndex,  '[{}]'.format(', '.join(hex(x) for x in BidList)))
        for n in range(meshInfo[0]):
            vidx = ucMeshVertStride * n
            x,y,z = struct.unpack('fff', vertBuff[vidx:vidx+12])
            nx,ny,nz = struct.unpack('fff', vertBuff[vidx+12:vidx+24])
            Bw1,Bw2,Bw3,Bw4 = struct.unpack('ffff',vertBuff[vidx+48:vidx+64])
            Bid1,Bid2,Bid3,Bid4 = struct.unpack('IIII',vertBuff[vidx+32:vidx+48])
            Bi1 = self.bmID_to_Idx[BidList.index(Bid1)]  # convert index id to index
            Bi2 = self.bmID_to_Idx[BidList.index(Bid2)]
            Bi3 = self.bmID_to_Idx[BidList.index(Bid3)]
            Bi4 = self.bmID_to_Idx[BidList.index(Bid4)]
            biList.append(Bi1)
            biList.append(Bi2)
            biList.append(Bi3)
            biList.append(Bi4)

            # need to moved vertex to initial postion by transformating to first bone location
            vert = NoeVec4((x,y,z,1))
            norm = NoeVec4((nx,ny,nz,0))
            bid = boneMap[Bi1]
            mat = self.boneMat[boneMap[Bi1]]


            # transform vertices and normals to their inital positions
            newv = mat * vert
            newn = mat * norm
            vertList.append(newv[0])
            vertList.append(newv[1])
            vertList.append(newv[2])
            
            normList.append(newn[0])
            normList.append(newn[1])
            normList.append(newn[2])
            
        vertB = struct.pack("<" + 'f'*len(vertList), *vertList)        
        rapi.rpgBindPositionBufferOfs(vertB, noesis.RPGEODATA_FLOAT, 0xc, 0x0)

        normBuff = struct.pack("<" + 'f'*len(normList), *normList)        
        rapi.rpgBindNormalBufferOfs(normBuff, noesis.RPGEODATA_FLOAT, 0xC, 0x0)
        
        biBuff = struct.pack("<" + 'H'*len(biList), *biList)  
        rapi.rpgBindBoneIndexBufferOfs(biBuff, noesis.RPGEODATA_USHORT, 8, 0, 0x4)                    
        rapi.rpgBindBoneWeightBufferOfs(vertBuff, noesis.RPGEODATA_FLOAT, ucMeshVertStride, iMeshBwPos, 0x4)
        
        rapi.rpgBindUV1BufferOfs(vertBuff, noesis.RPGEODATA_FLOAT, ucMeshVertStride, iMeshUV1Pos)
                 
        rapi.rpgCommitTriangles(faceBuff, noesis.RPGEODATA_USHORT, meshInfo[2], noesis.RPGEO_TRIANGLE_STRIP, 0x1)
              
        rapi.rpgClearBufferBinds()                                               

    def getTailPos(self, PID, bonePID,bonePos):
        hasChild = False
        childBone = None    
        childList = []
        for i,bone in enumerate(bonePID):
            if bonePID[i] == PID:
                childList.append(bonePos[i])
                hasChild = True
        if hasChild:
            temp = NoeVec3([0.0,0.0,0.0])
            for childPos in childList:
                temp += childPos
            temp /= len(childList)
        else:
            temp = NoeVec3(bonePos[PID])
        return temp
        
    class bone:
        def __init__(self, x, y, z):
            self.pos = NoeVec3([x,y,z])
            self.tail = NoeVec3(pos)
            self.direction = NoeVec3()
        
        
    def buildSkeleton(self):
        bs = self.inFile
        
        BonePID = []
        BonePos = []
        bone_mm = []
        if self.numBones > 0:
            bs.seek(self.offsetSkel + self.offsetMeshStart, NOESEEK_ABS)
            for i in range(self.numBones):
                pid = bs.readUShort()
                BonePID.append(pid)
               
            bs.seek(self.offsetBones + self.offsetMeshStart, NOESEEK_ABS)
            for i in range(self.numBones):           
                # read mesh initial matrix                
                mat = NoeMat44([[bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()]])
                self.boneMat.append(mat)
                BonePos.append([-mat[3][0],-mat[3][1],mat[3][2]])
                
            for i in range(self.numBones):
                            
                quat = NoeQuat([0, 0, 0, 1])
                bone_mat = quat.toMat43()  
                
                mat = self.boneMat[i]
                bone_mat[0]=[mat[0][0],mat[0][1],mat[0][2] ]
                bone_mat[1]=[mat[1][0],mat[1][1],mat[1][2] ]
                bone_mat[2]=[mat[2][0],mat[2][1],mat[2][2] ]
                bone_mat[3]=[-mat[3][0],-mat[3][1],mat[3][2] ]
                bone_mm.append(bone_mat)
                self.boneList.append(NoeBone(i, "bone%03i"%i, bone_mat, None, BonePID[i]))

        if self.numBones2 > 0:
            BonePair = []
            helperMat = []
            bs.seek( self.offsetMeshStart + self.offsetBonePair, NOESEEK_ABS);
            for i in range(self.numBones2):
                BonePair.append([bs.readUShort(),bs.readUShort()])         

            bs.seek(self.offsetBones2 + self.offsetMeshStart, NOESEEK_ABS)

            for i in range(self.numBones2):           
                # read mesh initial matrix                
                mat = NoeMat44([[bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()],
                    [bs.readFloat(),bs.readFloat(),bs.readFloat(),bs.readFloat()]])
                
                quat = NoeQuat([0, 0, 0, 1])
                bone_mat = quat.toMat43()                
                
                bone_mat[0]=[mat[0][0],mat[0][1],mat[0][2] ]
                bone_mat[1]=[mat[1][0],mat[1][1],mat[1][2] ]
                bone_mat[2]=[mat[2][0],mat[2][1],mat[2][2] ]
                bone_mat[3]=[mat[3][0],mat[3][1],mat[3][2] ]
                new_mat = mat * self.boneMat[BonePair[i][1]]

def meshLoadModel(data, mdlList):
    ctx = rapi.rpgCreateContext()
    mesh = meshFile(data)
    mesh.loadMesh()
    try:
        mdl = rapi.rpgConstructModel()
    except:
        mdl = NoeModel()
    if len(mesh.boneList):
        mdl.setBones(mesh.boneList)
    mdl.setModelMaterials(NoeModelMaterials(mesh.texList, mesh.matList))
    mdlList.append(mdl);
    return 1