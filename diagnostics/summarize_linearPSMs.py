"""
Module: summarize_linearPSMs.py

 This script reads in data generated by LMR_PSMbuild.py
 and produces a summary of the linear forward models
 for proxy records used in LMR. The ouput of this consists of:
  1) Figures showing histograms of correlations of the linear fits
     per proxy types considred in the assimilation.
  2) Maps showing the correlations of the linear fits for 
     each calibrated proxy records, per proxy types. 
  3) Figures providing summary info for each calibrated proxy records,
     including scatter plots of data used in the calibration.

 author: Robert Tardif - Univ. of Washington
 date  : 5/17/2017

 Revisions:  

"""
import sys
import os
import cPickle
import numpy as np
import pandas as pd
import math
from collections import Counter

import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.colors import from_levels_and_colors
from mpl_toolkits.basemap import Basemap

sys.path.append('../')
from LMR_utils import coefficient_efficiency

# ------------------------------------------------------------ #
# -------------- Begin: user-defined parameters -------------- #

LMRdbversion = 'v0.2.0'
psm_type     = 'linear'        # linear or bilinear (only linear for now!)
calib_source = 'GISTEMP'       # linear: GISTEMP, MLOST, HadCRUT, BerkeleyEarth, GPCC or DaiPDSI
calib_season = 'annual'        # annual, seasonMETA, seasonPSM
inputdir     = '/home/disk/kalman3/rtardif/LMR/PSM'
dbdir        = '/home/disk/kalman3/rtardif/LMR/data/proxies'

PSM_Rcrit    = 0.2 # sites w/ "good" calibration 

make_proxy_individual_plots = True

# Region for maps. Choice of:
#  'GLOBAL', 'NAmerica', 'SAmerica', 'Europe', 'Asia', 'Africa', 'Australasia'
#  'Arctic', 'Antarctica', 'Greenland', 'TropicalPacific'
map_region = 'GLOBAL' 


# --------------  End: user-defined parameters  -------------- #
# ------------------------------------------------------------ #

plt.style.use('ggplot')

calib_source_var = {'GISTEMP': 'temperature',
                    'MLOST': 'temperature',
                    'HadCRUT': 'temperature',
                    'BerkeleyEarth': 'temperature',
                    'GPCC': 'moisture',
                    'DaiPDSI': 'moisture'
                    }

calib_tag = LMRdbversion+'_'+calib_season+'_'+calib_source
dirfig = inputdir+'/Figs_'+calib_tag

# create dirfig if it does not exist
if not os.path.isdir(dirfig):
    os.system('mkdir {}'.format(dirfig))

fname = inputdir+'/PSMs_NCDC_'+calib_tag+'_diag.pckl'
infile = open(fname,'r')
psm_data = cPickle.load(infile)
infile.close()

proxy_types_sites = sorted(psm_data.keys())
proxy_types = list(set([proxy_types_sites[k][0] for k in range(len(proxy_types_sites))]))

# metadata of proxies in the database
fname_meta = dbdir+'/NCDC_'+LMRdbversion+'_Metadata.df.pckl'
metadata = pd.read_pickle(fname_meta)


# --------------------------------------------
# ======== Summary of PSM fit errors  ========

outfilename = dirfig+'/PSM_summary_stats.txt'
outfile = open(outfilename,'w')

for t in sorted(proxy_types):

    mean_error_ratio = []
    var_error_ratio = []
    SNR_vals = []
    CE_vals = [] 
    
    ind = [j for j, item in enumerate(proxy_types_sites) if item[0] == t]
    for ts in [proxy_types_sites[k] for k in ind]:        
        ts_errors = psm_data[ts]['calib_proxy_values'] -  psm_data[ts]['calib_fit_values']
        ts_relative_mean_errors = np.mean(ts_errors)/np.mean(psm_data[ts]['calib_proxy_values'])
        ts_relative_var_errors = np.var(ts_errors)/np.var(psm_data[ts]['calib_proxy_values'])
        
        mean_error_ratio.append(ts_relative_mean_errors)
        var_error_ratio.append(ts_relative_var_errors)
        
        R2 = psm_data[ts]['PSMcorrel']*psm_data[ts]['PSMcorrel']
        k = 1 # linear...
        n = psm_data[ts]['NbCalPts']
        SNR_vals.append((R2/k)/((1-R2)/(n-k-1)))

        CE = coefficient_efficiency(psm_data[ts]['calib_proxy_values'],psm_data[ts]['calib_fit_values'])
        CE_vals.append(CE)

    outfile.write('%-30s : SNR(min,mean,max)=%7.2f %7.2f %7.2f CE(min,mean,max)=%7.4f %7.4f %7.4f \n'
                  %(t,np.min(SNR_vals), np.mean(SNR_vals), np.max(SNR_vals),
                    np.min(CE_vals), np.mean(CE_vals), np.max(CE_vals)))
    
    
outfile.close()
        
# --------------------------------------------
# === Histogram of calibration correlation === 

# file for diagnostic output (sensitivity)
fname = 'linearPSM_calibError_'+calib_tag+'.txt'
outfilename = os.path.join(dirfig, fname)
if os.path.exists(outfilename):
    os.system('rm -f {}'.format(outfilename))

# file for diagnostic output (seasonality)
if calib_season == 'seasonPSM':
    fname2 = 'linearPSM_calibSeasonality_'+calib_tag+'.txt'
    outfilename2 = os.path.join(dirfig, fname2)
    if os.path.exists(outfilename2):
        os.system('rm -f {}'.format(outfilename2))

    
for t in sorted(proxy_types):

    sites_goodPSM      = []
    sites_goodPSM_corr = []
    sites_allPSM_corr  = []
    sites_PSMagreeMetadata = []
    
    ind = [j for j, item in enumerate(proxy_types_sites) if item[0] == t]
    for ts in [proxy_types_sites[k] for k in ind]:
        sites_allPSM_corr.append(psm_data[ts]['PSMcorrel'])
        if abs(psm_data[ts]['PSMcorrel']) >= PSM_Rcrit:
            sites_goodPSM.append(ts)
            sites_goodPSM_corr.append(psm_data[ts]['PSMcorrel'])





            
        # -- checking sensitivity inferred from PSM vs metadata (if available) --

        site_meta = metadata[metadata['NCDC ID'] == ts[1]]
        climVar = site_meta['climateVariable'].iloc[0]
        sensi = site_meta['Relation_to_climateVariable'].iloc[0]
        # check seasonality
        meta_seasonality = site_meta['Seasonality'].iloc[0]
        calib_seasonality = psm_data[ts]['Seasonality']
        
        if climVar and sensi:
            if calib_source_var[calib_source] == 'temperature' and climVar == 'temperature':
                if psm_data[ts]['PSMslope'] > 0. and sensi == 'positive' or \
                   psm_data[ts]['PSMslope'] < 0. and sensi == 'negative':
                    sites_PSMagreeMetadata.append('agree')
                else:
                    sites_PSMagreeMetadata.append('disagree')
            elif calib_source_var[calib_source] == 'moisture' and climVar == 'moisture':
                if psm_data[ts]['PSMslope'] > 0. and sensi == 'positive' or \
                   psm_data[ts]['PSMslope'] < 0. and sensi == 'negative':
                    sites_PSMagreeMetadata.append('agree')
                else:
                    sites_PSMagreeMetadata.append('disagree')
            # conditions below assume warm-dry/cold-wet for agreement ...
            elif calib_source_var[calib_source] == 'temperature' and climVar == 'moisture':
                if psm_data[ts]['PSMslope'] > 0. and sensi == 'negative' or \
                   psm_data[ts]['PSMslope'] < 0. and sensi == 'positive':
                    sites_PSMagreeMetadata.append('agree')
                else:
                    sites_PSMagreeMetadata.append('disagree')
            elif calib_source_var[calib_source] == 'moisture' and climVar == 'temperature':
                if psm_data[ts]['PSMslope'] < 0. and sensi == 'positive' or \
                   psm_data[ts]['PSMslope'] > 0. and sensi == 'negative':
                    sites_PSMagreeMetadata.append('agree')
                else:
                    sites_PSMagreeMetadata.append('disagree')
            else:
                sites_PSMagreeMetadata.append('unknown')
        else:
            sites_PSMagreeMetadata.append('unknown')

        # print out if 'disagree' has been identified
        # last element of list corresponds to tested proxy record
        if sites_PSMagreeMetadata[-1] == 'disagree':
            if os.path.exists(outfilename):
                append_write = 'a'
            else:
                append_write = 'w'
            outfile = open(outfilename, append_write)
            outfile.write('{:120}'.format(str(ts))+' : Corr= '+"{:7.4f}".format(psm_data[ts]['PSMcorrel'])+\
                          ' Slope= '+"{:.4f}".format(psm_data[ts]['PSMslope'])+'\n')
            outfile.close()


        # for checking seasonality derived during PSM calibration
        if calib_season == 'seasonPSM':
            if os.path.exists(outfilename2):
                append_write = 'a'
            else:
                append_write = 'w'

            outfile2 = open(outfilename2, append_write)
            outfile2.write('{:120}'.format(str(ts))+' : Seasonality(metadata)= '+"{:48}".format(str(meta_seasonality))+\
                           ' Seasonality(calibration)= '+"{:48}".format(str(calib_seasonality))+'\n')
            outfile2.close()

    
    ALLcorr = np.asarray([sites_allPSM_corr[i] for i in range(len(sites_allPSM_corr))])
    GOODcorr = np.asarray([sites_goodPSM_corr[i] for i in range(len(sites_goodPSM_corr))])

    print('Proxy type: %s' %t)
    print('  Total nb of sites        : %4d' %len(sites_allPSM_corr))
    print('  Nb of sites w/ good PSM  : %4d' %len(sites_goodPSM))
    if len(sites_goodPSM) > 0:
        print('  Stats correlation magnitude for sites w/ good PSM: min=%6.4f mean=%6.4f median=%6.4f max=%6.4f' \
              %(np.min(abs(GOODcorr)), np.mean(abs(GOODcorr)), np.median(abs(GOODcorr)), np.max(abs(GOODcorr))))

    vsMetadata_unknown  = sites_PSMagreeMetadata.count('unknown')
    vsMetadata_agree    = sites_PSMagreeMetadata.count('agree')
    vsMetadata_disagree = sites_PSMagreeMetadata.count('disagree')

    
    

    
    if len(sites_allPSM_corr) > 0:

        fig = plt.figure()

        #bins = np.linspace(-1.05,1.05,22)
        bins = np.linspace(-1.025,1.025,42)
        #n, bins, patches = plt.hist(abs(GOODcorr), histtype='stepfilled',normed=False)
        n, bins, patches = plt.hist(ALLcorr, bins, histtype='stepfilled',normed=False)
        plt.setp(patches, 'facecolor', '#5CB8E6', 'alpha', 0.75)
        plt.title("%s - PSM calibration: %s" % (t, calib_source))
        plt.xlabel("Correlation")
        plt.ylabel("Count")
        xmin,xmax,ymin,ymax = plt.axis()

        # round up to next decade
        countmax = int(math.ceil(np.max(n)/10.)*10.)
        plt.axis((-1,1,0,countmax))

        xmin,xmax,ymin,ymax = plt.axis()
        plt.plot([-PSM_Rcrit,-PSM_Rcrit],[ymin,ymax],'--r')
        plt.plot([PSM_Rcrit,PSM_Rcrit],[ymin,ymax],'--r')

        # Annotate with summary stats
        ypos = ymax-0.05*(ymax-ymin)
        xpos = xmin+0.02*(xmax-xmin)
        plt.text(xpos,ypos,'Total = %s' % str(len(sites_allPSM_corr)),fontsize=9,fontweight='bold')
        ypos = ypos-0.05*(ymax-ymin)
        plt.text(xpos,ypos,'Nb. above threshold = %s' % str(len(sites_goodPSM_corr)),fontsize=9,fontweight='bold')
        ypos = ypos-0.05*(ymax-ymin)
        plt.text(xpos,ypos,'Nb. unknown vs metadata  = %s' % str(vsMetadata_unknown),fontsize=9,fontweight='bold')
        ypos = ypos-0.05*(ymax-ymin)
        plt.text(xpos,ypos,'Nb. agree vs metadata    = %s' % str(vsMetadata_agree),fontsize=9,fontweight='bold')
        ypos = ypos-0.05*(ymax-ymin)
        plt.text(xpos,ypos,'Nb. disagree vs metadata = %s' % str(vsMetadata_disagree),fontsize=9,fontweight='bold')
                
        # Save file
        plt.savefig('%s/hist_PSMcorr_%s_%s.png' % (dirfig,calib_tag,t.replace(" ", '_')),bbox_inches='tight')
        plt.close()


# --------------------------------------------
# ------ Map of calibration correlation ------

print(' ')
print('Creating maps of PSM correlation...')

water = '#9DD4F0'
continents = '#888888'
mapcolor = plt.cm.seismic
cbarfmt = '%4.1f'

fmin = -1.0; fmax = 1.0
fval = np.linspace(fmin, fmax, 100);  fvalc = np.linspace(0, fmax, 101);           
scaled_colors = mapcolor(fvalc)
cmap, norm = from_levels_and_colors(levels=fval, colors=scaled_colors, extend='both')
cbarticks=np.linspace(fmin,fmax,11)

# loop over proxy types & sites
l = []
ptypes = []
for t in proxy_types:

    ptypes.append(t)

    fig = plt.figure(figsize=[11,9])
    if map_region == 'GLOBAL':
        m = Basemap(projection='robin', lat_0=0, lon_0=0,resolution='l', area_thresh=700.0)
        latres = 20.; lonres=40.
    elif map_region == 'NAmerica':
        m = Basemap(projection='stere',width=12000000,height=8000000,lat_ts=50,lat_0=50,lon_0=-107.,resolution='l', 
                    area_thresh=700.0)
        latres = 10.; lonres=20.
    elif map_region == 'SAmerica':
        m = Basemap(projection='stere',width=12000000,height=8000000,lat_ts=90,lat_0=-22,lon_0=-67.,resolution='l',
                    area_thresh=700.0)
        latres = 10.; lonres=20.
    elif map_region == 'Europe':
        m = Basemap(projection='stere',width=7500000,height=5000000,lat_ts=30,lat_0=50,lon_0=20.,resolution='l',
                    area_thresh=700.0)
        latres = 10.; lonres=20.
    elif map_region == 'Asia':
        m = Basemap(projection='stere',width=13000000,height=9000000,lat_ts=90,lat_0=40,lon_0=100.,resolution='l',
                    area_thresh=700.0)
        latres = 10.; lonres=20.
    elif map_region == 'Africa':
        m = Basemap(projection='stere',width=12000000,height=8600000,lat_ts=90,lat_0=2,lon_0=20.,resolution='l',
                    area_thresh=700.0)
        latres = 10.; lonres=20.
    elif map_region == 'Australasia':
        m = Basemap(projection='stere',width=13500000,height=9000000,lat_ts=82,lat_0=-15,lon_0=132.,resolution='l',
                    area_thresh=700.0)
        latres = 10.; lonres=20.
    elif map_region == 'Arctic':
        m = Basemap(projection='npstere',boundinglat=60,lon_0=270,resolution='l', area_thresh=700.0)
        latres = 10.; lonres=20.
    elif map_region == 'Antarctica':
        m = Basemap(projection='spstere',boundinglat=-60,lon_0=180,resolution='l', area_thresh=700.0)
        latres = 10.; lonres=20.
    elif map_region == 'Greenland':
        m = Basemap(projection='stere',width=5000000,height=3000000,lat_ts=30,lat_0=72,lon_0=-40.,resolution='l',
                    area_thresh=700.0)
        latres = 10.; lonres=20.
    elif map_region == 'TropicalPacific':
        m = Basemap(projection='stere',width=18000000,height=9500000,lat_ts=30,lat_0=0,lon_0=-150.,resolution='l',
                    area_thresh=700.0)
        latres = 10.; lonres=20.
    else:
        raise SystemExit('Unrecognized region for mapping!')

    m.drawmapboundary(fill_color=water)
    m.drawcoastlines(); m.drawcountries()
    m.fillcontinents(color=continents,lake_color=water)
    m.drawparallels(np.arange(-80.,81.,latres))
    m.drawmeridians(np.arange(-180.,181.,lonres))

    ind = [j for j, item in enumerate(proxy_types_sites) if item[0] == t]
    for ts in [proxy_types_sites[k] for k in ind]:        

        sitemarker = 'o'
        lat = psm_data[ts]['lat']
        lon = psm_data[ts]['lon']
        x, y = m(lon,lat)

        l.append(m.scatter(x,y,35,c='white',marker=sitemarker,edgecolor='black',linewidth='1'))
        Gplt = m.scatter(x,y,35,c=psm_data[ts]['PSMcorrel'],marker=sitemarker,
                         edgecolor='black',linewidth='.5',zorder=4,cmap=cmap,norm=norm)

    cbar = m.colorbar(Gplt,location='right',pad="2%",size="2%",ticks=cbarticks,format=cbarfmt,extend='neither')
    cbar.outline.set_linewidth(1.0)
    cbar.set_label('%s' % 'Correlation',size=11,weight='bold')
    cbar.ax.tick_params(labelsize=10)
    plt.title("%s - PSM calibration: %s (%s)" % (t, calib_source,calib_season),fontweight='bold')

    plt.savefig('%s/map_%s_proxy_PSMcorr_%s_%s.png'
                % (dirfig,map_region,calib_tag,t.replace(" ", '_')),bbox_inches='tight')
    plt.close()

    

if make_proxy_individual_plots:
    # -----------------------------------------------
    # --- Scatter plots of proxy site calibration ---

    print(' ')
    print('Creating scatter plots showing PSM calibration characteristics, for each calibrated proxy record...')

    for t in sorted(proxy_types):

        ind = [j for j, item in enumerate(proxy_types_sites) if item[0] == t]
        for ts in [proxy_types_sites[k] for k in ind]:        

            proxy_type = ts[0]
            proxy_id   = ts[1]

            fig = plt.figure(figsize=[6,9])

            # --- scatter plots of calibration data ---
            ax = fig.add_subplot(2,1,1)

            plt.plot(psm_data[ts]['calib_refer_values'], psm_data[ts]['calib_proxy_values'],\
                               'o',markersize=8, markerfacecolor='#5CB8E6',
                               markeredgecolor='black', markeredgewidth=1,alpha=0.5)
            xmin, xmax, ymin, ymax = plt.axis()
            # the fit
            reg_x = psm_data[ts]['calib_refer_values']
            reg_x = np.insert(reg_x,0,xmin)
            reg_x = np.append(reg_x,xmax)
            line = psm_data[ts]['PSMslope'] * reg_x + psm_data[ts]['PSMintercept']
            plt.plot(reg_x,line, 'r-', linewidth=5, alpha=0.25)

            #plt.suptitle('%s' %(proxy_type),fontsize=14,fontweight='bold')
            plt.title('%s\n%s' % (proxy_type,proxy_id),fontsize=9,fontweight='bold')
            plt.xlabel('Calibration data : %s (%s)' %(calib_source, calib_season),fontweight='bold')
            plt.ylabel('Proxy data',fontweight='bold')
            xmin, xmax, ymin, ymax = plt.axis()

            ax.tick_params(axis='both', which='major',labelsize=10)

            # Annotate with summary stats
            ypos = ymax - 0.05 * (ymax - ymin)
            xpos = xmin + 0.025 * (xmax - xmin)
            plt.text(xpos, ypos, 'Nobs = %s' % str(psm_data[ts]['NbCalPts']), fontsize=10,
                     fontweight='bold')
            ypos = ypos - 0.05 * (ymax - ymin)
            plt.text(xpos, ypos,
                     'Slope = %s' % "{:.4f}".format(psm_data[ts]['PSMslope']),
                     fontsize=10, fontweight='bold')
            ypos = ypos - 0.05 * (ymax - ymin)
            plt.text(xpos, ypos,
                     'Intcpt = %s' % "{:.4f}".format(psm_data[ts]['PSMintercept']),
                     fontsize=10, fontweight='bold')
            ypos = ypos - 0.05 * (ymax - ymin)
            plt.text(xpos, ypos, 'Corr = %s' % "{:.4f}".format(psm_data[ts]['PSMcorrel']),
                     fontsize=10, fontweight='bold')
            ypos = ypos - 0.05 * (ymax - ymin)
            plt.text(xpos, ypos, 'Res.MSE = %s' % "{:.4f}".format(psm_data[ts]['PSMmse']),
                     fontsize=10, fontweight='bold')


            # --- proxy vs fit time series ---
            ax = fig.add_subplot(2,1,2)

            reg_x = psm_data[ts]['calib_refer_values']
            model = psm_data[ts]['PSMslope'] * reg_x + psm_data[ts]['PSMintercept']

            plot_time = np.arange(1850,2016,1)
            proxy_data = np.zeros(plot_time.shape); proxy_data[:] = np.nan
            model_data = np.zeros(plot_time.shape); model_data[:] = np.nan

            # indices of elements of psm_data[ts]['calib_time'] present in plot_time
            mask = np.in1d(plot_time,psm_data[ts]['calib_time'])
            proxy_data[mask] = psm_data[ts]['calib_proxy_values']
            model_data[mask] = model

            # plot with masking the missing data, if any
            ax.plot(plot_time, proxy_data, color='#5CB8E6',linewidth=2,alpha=.6)
            ax.plot(plot_time, model_data, 'r-', linewidth=2, alpha=.6)
            # plot dots to show isolated data points
            prx, = ax.plot(plot_time, proxy_data, '.', color='#5CB8E6', label='Proxy values')
            fit, = ax.plot(plot_time, model_data, '.', color='red', label='Forward model')

            plt.xlabel('Year',fontweight='bold')
            plt.ylabel('Proxy',fontweight='bold')

            ax.tick_params(axis='both', which='major',labelsize=10)        
            legend_properties = {'size':10, 'weight':'bold'}
            ax.legend(handles=[prx,fit],handlelength=0.5,ncol=1,loc='lower left',frameon=False,prop=legend_properties)

            fig.tight_layout()
            plt.savefig('%s/psmCalib_%s_%s%s_%s_%s.png' % (dirfig,psm_type,calib_source,calib_season,
                proxy_type.replace(" ", "_"), proxy_id.replace("/", "_")),bbox_inches='tight')
            plt.close()



