#!/usr/bin/env python
from __future__ import print_function
import ROOT
import numpy as np
from Jet import Jet
from BranchTools import Collection
from BranchTools import AddCollectionsModule
from XbbConfig import XbbConfigTools

from JMEres import JMEres

# resolution functions from HH4b analysis
# https://github.com/cvernier/HH4b2016/blob/master/HbbHbb_Component_KinFit.cc
def ErrpT_Signal(pT, eta):
    if abs(eta)<1.4:
        pT = 40 if pT<40 else 550 if pT > 550 else pT
        sigmapT = 22.26 - 0.01*pT + 0.00018*pT*pT
    else:
        pT = 40 if pT<40 else 350 if pT > 350 else pT
        sigmapT = 17.11 + 0.058 * pT
    return sigmapT*sigmapT

def ErrEta_Signal(pT):
    pT = 40 if pT<40 else 500 if pT > 500 else pT
    sigmaEta = 0.033 + (4.1/pT) + (-0.17/pow(pT,0.5))
    return sigmaEta*sigmaEta

def ErrPhi_Signal(pT):
    pT = 40 if pT<40 else 500 if pT > 500 else pT
    sigmaPhi = 0.038 + (4.1/pT) + (-0.19/pow(pT,0.5))
    return sigmaPhi*sigmaPhi

def fourvector(pt, eta, phi, m, ind=-1):
    if ind == -1:
        v = ROOT.TLorentzVector()
        v.SetPtEtaPhiM(pt, eta, phi, m)
    else:
        v = ROOT.TLorentzVector()
        v.SetPtEtaPhiM(pt[ind], eta[ind], phi[ind], m[ind])
    return v

def fit_jet(v, resScale=1.0):
    cov = ROOT.TMatrixD(3, 3)
    cov.Zero()
    cov[0][0] = ErrpT_Signal(v.Et(), v.Eta()) * resScale**2
    cov[1][1] = ErrEta_Signal(v.Et())
    cov[2][2] = ErrPhi_Signal(v.Et())
    return ROOT.TFitParticleEtEtaPhi(v, cov)

def fit_lepton(v, ptErr):    
    cov = ROOT.TMatrixD(3, 3)
    cov.Zero()
    cov[0][0] = ptErr**2 
    cov[1][1] = 0.0001 # eta: too small
    cov[2][2] = 0.0001 # phi: too small
    return ROOT.TFitParticleEtEtaPhi(v, cov) 

# based on AnalysisTools code
# https://github.com/capalmer85/AnalysisTools/blob/master/python/kinfitter.py
class kinFitterXbb(AddCollectionsModule):

    def __init__(self, year, branchName="kinFit", useMZconstraint=True, recoilPtThreshold=20.0, jetIdCut=4, puIdCut=6, hJidx="hJidx"):
        super(kinFitterXbb, self).__init__()
        self.version = 4
        self.branchName = branchName
        self.useMZconstraint = useMZconstraint
        self.debug = False
        self.enabled = True
        self.year = year
        self.jetIdCut = jetIdCut
        self.puIdCut = puIdCut
        self.HH4B_RES_SCALE = 0.62
        self.LLVV_PXY_VAR = 8.0**2 
        self.Z_MASS = 91.0
        self.Z_WIDTH = 1.7*3
        self.recoilPtThreshold = recoilPtThreshold
        self.hJidx = hJidx
        self.systematics = None
        
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TAbsFitConstraint_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TAbsFitParticle_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitConstraintEp_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitConstraintMGaus_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitConstraintM_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitParticleCart_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitParticleECart_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitParticleEMomDev_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitParticleEScaledMomDev_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitParticleESpher_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitParticleEtEtaPhi_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitParticleEtThetaPhi_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitParticleMCCart_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitParticleMCMomDev_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitParticleMCPInvSpher_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitParticleMCSpher_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitParticleMomDev_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TFitParticleSpher_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TKinFitter_cc.so")
        ROOT.gSystem.Load("../HelperClasses/KinFitter/TSLToyGen_cc.so")

        self.jetResolution = JMEres(year=self.year)

    def customInit(self, initVars):
        self.sample = initVars['sample']
        self.config = initVars['config']
        self.xbbConfig  = XbbConfigTools(self.config)
        if self.systematics is None:
            if not self.sample.isData():
                jetSystematics= self.xbbConfig.getJECuncertainties(step='KinFit')
                self.systematics = [None] + [x+'_Up' for x in jetSystematics] + [x+'_Down' for x in jetSystematics] 
            else:
                self.systematics = [None]
        print("INFO: computing the fit for", len(self.systematics), " variations.")

        self.bDict = {}
        for syst in self.systematics:
            self.bDict[syst] = {}
            for n in ['H_mass_fit', 'H_eta_fit', 'H_phi_fit', 'H_pt_fit', 'HVdPhi_fit', 'jjVPtRatio_fit', 'hJets_pt_0_fit', 'hJets_pt_1_fit', 'V_pt_fit', 'V_eta_fit', 'V_phi_fit', 'V_mass_fit', 'H_mass_sigma_fit','H_pt_sigma_fit', 'hJets_pt_0_sigma_fit', 'hJets_pt_1_sigma_fit', 'H_pt_corr_fit', 'llbb_pt_fit', 'llbb_eta_fit', 'llbb_phi_fit', 'llbb_mass_fit', 'llbbr_pt_fit', 'llbbr_eta_fit', 'llbbr_phi_fit', 'llbbr_mass_fit', 'H_mass_fit_noJetMass']:
                branchNameFull = self.branchName + "_" + n + ('_' + syst if not self._isnominal(syst) else '')
                self.bDict[syst][n] = branchNameFull
                self.addBranch(branchNameFull)
            for n in ['n_recoil_jets_fit', 'status']:
                branchNameFull = self.branchName + "_" + n + ('_' + syst if not self._isnominal(syst) else '')
                self.bDict[syst][n] = branchNameFull
                self.addIntegerBranch(branchNameFull)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def cart_cov(self, v, rho):
        jme_res = self.jetResolution.eval(v.Eta(), rho, v.Pt()) * v.Pt()
        cos_phi = np.cos(v.Phi())
        sin_phi = np.sin(v.Phi())
        cov = ROOT.TMatrixD(4, 4)
        cov.Zero()
        cov[0][0] = (jme_res*cos_phi)**2
        cov[1][0] = jme_res**2 * cos_phi * sin_phi
        cov[0][1] = cov[1][0]
        cov[1][1] = (jme_res*sin_phi)**2
        return cov

    def getResolvedJetIndicesFromTree(self, tree, syst=None, UD=None):
        indexNameSyst = (self.hJidx + '_' + syst + UD) if not self._isnominal(syst) else self.hJidx
        if hasattr(tree, indexNameSyst):
            self.count('_debug_resolved_idx_syst_exists')
            return getattr(tree, indexNameSyst)
        else:
            print("\x1b[31mDOES NOT HAVE INDEX:", indexNameSyst,"\x1b[0m")
            self.count('_debug_resolved_idx_fallback_nom')
            self.count('_debug_resolved_idx_fallback_nom_for_'+str(syst))
            return getattr(tree, self.hJidx)

    def getInputSystFormatFromOutputSyst(self, syst):
        if syst.endswith('_Up'):
            return syst[:-3] + 'Up'
        elif syst.endswith('_Down'):
            return syst[:-5] + 'Down'
        return syst

    def processEvent(self, tree):
        if not self.hasBeenProcessed(tree) and self.enabled:
            self.markProcessed(tree)

            phi = tree.Jet_phi
            eta = tree.Jet_eta

            vLidx = tree.vLidx

            for syst in self.systematics:

                if not self._isnominal(syst):
                    if syst.endswith('Up'):
                        variation = 'Up'
                        systBase  = syst[:-2].strip('_')
                    elif syst.endswith('Down'):
                        variation = 'Down'
                        systBase  = syst[:-4].strip('_')
                    else:
                        variation = None
                        systBase  = syst
                else:
                    variation = None
                    systBase  = syst

                hJidx = self.getResolvedJetIndicesFromTree(tree, systBase, variation)

                if hJidx[0] > -1 and hJidx[1] > -1:
                    # systematic up/down variation
                    if not self._isnominal(syst):
                        # vary regression
                        if syst == 'jerReg_Up':
                            pt = tree.Jet_Pt
                            pt_reg = tree.Jet_PtRegUp
                            mass = tree.Jet_mass_nom
                        elif syst == 'jerReg_Down':
                            pt = tree.Jet_Pt
                            pt_reg = tree.Jet_PtRegDown
                            mass = tree.Jet_mass_nom
                        elif syst == 'jerRegScale_Down':
                            pt = tree.Jet_Pt
                            pt_reg = tree.Jet_PtRegScaleDown
                            mass = tree.Jet_mass_nom
                        elif syst == 'jerRegScale_Up':
                            pt = tree.Jet_Pt
                            pt_reg = tree.Jet_PtRegScaleUp
                            mass = tree.Jet_mass_nom
                        elif syst == 'jerRegSmear_Down':
                            pt = tree.Jet_Pt
                            pt_reg = tree.Jet_PtRegSmearDown
                            mass = tree.Jet_mass_nom
                        elif syst == 'jerRegSmear_Up':
                            pt = tree.Jet_Pt
                            pt_reg = tree.Jet_PtRegSmearUp
                            mass = tree.Jet_mass_nom
                        # vary JEC
                        else:
                            pt = getattr(tree, 'Jet_pt_' + self.getInputSystFormatFromOutputSyst(syst)) 
                            # propagate JEC to regressed pt
                            pt_reg = [tree.Jet_PtReg[i] * getattr(tree, 'Jet_pt_' + self.getInputSystFormatFromOutputSyst(syst))[i] / tree.Jet_Pt[i] for i in range(len(tree.Jet_PtReg))]
                            mass = getattr(tree, 'Jet_mass_' + self.getInputSystFormatFromOutputSyst(syst))

                    # nominal
                    else:
                        pt = tree.Jet_Pt
                        pt_reg = tree.Jet_PtReg
                        if self.sample.isMC():
                            mass = tree.Jet_mass_nom
                        else:
                            mass = tree.Jet_mass

                    # higgs jets
                    j1 = fourvector(pt_reg[hJidx[0]], eta[hJidx[0]], phi[hJidx[0]], mass[hJidx[0]] * tree.Jet_PtReg[hJidx[0]]/tree.Jet_Pt[hJidx[0]])
                    j2 = fourvector(pt_reg[hJidx[1]], eta[hJidx[1]], phi[hJidx[1]], mass[hJidx[1]] * tree.Jet_PtReg[hJidx[1]]/tree.Jet_Pt[hJidx[1]])

                    # FSR jets
                    fsrJets = []
                    fsrJidx = []
                    for i in range(tree.nJet):
                        if i not in hJidx and tree.Jet_lepFilter[i] > 0 and (tree.Jet_puId[i] > self.puIdCut or tree.Jet_Pt[i] > 50) and tree.Jet_jetId[i] > self.jetIdCut and pt[i] > 20 and abs(eta[i]) < 3.0:

                            j_fsr = fourvector(pt[i], eta[i], phi[i], mass[i])

                            delta_r1 = j_fsr.DeltaR(j1)
                            delta_r2 = j_fsr.DeltaR(j2)

                            if min(delta_r1, delta_r2) < 0.8:
                                fsrJets.append(j_fsr)
                                fsrJidx.append(i)
                                #if delta_r1 < delta_r2:
                                #    j1 += j_fsr
                                #else:
                                #    j2 += j_fsr

                    fit_j1 = fit_jet(j1, self.HH4B_RES_SCALE)
                    fit_j2 = fit_jet(j2, self.HH4B_RES_SCALE)

                    fit_jets = [fit_j1, fit_j2] + [fit_jet(fsrJet, self.HH4B_RES_SCALE) for fsrJet in fsrJets]

                    # recoil jets
                    recoil_jets = []
                    for i in range(tree.nJet):
                        if i not in hJidx and i not in fsrJidx and (tree.Jet_puId[i] > self.puIdCut or tree.Jet_Pt[i] > 50) and tree.Jet_jetId[i] > self.jetIdCut and tree.Jet_lepFilter[i] > 0 and pt[i] > self.recoilPtThreshold:
                            recoil_jets.append(fourvector(pt[i], eta[i], phi[i], mass[i]))
                    recoil_sum = sum(recoil_jets, ROOT.TLorentzVector())

                    cov_recoil = ROOT.TMatrixD(4, 4)
                    cov_recoil.Zero()
                    cov_recoil[0][0] = self.LLVV_PXY_VAR
                    cov_recoil[1][1] = self.LLVV_PXY_VAR
                    cov_recoil[2][2] = 1
                    cov_recoil[3][3] = 1e12

                    for j in recoil_jets:
                        cov_recoil += self.cart_cov(j, tree.fixedGridRhoFastjetAll)
                    fit_recoil = ROOT.TFitParticleECart(recoil_sum, cov_recoil)

                    #leptons
                    if tree.Vtype == 0:
                        fit_l1 = fit_lepton(fourvector(abs(tree.Muon_corrected_pt[vLidx[0]]), tree.Muon_eta[vLidx[0]], tree.Muon_phi[vLidx[0]], tree.Muon_mass[vLidx[0]]), tree.Muon_ptErr[vLidx[0]])
                        fit_l2 = fit_lepton(fourvector(abs(tree.Muon_corrected_pt[vLidx[1]]), tree.Muon_eta[vLidx[1]], tree.Muon_phi[vLidx[1]], tree.Muon_mass[vLidx[1]]), tree.Muon_ptErr[vLidx[1]])
                    else:
                        fit_l1 = fit_lepton(fourvector(abs(tree.Electron_pt[vLidx[0]]), tree.Electron_eta[vLidx[0]], tree.Electron_phi[vLidx[0]], tree.Electron_mass[vLidx[0]]), tree.Electron_energyErr[vLidx[0]])
                        fit_l2 = fit_lepton(fourvector(abs(tree.Electron_pt[vLidx[1]]), tree.Electron_eta[vLidx[1]], tree.Electron_phi[vLidx[1]], tree.Electron_mass[vLidx[1]]), tree.Electron_energyErr[vLidx[1]])

                    # constraints
                    cons_MZ = ROOT.TFitConstraintMGaus('cons_MZ', '', None, None, self.Z_MASS, self.Z_WIDTH)
                    cons_MZ.addParticle1(fit_l1)
                    cons_MZ.addParticle1(fit_l2)

                    # fit particles
                    #fit_particles = fit_jets + [fit_l1, fit_l2] + [fit_recoil]

                    cons_x = ROOT.TFitConstraintEp('cons_x', '', ROOT.TFitConstraintEp.pX)
                    cons_x.addParticles(*fit_jets)
                    cons_x.addParticles(fit_l1, fit_l2)
                    cons_x.addParticles(fit_recoil)

                    cons_y = ROOT.TFitConstraintEp('cons_y', '', ROOT.TFitConstraintEp.pY)
                    cons_y.addParticles(*fit_jets)
                    cons_y.addParticles(fit_l1, fit_l2)
                    cons_y.addParticles(fit_recoil)

                    # setup fitter
                    fitter = ROOT.TKinFitter()
                    fitter.addMeasParticles(*fit_jets)
                    fitter.addMeasParticles(fit_l1, fit_l2)
                    fitter.addMeasParticles(fit_recoil)

                    if self.useMZconstraint:
                        fitter.addConstraint(cons_MZ)
                    fitter.addConstraint(cons_x)
                    fitter.addConstraint(cons_y)

                    fitter.setMaxNbIter(30)
                    fitter.setMaxDeltaS(1e-2)
                    fitter.setMaxF(1e-1)
                    fitter.setVerbosity(0)

                    # run the fit
                    kinfit_fit = fitter.fit() + 1  # 0: not run; 1: fit converged; 2: fit didn't converge
                    kinfit_getNDF = fitter.getNDF()
                    kinfit_getS = fitter.getS()
                    kinfit_getF = fitter.getF()
                    #print("-"*10, kinfit_fit, kinfit_getNDF, kinfit_getS, kinfit_getF)
                    
                    # higgs jet output vectors
                    fit_result_j1 = fitter.get4Vec(0)
                    fit_result_j2 = fitter.get4Vec(1)
                    fit_result_H_noJetMass = fit_result_j1 + fit_result_j2
                    for iFsr in range(len(fit_jets)-2):
                        fit_result_H_noJetMass += fitter.get4Vec(2+iFsr)

                    # add back jet masses
                    fit_result_j1.SetPtEtaPhiM(fit_result_j1.Pt(),fit_result_j1.Eta(),fit_result_j1.Phi(), mass[hJidx[0]] * tree.Jet_PtReg[hJidx[0]]/tree.Jet_Pt[hJidx[0]])
                    fit_result_j2.SetPtEtaPhiM(fit_result_j2.Pt(),fit_result_j2.Eta(),fit_result_j2.Phi(), mass[hJidx[1]] * tree.Jet_PtReg[hJidx[1]]/tree.Jet_Pt[hJidx[1]])
                    fit_result_H = fit_result_j1 + fit_result_j2
                    for iFsr in range(len(fit_jets)-2):
                        j_fsr = fitter.get4Vec(2+iFsr)
                        j_fsr.SetPtEtaPhiM(j_fsr.Pt(),j_fsr.Eta(),j_fsr.Phi(), mass[fsrJidx[iFsr]])
                        fit_result_H += j_fsr

                    nFitJets = len(fit_jets)
                    fit_result_l1 = fitter.get4Vec(nFitJets)
                    fit_result_l2 = fitter.get4Vec(nFitJets+1)
                    fit_result_V = fit_result_l1 + fit_result_l2

                    # H + V (+ recoil)
                    llbb  = fit_result_H + fit_result_V
                    llbbr = llbb + fitter.get4Vec(nFitJets+2)

                    self._b(self.bDict[syst]['status'])[0] = kinfit_fit

                    if kinfit_fit == 1 and fit_result_H.M() > 0:
                        self.count("kinfit_success")
                        self._b(self.bDict[syst]['H_pt_fit'])[0]          = fit_result_H.Pt()
                        self._b(self.bDict[syst]['H_eta_fit'])[0]         = fit_result_H.Eta()
                        self._b(self.bDict[syst]['H_phi_fit'])[0]         = fit_result_H.Phi()
                        self._b(self.bDict[syst]['H_mass_fit'])[0]        = fit_result_H.M()
                        self._b(self.bDict[syst]['H_mass_fit_noJetMass'])[0] = fit_result_H_noJetMass.M()
                        self._b(self.bDict[syst]['V_pt_fit'])[0]          = fit_result_V.Pt()
                        self._b(self.bDict[syst]['V_eta_fit'])[0]         = fit_result_V.Eta()
                        self._b(self.bDict[syst]['V_phi_fit'])[0]         = fit_result_V.Phi()
                        self._b(self.bDict[syst]['V_mass_fit'])[0]        = fit_result_V.M()

                        self._b(self.bDict[syst]['HVdPhi_fit'])[0]        = abs(ROOT.TVector2.Phi_mpi_pi(fit_result_H.Phi() - fit_result_V.Phi()))
                        self._b(self.bDict[syst]['jjVPtRatio_fit'])[0]    = fit_result_H.Pt()/fit_result_V.Pt()
                        self._b(self.bDict[syst]['hJets_pt_0_fit'])[0]    = fit_result_j1.Pt()
                        self._b(self.bDict[syst]['hJets_pt_1_fit'])[0]    = fit_result_j2.Pt()

                        self._b(self.bDict[syst]['n_recoil_jets_fit'])[0] = len(recoil_jets)
                        
                        # higgs mass uncertainty
                        cov_fit = fitter.getCovMatrixFit()
                        dmH_by_dpt1 = ( (fit_result_H.X())*np.cos(fit_result_j1.Phi()) + (fit_result_H.Y())*np.sin(fit_result_j1.Phi()) )/fit_result_H.M()
                        dmH_by_dpt2 = ( (fit_result_H.X())*np.cos(fit_result_j2.Phi()) + (fit_result_H.Y())*np.sin(fit_result_j2.Phi()) )/fit_result_H.M()
                        self._b(self.bDict[syst]['H_mass_sigma_fit'])[0] = ( dmH_by_dpt1**2          * cov_fit(0,0)
                                                + dmH_by_dpt2**2          * cov_fit(3,3)
                                                + dmH_by_dpt1*dmH_by_dpt2 * cov_fit(0,3) )**.5

                        # Higgs pT uncertainty
                        self._b(self.bDict[syst]['hJets_pt_0_sigma_fit'])[0] = cov_fit(0,0)**0.5
                        self._b(self.bDict[syst]['hJets_pt_1_sigma_fit'])[0] = cov_fit(3,3)**0.5
                        self._b(self.bDict[syst]['H_pt_corr_fit'])[0]        = cov_fit(0,3) / ( (cov_fit(0,0)*cov_fit(3,3))**0.5 )
                        self._b(self.bDict[syst]['H_pt_sigma_fit'])[0]       = (cov_fit(0,0) + cov_fit(3,3) + 2.0*cov_fit(0,3) )**0.5

                        self._b(self.bDict[syst]['llbb_pt_fit'])[0]          = llbb.Pt()
                        self._b(self.bDict[syst]['llbb_phi_fit'])[0]         = llbb.Phi()
                        self._b(self.bDict[syst]['llbb_eta_fit'])[0]         = llbb.Eta()
                        self._b(self.bDict[syst]['llbb_mass_fit'])[0]        = llbb.M()
                        self._b(self.bDict[syst]['llbbr_pt_fit'])[0]          = llbbr.Pt()
                        self._b(self.bDict[syst]['llbbr_phi_fit'])[0]         = llbbr.Phi()
                        self._b(self.bDict[syst]['llbbr_eta_fit'])[0]         = llbbr.Eta()
                        self._b(self.bDict[syst]['llbbr_mass_fit'])[0]        = llbbr.M()
                    else:
                        if fit_result_H.M() <= 0:
                            self.count("kinfit_failure_mass_negative")
                        else:
                            self.count("kinfit_failure_convergence")

                        # fallback
                        self._b(self.bDict[syst]['H_pt_fit'])[0]          = tree.H_pt
                        self._b(self.bDict[syst]['H_eta_fit'])[0]         = tree.H_eta
                        self._b(self.bDict[syst]['H_phi_fit'])[0]         = tree.H_phi
                        self._b(self.bDict[syst]['H_mass_fit'])[0]        = tree.H_mass
                        self._b(self.bDict[syst]['H_mass_fit_noJetMass'])[0] = tree.H_mass
                        self._b(self.bDict[syst]['V_pt_fit'])[0]          = tree.V_pt
                        self._b(self.bDict[syst]['V_eta_fit'])[0]         = tree.V_eta
                        self._b(self.bDict[syst]['V_phi_fit'])[0]         = tree.V_phi
                        self._b(self.bDict[syst]['V_mass_fit'])[0]        = tree.V_mass
                        self._b(self.bDict[syst]['HVdPhi_fit'])[0]        = abs(ROOT.TVector2.Phi_mpi_pi(tree.H_phi - tree.V_phi))
                        self._b(self.bDict[syst]['jjVPtRatio_fit'])[0]    = tree.H_pt/tree.V_pt
                        self._b(self.bDict[syst]['hJets_pt_0_fit'])[0]    = pt_reg[hJidx[0]] 
                        self._b(self.bDict[syst]['hJets_pt_1_fit'])[0]    = pt_reg[hJidx[1]]

                        self._b(self.bDict[syst]['n_recoil_jets_fit'])[0] = -1 
                        self._b(self.bDict[syst]['H_mass_sigma_fit'])[0]  = -1

                        self._b(self.bDict[syst]['hJets_pt_0_sigma_fit'])[0] = -1
                        self._b(self.bDict[syst]['hJets_pt_1_sigma_fit'])[0] = -1
                        self._b(self.bDict[syst]['H_pt_corr_fit'])[0]        = -1
                        self._b(self.bDict[syst]['H_pt_sigma_fit'])[0]       = -1

                        self._b(self.bDict[syst]['llbb_pt_fit'])[0]          = -99
                        self._b(self.bDict[syst]['llbb_phi_fit'])[0]         = -99
                        self._b(self.bDict[syst]['llbb_eta_fit'])[0]         = -99
                        self._b(self.bDict[syst]['llbb_mass_fit'])[0]        = -99
                        self._b(self.bDict[syst]['llbbr_pt_fit'])[0]          = -99
                        self._b(self.bDict[syst]['llbbr_phi_fit'])[0]         = -99
                        self._b(self.bDict[syst]['llbbr_eta_fit'])[0]         = -99 
                        self._b(self.bDict[syst]['llbbr_mass_fit'])[0]        = -99

                else:
                    # no two resolved jets
                    self._b(self.bDict[syst]['H_pt_fit'])[0]          = -1 
                    self._b(self.bDict[syst]['H_eta_fit'])[0]         = -1 
                    self._b(self.bDict[syst]['H_phi_fit'])[0]         = -1 
                    self._b(self.bDict[syst]['H_mass_fit'])[0]        = -1 
                    self._b(self.bDict[syst]['H_mass_fit_noJetMass'])[0] = -1 
                    self._b(self.bDict[syst]['V_pt_fit'])[0]          = -1 
                    self._b(self.bDict[syst]['V_eta_fit'])[0]         = -1 
                    self._b(self.bDict[syst]['V_phi_fit'])[0]         = -1 
                    self._b(self.bDict[syst]['V_mass_fit'])[0]        = -1 
                    self._b(self.bDict[syst]['HVdPhi_fit'])[0]        = -1 
                    self._b(self.bDict[syst]['jjVPtRatio_fit'])[0]    = -1 
                    self._b(self.bDict[syst]['hJets_pt_0_fit'])[0]    = -1 
                    self._b(self.bDict[syst]['hJets_pt_1_fit'])[0]    = -1 

                    self._b(self.bDict[syst]['n_recoil_jets_fit'])[0] = -1 
                    self._b(self.bDict[syst]['H_mass_sigma_fit'])[0]  = -1

                    self._b(self.bDict[syst]['hJets_pt_0_sigma_fit'])[0] = -1
                    self._b(self.bDict[syst]['hJets_pt_1_sigma_fit'])[0] = -1
                    self._b(self.bDict[syst]['H_pt_corr_fit'])[0]        = -1
                    self._b(self.bDict[syst]['H_pt_sigma_fit'])[0]       = -1

                    self._b(self.bDict[syst]['llbb_pt_fit'])[0]          = -99
                    self._b(self.bDict[syst]['llbb_phi_fit'])[0]         = -99
                    self._b(self.bDict[syst]['llbb_eta_fit'])[0]         = -99
                    self._b(self.bDict[syst]['llbb_mass_fit'])[0]        = -99
                    self._b(self.bDict[syst]['llbbr_pt_fit'])[0]          = -99
                    self._b(self.bDict[syst]['llbbr_phi_fit'])[0]         = -99
                    self._b(self.bDict[syst]['llbbr_eta_fit'])[0]         = -99 
                    self._b(self.bDict[syst]['llbbr_mass_fit'])[0]        = -99
