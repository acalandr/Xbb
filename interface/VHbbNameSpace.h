#include "TLorentzVector.h"
#include "TVector3.h"
#include "TMath.h"

namespace VHbb {

  double deltaPhi(double phi1,double phi2)
  {
    double result = phi1 - phi2;
    while (result > TMath::Pi()) result -= 2*TMath::Pi();
    while (result <= -TMath::Pi()) result += 2*TMath::Pi();
    return result;
  }

  inline double deltaR(double eta1,double phi1,double eta2,double phi2)
    {
      double deta = eta1 - eta2;
      double dphi = deltaPhi(phi1, phi2);
      return std::sqrt(deta*deta + dphi*dphi);
    }


  double Hmass( double V_eta,double V_phi,double V_pt, 
		double hJet1_eta,double hJet1_phi,double hJet1_pt, 
		double hJet2_eta,double hJet2_phi,double hJet2_pt ){
    
    TVector3 V(1,1,1);
    V.SetPtEtaPhi(V_pt,V_eta,V_phi);
    
    TVector3 H1(1,1,1);
    H1.SetPtEtaPhi(hJet1_pt,hJet1_eta,hJet1_phi);
    H1.SetMag(1/sin(H1.Theta()));
    
    TVector3 H2(1,1,1);
    H2.SetPtEtaPhi(hJet2_pt,hJet2_eta,hJet2_phi);
    H2.SetMag(1/sin(H2.Theta()));
    
    TVector3 n1(H1);
    TVector3 n2(H2);
    
    float det= n1.Px() * n2.Py() - n2.Px() * n1.Py();
    
    H1.SetMag( (  - n2.Py() * V.Px() + n2.Px() * V.Py() )  / (sin(n1.Theta()) *det ) );
    H2.SetMag( ( + n1.Py() * V.Px() - n1.Px() * V.Py() )  / (sin(n2.Theta())  *det ) );
    
    float mass=std::sqrt( TMath::Power( (H1.Mag()+H2.Mag()),2 ) - TMath::Power(( ( H1+H2 ).Mag()),2) );
    
    return mass;
    
  }
  
  double Hmass_comb(double hJet1_eta,double hJet1_phi,double hJet1_pt, double hJet1_mass,
		    double hJet2_eta,double hJet2_phi,double hJet2_pt, double hJet2_mass){

    TLorentzVector H1, H2;
    H1.SetPtEtaPhiM(hJet1_pt,hJet1_eta,hJet1_phi, hJet1_mass);;
    H2.SetPtEtaPhiM(hJet2_pt,hJet2_eta,hJet2_phi, hJet2_mass);

    return (H1 + H2).M();

  }

  double Hmass_3j(double h_eta,double h_phi,double h_pt, double h_mass,
		  double aJet_eta,double aJet_phi,double aJet_pt, double aJet_mass){

    TLorentzVector H, H3;
    H.SetPtEtaPhiM( h_pt,h_eta,h_phi, h_mass);;
    H3.SetPtEtaPhiM(aJet_pt,aJet_eta,aJet_phi, aJet_mass);

    return (H + H3).M();


  }


}
