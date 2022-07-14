"""Module to determine spectral types of stars

@Author: Francis Fortin
"""

import math
import scipy.interpolate as interp
import numpy as np
from operator import itemgetter


type_to_num = {'O':0., 'B':1.,'A':2.,'F':3.,'G':4.,'K':5.,'M':6.}
num_to_type = {'0':'O', '1':'B', '2':'A', '3':'F', '4':'G', '5':'K', '6':'M'}


def spectype_to_number(spectype):
    """Translate the spectype (string) into an equivalent spectral number (float) from hot (0.) to
    cold (6.).
    """
    specs = []
    for i in range(len(spectype)):
        specs.append(type_to_num[spectype[i][0]]+0.1*float(spectype[i][1]))
    return np.asarray(specs)


def number_to_spectype(number):
    """Translate the spectral number (float) into the corresponding spectral type (str).
    """
    number = round(number,2)
    subtemp, temp = math.modf(number)
    subtemp = int(round(subtemp,2)*100)
    temp = str(int(temp))
    return num_to_type[temp]+str(subtemp/10.)

def dist(Teff, logg, Tref, gref):
    """Computes the relative distance in the Teff -- logg plane (log-log)
    """
    return np.sqrt((np.log10(Teff/Tref)/np.log10(Teff))**2 + ((logg - gref)/logg)**2)

def find_besttype(Teff, logg):
    """Finds the closest neighbourg of the input in the Teff -- logg plane

    Distance is measured according to the date on Main Sequence, Giant and Supergiant stars from
    Allen's Astrophysical Quantities.

    It returns the closest spectral type and luminosity class for each of those, ordered from
    closest to furthest.
    """
    dists = np.array([dist(Teff, logg, TMS, loggMS), dist(Teff, logg, TG, loggG), dist(Teff, logg, TSG, loggSG)])
    index = []
    mins = np.nanmin(dists, axis=1)
    for i in range(3):
        index.append(np.where(dists[i] == np.nanmin(dists[i]))[0][0])
    spectypes = [number_to_spectype(1.*fMS_T(np.log10(TMS[index[0]])))+' V', number_to_spectype(1.*fG_T(np.log10(TG[index[1]])))+' III', number_to_spectype(1.*fSG_T(np.log10(TSG[index[2]])))+' I']
    return sorted(np.array([spectypes,mins]).T, key=itemgetter(1))


# Allen's Astrophysical Quantities (entered manually :< )
MS_T = np.array([np.array(['O5','O9','B0','B2','B5','B8','A0','A2','A5','F0','F2','F5','F8','G0','G2','G5','G8','K0','K2','K5','M0','M2','M5']),np.array([42.,34.,30.,20.9,15.2,11.4,9.78,9.,8.18,7.3,7.,6.65,6.25,5.94,5.79,5.56,5.31,5.15,4.83,4.41,3.84,3.52,3.17])], dtype=object)
MS_g = np.array([np.array(['O3','O5','O6','O8','B0','B3','B5','B8','A0','A5','F0','F5','G0','G5','K0','K5','M0','M2','M5','M8']),np.array([-0.3,-0.4,-0.45,-0.5,-0.5,-0.5,-0.4,-0.4,-0.3,-0.15,-0.1,-0.1,-0.05,0.05,0.05,0.1,0.15,0.2,0.5,0.5])], dtype=object)

G_T = np.array([np.array(['G5','G8','K0','K2','K5','M0','M2','M5']), np.array([5.05,4.8,4.66,4.39,4.05,3.69,3.54,3.38])], dtype=object)
G_g = np.array([np.array(['B0','B5','A0','G0','G5','K0','K5','M0']), np.array([-1.1,-0.95,np.nan,-1.5,-1.9,-2.3,-2.7,-3.1])], dtype=object)

SG_T = np.array([np.array(['O9','B2','B5','B8','A0','A2','A5','F0','F2','F5','F8','G0','G2','G5','G8','K0','K2','K5','M0','M2','M5']),np.array([32.,17.6,13.6,11.1,9.98,9.38,8.61,7.46,7.03,6.37,5.75,5.37,5.19,4.93,4.7,4.55,4.31,3.99,3.62,3.37,2.88])], dtype=object)
SG_g = np.array([np.array(['O5','O6','O8','B0','B5','A0','A5','F0','F5','G0','G5','K0','K5','M0','M2']),np.array([-1.1,-1.2,-1.2,-1.6,-2.,-2.3,-2.4,-2.7,-3.,-3.1,-3.3,-3.5,-4.1,-4.3,-4.5])], dtype=object)

# Transform dirty data input into usable arrays
MS_T[0] = spectype_to_number(MS_T[0])
MS_g[0] = spectype_to_number(MS_g[0])

G_T[0] = spectype_to_number(G_T[0])
G_g[0] = spectype_to_number(G_g[0])

SG_T[0] = spectype_to_number(SG_T[0])
SG_g[0] = spectype_to_number(SG_g[0])

MS_T = MS_T.astype('float64')
MS_g = MS_g.astype('float64')

G_T = G_T.astype('float64')
G_g = G_g.astype('float64')

SG_T = SG_T.astype('float64')
SG_g = SG_g.astype('float64')

# Initialize range of Teff according to input data
TMS = np.logspace(np.log10(np.min(MS_T[1])),np.log10(np.max(MS_T[1])),100)
TG = np.logspace(np.log10(np.min(G_T[1])),np.log10(np.max(G_T[1])),100)
TSG = np.logspace(np.log10(np.min(SG_T[1])),np.log10(np.max(SG_T[1])),100)

# Interpolate the relation [spectral type = f(Teff)]
fMS_T = interp.interp1d(np.log10(MS_T[1]), MS_T[0], bounds_error=False)
fG_T = interp.interp1d(np.log10(G_T[1]), G_T[0], bounds_error=False)
fSG_T = interp.interp1d(np.log10(SG_T[1]), SG_T[0], bounds_error=False)

# Interpolate the relation [logg = f(spectral type)]
fMS_g = interp.interp1d(MS_g[0], MS_g[1], bounds_error=False)
fG_g = interp.interp1d(G_g[0], G_g[1], bounds_error=False)
fSG_g = interp.interp1d(SG_g[0], SG_g[1], bounds_error=False)

# Obtain logg = f(Teff)
loggMS = fMS_g(fMS_T(np.log10(TMS)))
loggG = fG_g(fG_T(np.log10(TG)))
loggSG = fSG_g(fSG_T(np.log10(TSG)))






