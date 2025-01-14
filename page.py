import tkinter as tk
from tkinter import ttk
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import numpy as np

ROOT_PATH = 'D:/github_repository/warning_effect_evaluation/'
# 读取故障表数据
def read_fault_data():
    return pd.read_csv(ROOT_PATH+'sz185_故障.csv')

def read_dim_data():
    return pd.read_csv(ROOT_PATH+'sz185_my_gen_fault_vis_dim.csv')


# 读取预警表数据（根据文件名前缀动态读取）
def read_warning_data():
    files = [f for f in os.listdir(ROOT_PATH+'所有预警/')]
    dfs = []
    for file in files:
        alarm_data = pd.read_csv(ROOT_PATH+'所有预警/'+file)
        alarm_data = alarm_data[['device_name','device_id','phase_name','phase_id','start_time','end_time','alarm_info']]
        alarm_data['start_time'] = pd.to_datetime(alarm_data['start_time'])
        alarm_data['scene'] = file
        dfs.append(alarm_data)
    return pd.concat(dfs) if dfs else pd.DataFrame()


# 根据故障开始时间筛选对应预警表中的数据，并计算相关统计信息
def process_data_for_fault(fault_data, warning_data, dim_data):
    warning_data['start_time'] = pd.to_datetime(warning_data['start_time'])
    fault_data['start_time'] = pd.to_datetime(fault_data['start_time'])
    results = []
    warnings = []
    
    for index, row in fault_data.iterrows():
        warning_df = warning_data[warning_data['start_time'] <= row['start_time']].reset_index(drop=True)
        warning_df = warning_df[warning_df['start_time'] >= (row['start_time'] - pd.DateOffset(months=6))].reset_index(drop=True)
        warning_df = warning_df[warning_df['device_id'] == row['device_id']].reset_index(drop=True)
        
        alarm_name = dim_data[(dim_data['sc_id']==row['sc_id'])&(dim_data['phase_id']==row['phase_id'])]['alarm_info']
        warning_df = warning_df[warning_df['alarm_info'].isin(alarm_name.to_list())].reset_index(drop=True)
        
        earliest_warning_time = warning_df['start_time'].min() if not warning_df.empty else None
        warning_count = len(warning_df)
        warning_days = len(warning_df['start_time'].dt.date.unique()) if not warning_df.empty else 0
        
        # 修改每月预警统计为按天数统计
        monthly_days = (warning_df.groupby(pd.Grouper(key='start_time', freq='M'))
                       .agg({'start_time': lambda x: len(x.dt.date.unique())})
                       .rename(columns={'start_time': 'days'})
                       .reset_index())
        monthly_days_dict = {month.strftime('%Y-%m'): days 
                           for month, days in zip(monthly_days['start_time'], monthly_days['days'])}

        result = {
            'site_id': row['site_id'],
            'site_name': row['site_name'],
            'phase_id': row['phase_id'],
            'phase_name': row['phase_name'],
            'device_id': row['device_id'],
            'device_name': row['device_name'],
            'fault_name': row['sc_name'],
            'fault_id': row['sc_id'],
            'fault_start_time': row['start_time'],
            'fault_end_time': row['end_time'],
            'last_time': row['time_duration'],
            'earliest_warning_time': earliest_warning_time,
            'warning_count': warning_count,
            'warning_days': warning_days,
            'monthly_counts': monthly_days_dict,
            'date_dif': (row['start_time'] - earliest_warning_time).days if earliest_warning_time else None
        }
        results.append(result)
        warnings.append(warning_df)
    
    return pd.DataFrame(results), warnings

