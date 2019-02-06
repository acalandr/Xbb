import json
import os
import array
from JsonTable import JsonTable
from vLeptons import vLeptonSelector
from BranchTools import Collection
from BranchTools import AddCollectionsModule

class MuonSFfromJSON(AddCollectionsModule):

    def __init__(self, jsonFiles=None, branchName='muonSF',channel='None'):
        super(MuonSFfromJSON, self).__init__()
        self.jsonFiles = jsonFiles
        self.debug = 'XBBDEBUG' in os.environ
        self.branchName = branchName

        # load JOSN files
        self.jsonTable = JsonTable(jsonFiles)
        self.channel = channel 
        if self.channel== 'Zll':
            self.idSf = self.jsonTable.getEtaPtTable('NUM_LooseID_DEN_genTracks', 'abseta_pt')
            self.isoSf = self.jsonTable.getEtaPtTable('NUM_LooseRelIso_DEN_LooseID', 'abseta_pt')
            #self.triggerSf = ; not implemented yet
        elif self.channel == 'Wlv':
            self.idSf = self.jsonTable.getEtaPtTable('NUM_TightID_DEN_genTracks', 'abseta_pt')
            self.isoSf = self.jsonTable.getEtaPtTable('NUM_UltraTightIso4_DEN_TightIDandIPCut', 'abseta_pt')
            self.triggerSf = [self.jsonTable.getEtaPtTable('NUM_IsoMu27_DEN_empty', 'abseta_pt')]
        else: 
            print "Channel not defined!"
            raise Exception("ChannelNotDefined")
        self.systVariations = [None, 'Down', 'Up']

    def customInit(self, initVars):
        sample = initVars['sample']
        self.isData = sample.type == 'DATA'
        self.config = initVars['config']

        # prepare buffers for new branches to add
        self.branches = []
        self.branchBuffers = {}
        self.lastEntry = -1
        if not self.isData:
            for n in ['', '_Id', '_Iso', '_trigger']:
                self.addVectorBranch(self.branchName + n, default=1.0, length=3)

    def processEvent(self, tree):
        # if current entry has not been processed yet
        if not self.hasBeenProcessed(tree) and not self.isData:
            self.markProcessed(tree)

            #TODO check the assigned weights for events with more than 2 letpns
            Vtype = tree.Vtype
            vLidx = []
            lep_eta = []
            lep_pt = []
         
            if self.channel == "Wlv" and Vtype == 2:
               vLidx = [tree.vLidx[0]]
               lep_pt = [tree.Muon_pt[vLidx[0]]]
               lep_eta = [tree.Muon_eta[vLidx[0]]]
            elif self.channel == "Zll" and Vtype == 0:
               vLidx = [tree.vLidx[0],tree.vLidx[1]]
               lep_pt = [tree.Muon_pt[vLidx[0]], tree.Muon_pt[vLidx[1]]]
               lep_eta = [tree.Muon_eta[vLidx[0]], tree.Muon_eta[vLidx[1]]]

            self.computeSF(
                    weight_trigg=self._b(self.branchName + '_trigger'),
                    weight_Id=self._b(self.branchName + '_Id'),
                    weight_Iso=self._b(self.branchName + '_Iso'),
                    weight_SF=self._b(self.branchName),
                    lep_eta=lep_eta,
                    lep_pt=lep_pt,
                    lep_n=len(vLidx)
                    )

        return True

    def computeSF(self, weight_trigg, weight_Id, weight_Iso, weight_SF, lep_eta, lep_pt, lep_n):
        '''Computes the trigger, IdIso (including separated variations in eta) and final event SF'''
        # require two electrons

        if lep_n == 1 or lep_n == 2:

            #Calculating the trigger and IdIso weights and Down/Up variations
            for i, syst in enumerate(self.systVariations):
               weight_trigg[i] = self.getTriggerSf(lep_eta, lep_pt, lep_n, syst=syst)
               weight_Id[i] = self.getIdSf(lep_eta, lep_pt, lep_n)
               weight_Iso[i] = self.getIsoSf(lep_eta, lep_pt, lep_n)
               weight_SF[i] = weight_trigg[i] * weight_Id[i] * weight_Iso[i]

#               print "trigg", weight_trigg[i] 
#               print "Id", weight_Id[i]
#               print "Iso", weight_Iso[i]
#               print "SF", weight_SF[i]

        #This is when an event has 0 or more than 2 lepton
        else:
            for i, syst in enumerate(self.systVariations):
                weight_trigg[i] = 1.
                weight_Id[i] = 1.
                weight_Iso[i] = 1.
                weight_SF[i] = 1.

    def getIdSf(self, eta, pt, len_n, syst=None):
        idSF = 1.
        if self.idSf:
            for i in range(len_n):
                idSF = idSF * self.jsonTable.find(self.idSf, eta[i], pt[i], syst=syst)

        return idSF


    def getIsoSf(self, eta, pt, len_n, syst=None):
        isoSF = 1.
        for i in range(len_n):
            isoSF = isoSF * self.jsonTable.find(self.isoSf, eta=eta[i], pt=pt[i], syst=syst)

        return isoSF
          
  
#    def getTriggerSf(self, eta1, pt1, eta2, pt2, syst=None):
#        leg1 = 1.0 #not implemented yet
#        leg2 = 1.0 
#        #define efficiency for MC and 
#        effData_leg8 = []
#        effData_leg17= []
#        effMC_leg8= []
#        effMC_leg17 = []
#        #if self.debug:
#        #    print "leg1: eta:", eta1, " pt:", pt1, "->", leg1
#        #    print "leg2: eta:", eta2, " pt:", pt2, "->", leg2
#        #    print "-->", leg1*leg2
#        return leg1*leg2

    def getTriggerSf(self, eta, pt, len_n, syst=None):
        triggSF = 1.
        if self.channel == 'Zll' :
           trigSF = 1. #not implemented for Zll2017 (when ready, just remove the if/else block)
        else: 
           for i in range(len_n):
            triggSF = triggSF * self.jsonTable.find(self.triggerSf[i], eta[i], pt[i], syst=syst)
            #print "leg", i, " : eta:", eta[i], " pt:", pt[i], "->", self.jsonTable.find(self.triggerSf[i], eta[i], pt[i], syst=syst)

        return triggSF

if __name__ == "__main__":
    sfObject = MuonSFfromJSON([
            'weights/Zll/Muons/RunBCDEF_SF_ID.json',
            'weights/Zll/Muons/RunBCDEF_SF_ISO.json',
        ])
    print sfObject.getIdSf(0.5, 42)
    print sfObject.getIdSf(-0.5, 42)
    print sfObject.getIsoSf(1.5, 21)
    print sfObject.getIsoSf(-1.5, 21)
