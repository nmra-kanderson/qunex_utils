import os
import pandas as pd
import numpy as np


def read_freesurfer(qunex_run, stat_files=['aseg.stats', 'lh.aparc.stats', 'rh.aparc.stats']):
    '''
    Read freesurfer stats
    '''

    def _lines_to_df(fs_data, qunex_run):
        # read freesurfer data
        hemi = [x.split('hemi')[1].replace('\n','').replace(' ','') for x in fs_data if 'hemi' in x][0]
        fs_hdrs = [x for x in fs_data if 'ColHeaders' in x][0].split()
        fs_hdrs = fs_hdrs[2:]
        fs_df   = pd.DataFrame([x.split() for x in fs_data if '#' not in x])
        fs_df.columns = fs_hdrs
        fs_df.insert(0, 'id', qunex_run.session_info['id'])
        return fs_df


    def _read_surface(fs_data, qunex_run):
        # read freesurfer data
        hemi  = [x.split('hemi')[1].replace('\n','').replace(' ','') for x in fs_data if 'hemi' in x][0]
        fs_df = _lines_to_df(fs_data, qunex_run)

        meas_list = []
        for meas in ['SurfArea', 'ThickAvg', 'GrayVol']:
            fs_wide = fs_df.pivot(columns='StructName', values=meas, index='id')
            fs_wide.columns = meas + '_' + hemi + '_' +  fs_wide.columns
            meas_list.append(fs_wide)
        meas_df = pd.concat(meas_list, 1)
        return meas_df


    def _read_volume(fs_data, qunex_run):
        fs_df = _lines_to_df(fs_data, qunex_run)
        fs_wide = fs_df.pivot(columns='StructName', values='Volume_mm3', index='id')
        return fs_wide


    def _read_hdr(fs_dir, stat_file, qunex_run):
        fs_path = os.path.join(fs_dir, 'stats', stat_file)
        try:
            with open(fs_path, 'r') as f:
                fs_data = f.readlines()
            measure_lines = [x for x in fs_data if '# Measure' in x]
            measure_list  = [x.split()[2].replace(',','') for x in measure_lines]
            value_list    = [float(x.split()[-2].replace(',','')) for x in measure_lines]
            aseg_row      = pd.DataFrame(value_list).transpose()
            aseg_row.columns = measure_list
            aseg_row.insert(0, 'id', qunex_run.session_info['id'])
            aseg_row.set_index(['id'], inplace=True)
            return aseg_row
        except FileNotFoundError:
            return 'FileNotFoundError'


    # path to freesurfer output
    fs_dir = os.path.join(qunex_run.dir_hcp, qunex_run.session_info['id'], 'T1w', qunex_run.session_info['id'])
    
    # read data stored in the header of stats files
    hdr_measures = _read_hdr(fs_dir, stat_files[0], qunex_run)

    fs_list = []
    fs_list.append(hdr_measures)
    for stat_file in stat_files:
        # read freesurfer data as lines
        fs_path = os.path.join(fs_dir, 'stats', stat_file)
        if os.path.exists(fs_path):
            with open(fs_path, 'r') as f:
                fs_data = f.readlines()

        # pull freesurfer data (different format for surface vs volume)
        anat_type = [x.split('anatomy_type')[1].replace('\n','').replace(' ','') for x in fs_data if 'anatomy_type' in x][0]
        if anat_type == 'surface':
            fs_df = _read_surface(fs_data, qunex_run)
        elif anat_type == 'volume':
            fs_df = _read_volume(fs_data, qunex_run)
        
        fs_list.append(fs_df)
        
    # return combined freesurfer dataframe
    if len(fs_list) > 0:
        fs_df = pd.concat(fs_list, 1)
        return fs_df



def read_mask_stats(qunex_run):
    '''
    Read stats about mask coverage
    '''
    # if there are bold runs to process
    if len(qunex_run.bold_dict) > 0:
        mask_list = []
        for bold in qunex_run.bold_dict.keys():
            res_dir  = os.path.join(qunex_run.dir_hcp, qunex_run.session_info['id'], 'MNINonLinear/Results', str(bold))
            mask_path = os.path.join(res_dir, '{}_finalmask.stats.txt'.format(bold))
            if os.path.exists(mask_path):
                stats_df = pd.read_csv(os.path.join(res_dir, '{}_finalmask.stats.txt'.format(bold)))
                stats_df.insert(0, 'bold', bold)
                stats_df.insert(0, 'id', qunex_run.session_info['id'])
                mask_list.append(stats_df)
        if len(mask_list) > 0:
            mask_df = pd.concat(mask_list)
            return mask_df



def read_bold_motion(qunex_run):
    '''
    Read motion estimates from QUNEX formatted bold runs
    '''
    def _read_motion(read_path):
        if os.path.exists(read_path):
            with open(read_path, 'r') as f:
                dat = f.readlines()
            return_dat = float(dat[0].replace('\n',''))
        else: 
            return_dat = np.nan
        return return_dat

    # read the relative/absolute motion for each run
    est_list = []
    for bold in qunex_run.bold_dict.keys():
        bold_dir = os.path.join(qunex_run.dir_hcp, qunex_run.session_info['id'], str(bold))
        for motion_file in ['Movement_AbsoluteRMS_mean.txt', 'Movement_RelativeRMS_mean.txt']:
            est = _read_motion(os.path.join(bold_dir, motion_file))
            est_series = pd.Series({'id': qunex_run.session_info['id'],
                                    'scan': bold, 
                                    'measure': motion_file.replace('.txt',''),
                                    'motion':est})
            est_list.append(est_series)
    motion_df = pd.DataFrame(est_list)
    return motion_df



