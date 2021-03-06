#include "TString.h"
#include "TBranch.h"
#include "TTree.h"
#include "TFile.h"
#include "TH1D.h"
#include "TH2D.h"
#include "TLorentzVector.h"
#include "TCanvas.h"
#include "TGraph2D.h"
#include "TStyle.h"
#include "TROOT.h"

#include "tdrstyle.C"

#include <iostream>
#include <vector>

//_*_*_*
//Macros
//_*_*_*

// prepare histogram with axis labels and style
void preparehisto(TH2D* histo, TString title, TString xtitle, TString ytitle){
      histo->SetTitle(title);
      histo->GetXaxis()->SetTitle(xtitle);
      histo->GetXaxis()->SetLabelSize(20);
      histo->GetXaxis()->SetLabelFont(43);
      histo->GetXaxis()->SetTitleFont(63);
      histo->GetXaxis()->SetTitleSize(20);
      histo->GetYaxis()->SetTitle(ytitle);
      histo->GetYaxis()->SetLabelSize(20);
      histo->GetYaxis()->SetLabelFont(43);
      histo->GetYaxis()->SetTitleFont(63);
      histo->GetYaxis()->SetTitleSize(20);
}

//Create a TLorentzVector of the jets other than the two Higgs candidate b-jets. 
vector<TLorentzVector> OtherJets(Float_t Jet_pt[15], Float_t Jet_eta[15], Float_t Jet_phi[15], Float_t Jet_mass[15], Int_t Jet_puId[15], Int_t Jet_id[15], Int_t aJCidx[8], Int_t hJCidx[2]){
  vector<TLorentzVector> OtherJets;
  for(int i = 0; i < 15; ++i){
    TLorentzVector Ojet;
    if(
      Jet_pt[i]>30 && abs(Jet_eta[i])<4.5 && Jet_puId[i]>0 && Jet_id[i]>0 // quality cuts
      && aJCidx[i] != (hJCidx[0]) && (aJCidx[i] != (hJCidx[1])) // not an higgs b-jet
      ){ 
      // cout << " i= " << i << " Jet_pt= " << Jet_pt[i] << ";";
      Ojet.SetPtEtaPhiM( Jet_pt[i], Jet_eta[i], Jet_phi[i], Jet_mass[i]);
    }
    OtherJets.push_back(Ojet);
  }
  return OtherJets;
}

//Create a TLorentzVector of containing all the Higgs sisters
vector<TLorentzVector> Sis(Float_t Sis_pt[3], Float_t Sis_eta[3], Float_t Sis_phi[3], Float_t Sis_mass[3], Int_t Sis_pdgId[3]){
  vector<TLorentzVector> SIS;
  for(int i = 0; i < 3; ++i){
    if(Sis_pdgId[i]==23 || Sis_pdgId[i]==24) continue;
    // cout << " i= " << i << " Sis_pdgId= " << Sis_pdgId[i] << " Sis_pt= " << Sis_pt[i] << ";";
    TLorentzVector Sis;
    Sis.SetPtEtaPhiM( Sis_pt[i], Sis_eta[i], Sis_phi[i], Sis_mass[i]);
    SIS.push_back(Sis);
  }
  return SIS;
}

double ISRj_Idx(TLorentzVector V, TLorentzVector H, TLorentzVector VH, vector<TLorentzVector> O_Jets, double PhiCut, double VHPtCut, bool keep = true){
  //_*_*_*_*_*_*_*_*
  //Find the ISR jet 
  //_*_*_*_*_*_*_*_*
  TLorentzVector VHj;

  //Apply VHPt Cut
  if(VH.Pt() < VHPtCut){
    return -1;
  }
  double maxpt = 0;
  int ISRidx = -1;
  //Apply phi cut and keep ISR candiate only. Choose the ISR candidate having the higest Pt
  for(unsigned int i = 0; i < O_Jets.size(); ++i){
    if(abs(O_Jets[i].DeltaPhi(VH)) < TMath::Pi() - PhiCut) continue;
    if(O_Jets[i].Pt() < maxpt) continue;
    maxpt = O_Jets[i].Pt();
    ISRidx = i;
  }
  return ISRidx;
}

double HSisIerISR_Idx(TLorentzVector V, TLorentzVector H, TLorentzVector VH, int ISRidx, TLorentzVector ISRjet, vector<TLorentzVector> Sis, double PhiCut, double VHPtCut){
  //_*_*_*_*_*_*_*_*
  //Find the ISR jet 
  //_*_*_*_*_*_*_*_*
  //Returns the efficiency for a ISR-tagged jet to be matched to a syster jet
  //Apply VHPt Cut
  
  if(ISRidx == -1) return -1;
  
  if(VH.Pt() < VHPtCut) return -1;

  //Passes VHPt cut
  double idx = -1;
  double dR = 1e6;
  for(unsigned int i = 0; i < Sis.size(); ++i){
    //if(Sis[i].Pt() == 0 && Sis[i].Eta() == 0 && Sis[i].Phi() == 0) continue;
    if(Sis[i].DeltaR(ISRjet) < dR){
      dR = Sis[i].DeltaR(ISRjet);
      idx = i;
    }
  }

  return idx;

}

//_*_*
//Main
//_*_*

void VHF_Pt(int sample=0){

  //setTDRStyle();
  //gStyle->SetPaintTextFormat("4.2f");
  //gStyle->SetOptStat(0);

  TString _f_in="dcap://t3se01.psi.ch:22125//pnfs/psi.ch/cms/trivcat/store/t3groups/ethz-higgs/run2/V12/", _sample;

  //_*_*_*_*_*
  //Read Input
  //_*_*_*_*_*

  if(sample==0){
    //ZHbb powheg
    _f_in +="VHBB_HEPPY_V12_ZH_HToBB_ZToLL_M125_13TeV_powheg_pythia8__RunIISpring15DR74-Asympt25ns_MCRUN2_74_V9-v1.root";
    _sample = "ZH_HToBB_powheg_pythia";
  } else if(sample==0){
    //ZHbb amc@nlo
    _f_in +="VHBB_HEPPY_V12_ZH_HToBB_ZToLL_M125_13TeV_amcatnloFXFX_madspin_pythia8__RunIISpring15DR74-Asympt25ns_MCRUN2_74_V9-v1.root";
    _sample = "ZH_HToBB_amcanlo_pythia";
  } else if(sample==0){
    //ggZH powheg
    _f_in +="VHBB_HEPPY_V12_ggZH_HToBB_ZToLL_M125_13TeV_powheg_pythia8__RunIISpring15DR74-Asympt25ns_MCRUN2_74_V9-v1.root";
    _sample = "ggZH_powheg_pythia";
  } else if(sample==0){
    // ttH amc@nlo
    _f_in +="VHBB_HEPPY_V12_TTJets_TuneCUETP8M1_13TeV-amcatnloFXFX-pythia8__RunIISpring15DR74-Asympt25ns_MCRUN2_74_V9-v1.root";
    _sample = "ttjets_amcanlo_pythia";
  } else if(sample==0){
    //ttH powheg
    _f_in +="VHBB_HEPPY_V12_TTJets_TuneCUETP8M1_13TeV-madgraphMLM-pythia8__RunIISpring15DR74-Asympt25ns_MCRUN2_74_V9-v2.root";
    _sample = "ttjets_madgraph_pythia";
  }

  TString _f_out ="";
  TFile* f = TFile::Open(_f_in);
  TTree* t = (TTree*) f->Get("tree");

  //_*_*_*_*_*_*_*_*_*
  //ISR-tag Parameters
  //_*_*_*_*_*_*_*_*_*

  double _PhiCut[16] = { 0.2, 0.4, 0.6, 0.8, 1, 1.2, 1.4, 1.6, 1.8, 2., 2.2, 2.4, 2.6, 2.8, 3., 3.2};
  double _VHPtCut[9] = {10, 20, 30, 40, 50, 60, 80, 90, 100};
  bool keep = true;

  vector<double> PhiCut(_PhiCut, _PhiCut+16);
  vector<double> VHPtCut(_VHPtCut, _VHPtCut+9);
  vector<vector<TH1D*> > hist_VHj_pt,hist_Sister_pt,hist_Sister_eta,hist_ISRjall_pt,hist_ISRjall_eta,hist_ISRjmatched_pt,hist_ISRjmatched_eta;
  vector<vector<TCanvas*> > c_VHj_pt,c_ISR_sister_pt,c_ISR_sister_eta;
  TCanvas* cVHj = new TCanvas("cVHj","cVHj");
  TCanvas* cpur = new TCanvas("cpur","cpur");
  TCanvas* ceff = new TCanvas("ceff","ceff");
  TCanvas* ceffxpur = new TCanvas("ceffxpur","ceffxpur");

  vector<vector<double> > VHj;//VHj_Pt. To be computed in each event
  vector<vector<TH1D*> > hVHj1D;
  vector<vector<double> > pur;//Sister-ISR efficiency. To be computed at each event
  vector<vector<Int_t> > nbinentries;//#entries per PhixPt bins
  vector<vector<Int_t> > nisrtag;//#ISR jets found per PhixPt bins
  vector<vector<Int_t> > noISR;//count the # of times no ISR has been found

  TH2D* hVHj = new TH2D("hVHj", "h_VHj", 15, _PhiCut, 8, _VHPtCut);
  TH2D* hpur = new TH2D("hpur", "hpur",  15, _PhiCut, 8, _VHPtCut);
  TH2D* heff = new TH2D("heff", "heff",  15, _PhiCut, 8, _VHPtCut);
  TH2D* heffxpur = new TH2D("heffxpur", "heffxpur",  15, _PhiCut, 8, _VHPtCut);

  //Simple h_VH histogram without the ISR jet 
  TH1D* h_VH = new TH1D("h_VH","h_VH",200,0,200);

  //_*_*_*_*_*_*_*_*_*_*_*_*_*
  //Prepar all the histograms
  //_*_*_*_*_*_*_*_*_*_*_*_*_*

  for(unsigned int i = 0; i < PhiCut.size(); ++i){

    vector<TH1D*>  _hist_VHj_pt;
    vector<TCanvas*>  _c_VHj_pt,_c_ISR_sister_pt,_c_ISR_sister_eta;
    vector<double> _VHj;
    vector<TH1D*>  _histVHj1D,_hist_Sister_pt,_hist_Sister_eta,_hist_ISRjall_pt,_hist_ISRjall_eta,_hist_ISRjmatched_pt,_hist_ISRjmatched_eta;
    vector<double> _pur;
    vector<Int_t> _nbinentries;
    vector<Int_t> _nisrtag;
    vector<Int_t> _noISR;

    for(unsigned int k = 0; k < VHPtCut.size(); ++k){

      TH1D* _hist_VHj_pt_temp = new TH1D(Form("h_phi%i_Pt%i",i,k),Form("h_phi%i_Pt%i",i,k),200, 0, 200);
      _hist_VHj_pt.push_back(_hist_VHj_pt_temp);
      TH1D* hVHj1D_temp = new TH1D(Form("hVHj1D_phi%i_Pt%i",i,k),Form("h_phi%i_Pt%i",i,k),200, 0, 200);
      _histVHj1D.push_back(hVHj1D_temp);
      TH1D* _hist_Sister_pt_temp = new TH1D(Form("hist_Sister_pt_phi%i_Pt%i",i,k),Form("hist_Sister_pt_phi%i_Pt%i",i,k),200, 0, 200);
      _hist_Sister_pt.push_back(_hist_Sister_pt_temp);
      TH1D* _hist_Sister_eta_temp = new TH1D(Form("hist_Sister_eta_phi%i_Pt%i",i,k),Form("hist_Sister_eta_phi%i_Pt%i",i,k),50, -5, 5);
      _hist_Sister_eta.push_back(_hist_Sister_eta_temp);
      TH1D* _hist_ISRjall_pt_temp = new TH1D(Form("hist_ISRjall_pt_phi%i_Pt%i",i,k),Form("hist_ISRjall_pt_phi%i_Pt%i",i,k),200, 0, 200);
      _hist_ISRjall_pt.push_back(_hist_ISRjall_pt_temp);
      TH1D* _hist_ISRjall_eta_temp = new TH1D(Form("hist_ISRjall_eta_phi%i_Pt%i",i,k),Form("hist_ISRjall_eta_phi%i_Pt%i",i,k),50, -5, 5);
      _hist_ISRjall_eta.push_back(_hist_ISRjall_eta_temp);
      TH1D* _hist_ISRjmatched_pt_temp = new TH1D(Form("hist_ISRjmatched_pt_phi%i_Pt%i",i,k),Form("hist_ISRjmatched_pt_phi%i_Pt%i",i,k),200, 0, 200);
      _hist_ISRjmatched_pt.push_back(_hist_ISRjmatched_pt_temp);
      TH1D* _hist_ISRjmatched_eta_temp = new TH1D(Form("hist_ISRjmatched_eta_phi%i_Pt%i",i,k),Form("hist_ISRjmatched_eta_phi%i_Pt%i",i,k),50, -5, 5);
      _hist_ISRjmatched_eta.push_back(_hist_ISRjmatched_eta_temp);
      
      TCanvas* _c_VHj_pt_temp = new TCanvas(Form("c_phi%i_Pt%i",i,k),Form("c_phi%i_Pt%i",i,k));
      _c_VHj_pt.push_back(_c_VHj_pt_temp);
      TCanvas* _c_ISR_sister_pt_temp = new TCanvas(Form("c_ISR_sister_pt_phi%i_Pt%i",i,k),Form("c_ISR_sister_pt_phi%i_Pt%i",i,k));
      _c_ISR_sister_pt.push_back(_c_ISR_sister_pt_temp);
      TCanvas* _c_ISR_sister_eta_temp = new TCanvas(Form("c_ISR_sister_eta_phi%i_Pt%i",i,k),Form("c_ISR_sister_eta_phi%i_Pt%i",i,k));
      _c_ISR_sister_eta.push_back(_c_ISR_sister_eta_temp);

      _VHj.push_back(0);
      _pur.push_back(0);
      _nbinentries.push_back(0);
      _nisrtag.push_back(0);
      _noISR.push_back(0);
    }		

    hist_VHj_pt.push_back(_hist_VHj_pt);
    hist_Sister_pt.push_back(_hist_Sister_pt);
    hist_Sister_eta.push_back(_hist_Sister_eta);
    hist_ISRjall_pt.push_back(_hist_ISRjall_pt);
    hist_ISRjall_eta.push_back(_hist_ISRjall_eta);
    hist_ISRjmatched_pt.push_back(_hist_ISRjmatched_pt);
    hist_ISRjmatched_eta.push_back(_hist_ISRjmatched_eta);
    c_VHj_pt.push_back(_c_VHj_pt);
    c_ISR_sister_pt.push_back(_c_ISR_sister_pt);
    c_ISR_sister_eta.push_back(_c_ISR_sister_eta);
    VHj.push_back(_VHj);
    pur.push_back(_pur);
    nbinentries.push_back(_nbinentries);
    nisrtag.push_back(_nisrtag);
    noISR.push_back(_noISR);

  }

  //_*_*_*_*_*_*_*_*_*_*
  //Get Branch Variables
  //_*_*_*_*_*_*_*_*_*_*

  Float_t Jet_pt[15];
  Float_t Jet_eta[15];
  Float_t Jet_phi[15];
  Float_t Jet_mass[15];
  Int_t Jet_puId[15];
  Int_t Jet_id[15];
  Int_t Jet_aJCidx[8];
  Int_t Jet_hJCidx[2];
  Float_t V_pt;
  Float_t V_eta;
  Float_t V_phi;
  Float_t V_mass;
  Float_t H_pt;
  Float_t H_eta;
  Float_t H_phi;
  Float_t H_mass;
  Float_t Sis_pt[3];
  Float_t Sis_eta[3];
  Float_t Sis_phi[3];
  Float_t Sis_mass[3];
  Int_t Sis_pdgId[3];
  Float_t weight;
  Float_t Vtype;

  t->SetBranchAddress("Jet_pt", &Jet_pt);
  t->SetBranchAddress("Jet_eta", &Jet_eta);
  t->SetBranchAddress("Jet_phi", &Jet_phi);
  t->SetBranchAddress("Jet_mass", &Jet_mass);
  t->SetBranchAddress("Jet_puId", &Jet_puId);
  t->SetBranchAddress("Jet_id", &Jet_id);
  t->SetBranchAddress("aJCidx", &Jet_aJCidx);
  t->SetBranchAddress("hJCidx", &Jet_hJCidx);
  t->SetBranchAddress("V_pt", &V_pt);
  t->SetBranchAddress("V_eta", &V_eta);
  t->SetBranchAddress("V_phi", &V_phi);
  t->SetBranchAddress("V_mass", &V_mass);
  t->SetBranchAddress("H_pt", &H_pt);
  t->SetBranchAddress("H_eta", &H_eta);
  t->SetBranchAddress("H_phi", &H_phi);
  t->SetBranchAddress("H_mass", &H_mass);
  t->SetBranchAddress("GenHiggsSisters_pt", &Sis_pt);
  t->SetBranchAddress("GenHiggsSisters_eta", &Sis_eta);
  t->SetBranchAddress("GenHiggsSisters_phi", &Sis_phi);
  t->SetBranchAddress("GenHiggsSisters_mass", &Sis_mass);
  t->SetBranchAddress("GenHiggsSisters_pdgId", &Sis_pdgId);
  t->SetBranchAddress("genWeight", &weight);
  t->SetBranchAddress("Vtype", &Vtype);

  //_*_*_*_*_*_*_*_*
  //Perform the loop
  //_*_*_*_*_*_*_*_*

  // double nentries = t->GetEntries();
  double nentries = 1e5;
  for(Int_t i = 0; i < nentries; ++i){
    if(i%10000==0) cout << "event " << i << "/" << nentries << endl;
    t->GetEntry(i);
    
    if(Vtype!=0 && Vtype!=1) continue; // select only ZToMuMu or ZToEE 
    if(V_pt < 100) continue;
    
    //Build the V+H to cross-check
    TLorentzVector V, H, VH, VHj4v;
    // cout << "H_pt,H_eta,H_phi,H_mass= " << H_pt << " " << H_eta << " " << H_phi << " " <<H_mass << endl;
    V.SetPtEtaPhiM(V_pt,V_eta,V_phi,V_mass);
    H.SetPtEtaPhiM(H_pt,H_eta,H_phi,H_mass);
    VH = V+H;
    VHj4v = VH;
    
    vector<TLorentzVector> vOtherJets = OtherJets( Jet_pt,  Jet_eta,  Jet_phi,  Jet_mass, Jet_puId, Jet_id, Jet_aJCidx, Jet_hJCidx);
    vector<TLorentzVector> vSis = Sis(Sis_pt, Sis_eta, Sis_phi, Sis_mass, Sis_pdgId);
    
    if(weight < 0){weight = -1;}
    else if(weight > 0){weight = 1;}
    //weight = 1;
    
    h_VH->Fill(VH.Pt(),weight);
    
    for(unsigned int k = 0; k < PhiCut.size(); ++k){
      for(unsigned int l = 0; l < VHPtCut.size(); ++l){
        
        //Count n events
        nbinentries[k][l] += weight;
        
        double ISRj_Index = ISRj_Idx(V, H, VH, vOtherJets, PhiCut[k], VHPtCut[l], keep);
        int HSisIerISR_Index = HSisIerISR_Idx(V, H, VH, ISRj_Index, vOtherJets[ISRj_Index], vSis, PhiCut[k], VHPtCut[l]);
        
        int ISRj_matched_to_sister = vOtherJets[ISRj_Index].DeltaR(vSis[HSisIerISR_Index]) < 0.3 ? 1 : 0;
        
        if(ISRj_Index>-1){
          VHj4v+=vOtherJets[ISRj_Index];
          //Count #ISR tags
          nisrtag[k][l] +=  weight;
          
          if(HSisIerISR_Index>-1){
            hist_Sister_pt[k][l]->Fill(vSis[HSisIerISR_Index].Pt(),weight);
            hist_Sister_eta[k][l]->Fill(vSis[HSisIerISR_Index].Eta(),weight);
            hist_ISRjall_pt[k][l]->Fill(vOtherJets[ISRj_Index].Pt(),weight);
            hist_ISRjall_eta[k][l]->Fill(vOtherJets[ISRj_Index].Eta(),weight);
            
            if(ISRj_matched_to_sister==1){
              hist_ISRjmatched_pt[k][l]->Fill(vOtherJets[ISRj_Index].Pt(),weight);
              hist_ISRjmatched_eta[k][l]->Fill(vOtherJets[ISRj_Index].Eta(),weight);
              
            }
          }

          //VHj minimisation
          hist_VHj_pt[k][l]->Fill(VHj4v.Pt(),weight);
          // VHj[k][l]+= weight*VHj4v.Pt(); // TO BE CROSSCHECKED!
          
          //Sister optimisation
          pur[k][l] += weight*ISRj_matched_to_sister;
        }
              
      }
    }
  }

  //_*_*_*_*_*_*_*_
  //Save the histos
  //_*_*_*_*_*_*_*_
  h_VH->Scale(1./h_VH->Integral());
  TFile *fout = new TFile("results"+_sample+".root","RECREATE");
  for(unsigned int k = 0; k < PhiCut.size(); ++k){
    for(unsigned int l = 0; l < VHPtCut.size(); ++l){
      //compute isreff
      hist_VHj_pt[k][l]->Scale(1./hist_VHj_pt[k][l]->Integral());
      c_VHj_pt[k][l]->cd();
      hist_VHj_pt[k][l]->SetLineColor(2);
      hist_VHj_pt[k][l]->Draw();
      h_VH->Draw("same");
      c_VHj_pt[k][l]->Write();
      c_ISR_sister_pt[k][l]->cd();
      hist_Sister_pt[k][l]->Draw();
      hist_ISRjall_pt[k][l]->SetLineColor(3);
      hist_ISRjall_pt[k][l]->Draw("same");
      hist_ISRjmatched_pt[k][l]->SetLineColor(2);
      hist_ISRjmatched_pt[k][l]->Draw("same");
      c_ISR_sister_pt[k][l]->Write();
      c_ISR_sister_eta[k][l]->cd();
      hist_Sister_eta[k][l]->Draw();
      hist_ISRjall_eta[k][l]->SetLineColor(3);
      hist_ISRjall_eta[k][l]->Draw("same");
      hist_ISRjmatched_eta[k][l]->SetLineColor(2);
      hist_ISRjmatched_eta[k][l]->Draw("same");
      c_ISR_sister_eta[k][l]->Write();
      //cout<<"The VHj_Pt mean for PhiCut: "<<k<<" and VHPtCut "<<l<<" is "<<VHj[k][l]/nbinentries[k][l]<<endl;
      //cout<<"The Sister-ISR efficiency for PhiCut: "<<k<<" and VHPtCut "<<l<<" is "<<eff[k][l]/nisrtag[k][l]<<endl;
      //cout<<"The efficiency for PhiCut: "<<k<<" and VHPtCut "<<l<<" is "<<nisrtag[k][l]/nbinentries[k][l]<<endl;
    }
  }
  
  preparehisto(heff,"ISR-finder efficiency","#alpha","P_{T}(VH) Cut");
  preparehisto(hVHj,"P_{T}(VH + ISR Jets)","#alpha","P_{T}(VH) Cut");
  preparehisto(hpur,"ISR-finder purity","#alpha","P_{T}(VH) Cut");
  preparehisto(heffxpur,"ISR-finder purity x efficiency","#alpha","P_{T}(VH) Cut");
  
  for(unsigned int k = 0; k < 15; ++k){
    for(unsigned int l = 0; l < 8; ++l){
      
      ceff->cd();
      heff->Fill((PhiCut[k]+PhiCut[k+1])/2., (VHPtCut[l]+VHPtCut[l+1])/2., ((double)nisrtag[k][l])/((double)nbinentries[k][l])); //#efficiency to be ISR tagged
      heff->Draw("colz text");
      
      cVHj->cd();
      hVHj->Fill((PhiCut[k]+PhiCut[k+1])/2., (VHPtCut[l]+VHPtCut[l+1])/2., hist_VHj_pt[k][l]->GetMean());
      hVHj->Draw("colz text");
      
      cpur->cd();
      hpur->Fill((PhiCut[k]+PhiCut[k+1])/2., (VHPtCut[l]+VHPtCut[l+1])/2., pur[k][l]/nisrtag[k][l]);
      hpur->Draw("colz text");
      
      ceffxpur->cd();
      heffxpur->Fill((PhiCut[k]+PhiCut[k+1])/2., (VHPtCut[l]+VHPtCut[l+1])/2., ((double)pur[k][l])/((double)nbinentries[k][l]));
      heffxpur->Draw("colz text");
    
    }
  }

  gStyle->SetPaintTextFormat("4.2f");
  gStyle->SetOptStat(0);

  gROOT->ProcessLine(".! mkdir optimisation");
  cVHj->Write();
  cVHj->SaveAs("optimisation/VHj"+_sample+".pdf");
  cpur->Write();
  cpur->SaveAs("optimisation/pur"+_sample+".pdf");
  ceff->Write();
  ceff->SaveAs("optimisation/eff"+_sample+".pdf");
  ceffxpur->Write();
  ceffxpur->SaveAs("optimisation/effxpur"+_sample+".pdf");
  fout->Write();
  fout->Close();
}
