from dash import Dash, dash_table, html, dcc, Input, Output,callback_context
import plotly.express as px
from page import read_fault_data, read_warning_data, read_dim_data, process_data_for_fault
import pandas as pd
# from datetime import datetime

# 创建 Dash 应用
app = Dash(__name__)

# 获取数据
fault_data = read_fault_data()
fault_data = fault_data.drop_duplicates().reset_index(drop=True)
all_warning_data = read_warning_data()
all_warning_data = all_warning_data.sort_values(by=['device_name','start_time'], ascending=False).reset_index(drop=True)
dim_data = read_dim_data()
processed_data, warnings = process_data_for_fault(fault_data, all_warning_data, dim_data)
processed_data = processed_data[['site_name','phase_name','device_name',
                                 'fault_name','fault_start_time','fault_end_time',
                                 'earliest_warning_time','date_dif','warning_count','warning_days',
                                 'monthly_counts']]
# 获取所有月份的并集
all_months = set()
for _, row in processed_data.iterrows():
    all_months.update(row['monthly_counts'].keys())
all_months = sorted(list(all_months))

# 获取筛选选项（添加全选选项）
def get_options_with_select_all(values, field_name):
    unique_values = sorted(values.unique())
    return [{'label': f'全选{field_name}', 'value': 'ALL'}] + [
        {'label': str(x), 'value': str(x)} for x in unique_values
    ]

phase_options = get_options_with_select_all(processed_data['phase_name'], '风场')
device_options = get_options_with_select_all(processed_data['device_name'], '设备')
fault_options = get_options_with_select_all(processed_data['fault_name'], '故障')
date_min = processed_data['fault_start_time'].min()
date_max = processed_data['fault_start_time'].max()

# 定义统一的样式
DROPDOWN_STYLE = {
    'width': '100%',
    'height': '38px',  # 统一高度
}

LABEL_STYLE = {
    'height': '32px',
    'lineHeight': '32px',
    'marginBottom': '5px'
}

DATE_INPUT_STYLE = {  # 新增日期输入框样式
    'height': '38px',
    'lineHeight': '38px',
    'padding': '0 8px',
    'fontSize': '14px'  # 调整字体大小
}

# 修改 STYLES 中的 date_input 样式
STYLES = {
    'dropdown': {
        'width': '100%',
        'height': '38px',
    },
    'label': {
        'height': '32px',
        'lineHeight': '32px',
        'marginBottom': '5px'
    },
    'date_input': {
        'height': '38px',  # 控制日期输入框高度
        'lineHeight': '38px',
        'padding': '0 8px',
        'fontSize': '14px'
    },
    'container': {
        'padding': '20px',
        'backgroundColor': '#f8f9fa',
        'marginBottom': '20px'
    }
}

# 设置布局
app.layout = html.Div([
    # 标题
    html.H1("故障与预警分析系统", style={'textAlign': 'center'}),
    
    # 筛选器区域
    html.Div([
        # 第一行筛选器（相别、设备名称、故障名称、故障开始时间范围）
        html.Div([
            html.Div([
                html.Label('风场:', style=LABEL_STYLE),
                dcc.Dropdown(
                    id='phase-filter',
                    options=phase_options,
                    multi=True,
                    maxHeight=200,
                    style=DROPDOWN_STYLE,
                    placeholder='请选择风场...',
                    clearable=True,
                )
            ], style={'width': '15%', 'display': 'inline-block', 'marginRight': '10px'}),
            
            html.Div([
                html.Label('设备名称:', style=LABEL_STYLE),
                dcc.Dropdown(
                    id='device-filter',
                    options=device_options,
                    multi=True,
                    maxHeight=200,
                    style=DROPDOWN_STYLE,
                    placeholder='请选择设备...',
                    clearable=True,
                )
            ], style={'width': '15%', 'display': 'inline-block', 'marginRight': '10px'}),
            
            html.Div([
                html.Label('故障名称:', style=LABEL_STYLE),
                dcc.Dropdown(
                    id='fault-filter',
                    options=fault_options,
                    multi=True,
                    maxHeight=200,
                    style=DROPDOWN_STYLE,
                    placeholder='请选择故障...',
                    clearable=True,
                )
            ], style={'width': '15%', 'display': 'inline-block', 'marginRight': '10px'}),
            
            html.Div([
                html.Label('故障开始时间范围:', style=LABEL_STYLE),
                dcc.DatePickerRange(
                    id='date-range-filter',
                    min_date_allowed=date_min.date(),
                    max_date_allowed=date_max.date(),
                    start_date=date_min.date(),
                    end_date=date_max.date(),
                    display_format='YYYY-MM-DD',
                    first_day_of_week=1,
                    calendar_orientation='horizontal',
                    with_portal=False,
                    month_format='YYYY年 MM月',
                    show_outside_days=True,
                    clearable=True,
                    updatemode='bothdates',
                    number_of_months_shown=2,
                    reopen_calendar_on_clear=True,
                    persistence=True,
                    persisted_props=['start_date', 'end_date'],
                    style=DATE_INPUT_STYLE  # 使用新的样式
                )
            ], style={'width': '30%', 'display': 'inline-block'}),
        ], style={'marginBottom': '10px', 'display': 'flex', 'alignItems': 'flex-start'}),
        
        # 第二行筛选器（预警提前天数和预警天数）
        html.Div([
            html.Div([
                html.Label('预警提前天数:', style={'height': '32px', 'lineHeight': '32px'}),
                dcc.RangeSlider(
                    id='date-diff-filter',
                    min=int(processed_data['date_dif'].min()),
                    max=int(processed_data['date_dif'].max()),
                    step=1,
                    marks={i: str(i) for i in range(
                        int(processed_data['date_dif'].min()),
                        int(processed_data['date_dif'].max()) + 1,
                        max(1, int((processed_data['date_dif'].max() - processed_data['date_dif'].min()) / 5))
                    )},
                    value=[int(processed_data['date_dif'].min()), int(processed_data['date_dif'].max())],
                    allowCross=False,
                    tooltip={'placement': 'bottom', 'always_visible': True}
                )
            ], style={'width': '35%', 'display': 'inline-block', 'marginRight': '20px'}),
            
            html.Div([
                html.Label('预警天数:', style={'height': '32px', 'lineHeight': '32px'}),
                dcc.RangeSlider(
                    id='warning-count-filter',
                    min=int(processed_data['warning_days'].min()),
                    max=int(processed_data['warning_days'].max()),
                    step=1,
                    marks={i: str(i) for i in range(
                        int(processed_data['warning_days'].min()),
                        int(processed_data['warning_days'].max()) + 1,
                        max(1, int((processed_data['warning_days'].max() - processed_data['warning_days'].min()) / 5))
                    )},
                    value=[int(processed_data['warning_days'].min()), int(processed_data['warning_days'].max())],
                    allowCross=False,
                    tooltip={'placement': 'bottom', 'always_visible': True}
                )
            ], style={'width': '35%', 'display': 'inline-block', 'marginRight': '20px'}),
            
            # 筛选按钮
            html.Div([
                html.Button('应用筛选', id='apply-filters', n_clicks=0),
                html.Button('重置筛选', id='reset-filters', n_clicks=0, style={'marginLeft': '10px'}),
            ], style={'width': '20%', 'display': 'inline-block', 'verticalAlign': 'bottom'}),
        ], style={'marginBottom': '20px', 'display': 'flex', 'alignItems': 'center'}),
    ], style={'padding': '20px', 'backgroundColor': '#f8f9fa', 'marginBottom': '20px'}),
    
    # 主数据表格
    dash_table.DataTable(
        id='fault-table',
        data=processed_data.drop('monthly_counts', axis=1).to_dict('records'),
        columns=[{"name": i, "id": i} for i in processed_data.columns if i != 'monthly_counts'],
        style_table={
            'overflowX': 'auto',
            'width': '100%'
        },
        style_cell={
            'textAlign': 'left',
            'minWidth': '100px',
            'maxWidth': '180px',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
        },
        style_header={
            'backgroundColor': 'rgb(230, 230, 230)',
            'fontWeight': 'bold',
            'cursor': 'pointer'
        },
        page_size=15,
        row_selectable='single',
        selected_rows=[0],
        sort_action='native',
        sort_mode='single',
    ),
    
    # 下方展示区域（水平排列）
    html.Div([
        # 左侧柱状图
        html.Div([
            dcc.Graph(id='monthly-chart')
        ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'}),
        
        # 右侧预警信息表格
        html.Div([
            html.H3("预警信息", style={'marginTop': '0px'}),
            dash_table.DataTable(
                id='warning-table',
                columns=[
                    {"name": "预警开始时间", "id": "start_time"},
                    {"name": "预警结束时间", "id": "end_time"},
                    {"name": "预警信息", "id": "alarm_info"}
                ],
                style_table={
                    'overflowY': 'auto',
                    'maxHeight': '500px'
                },
                style_cell={
                    'textAlign': 'left',
                    'minWidth': '100px',
                    'maxWidth': '300px',
                    'overflow': 'hidden',
                    'textOverflow': 'ellipsis',
                },
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
                page_size=10,
            )
        ], style={'width': '50%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ], style={'width': '100%', 'display': 'flex'})
])

# 添加自定义CSS样式
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            .Select-multi-value-wrapper {
                max-height: 38px;
                overflow-y: auto;
            }
            .Select--multi .Select-value {
                display: inline-block;
                margin: 2px;
            }
            /* 日期选择器样式，重点控制高度 */
            .DateRangePicker {
                height: 38px !important;
            }
            .DateRangePickerInput {
                height: 38px !important;
                border-radius: 4px;
            }
            .DateInput {
                height: 38px !important;
            }
            .DateInput_input {
                height: 38px !important;
                line-height: 38px !important;
                padding: 0 8px;
                font-size: 14px;
                font-weight: normal;
            }
            .DateRangePickerInput_arrow {
                padding: 0 5px;
                line-height: 38px !important;
            }
            .rc-slider-tooltip {
                z-index: 999;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# 添加全选回调函数
@app.callback(
    [Output('phase-filter', 'value'),
     Output('device-filter', 'value'),
     Output('fault-filter', 'value')],
    [Input('phase-filter', 'value'),
     Input('device-filter', 'value'),
     Input('fault-filter', 'value')]
)
def update_multi_select(phase_selected, device_selected, fault_selected):
    ctx = callback_context
    if not ctx.triggered:
        return [], [], []
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    def handle_selection(selected, all_options):
        if not selected:
            return []
        if 'ALL' in selected:
            # 如果刚刚选中了"全选"
            if len(selected) == 1:
                return [opt['value'] for opt in all_options]
            # 如果取消了某个选项
            else:
                return [opt['value'] for opt in all_options if opt['value'] != 'ALL']
        # 如果选中了所有选项（除了"全选"）
        elif len(selected) == len(all_options) - 1:
            return [opt['value'] for opt in all_options]
        return selected

    if trigger_id == 'phase-filter':
        phase_selected = handle_selection(phase_selected, phase_options)
        return phase_selected, device_selected or [], fault_selected or []
    elif trigger_id == 'device-filter':
        device_selected = handle_selection(device_selected, device_options)
        return phase_selected or [], device_selected, fault_selected or []
    elif trigger_id == 'fault-filter':
        fault_selected = handle_selection(fault_selected, fault_options)
        return phase_selected or [], device_selected or [], fault_selected

# 修改筛选回调函数
@app.callback(
    [Output('fault-table', 'data'),
     Output('fault-table', 'selected_rows')],
    [Input('apply-filters', 'n_clicks'),
     Input('reset-filters', 'n_clicks'),
     Input('phase-filter', 'value'),
     Input('device-filter', 'value'),
     Input('fault-filter', 'value'),
     Input('date-diff-filter', 'value'),
     Input('warning-count-filter', 'value'),
     Input('date-range-filter', 'start_date'),
     Input('date-range-filter', 'end_date')]
)
def update_table(apply_clicks, reset_clicks, phases, devices, faults, 
                date_diff_range, warning_days_range, start_date, end_date):
    ctx = callback_context
    if not ctx.triggered:
        return processed_data.drop('monthly_counts', axis=1).to_dict('records'), [0]
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'reset-filters':
        return processed_data.drop('monthly_counts', axis=1).to_dict('records'), [0]
    
    filtered_data = processed_data.copy()
    
    # 处理筛选条件
    if phases and 'ALL' not in phases:
        filtered_data = filtered_data[filtered_data['phase_name'].isin(phases)]
    if devices and 'ALL' not in devices:
        filtered_data = filtered_data[filtered_data['device_name'].isin(devices)]
    if faults and 'ALL' not in faults:
        filtered_data = filtered_data[filtered_data['fault_name'].isin(faults)]
    if date_diff_range:
        filtered_data = filtered_data[
            (filtered_data['date_dif'] >= date_diff_range[0]) &
            (filtered_data['date_dif'] <= date_diff_range[1])
        ]
    if warning_days_range:  # 修改筛选逻辑，使用 warning_days
        filtered_data = filtered_data[
            (filtered_data['warning_days'] >= warning_days_range[0]) &
            (filtered_data['warning_days'] <= warning_days_range[1])
        ]
    if start_date and end_date:
        filtered_data = filtered_data[
            (filtered_data['fault_start_time'].dt.date >= pd.to_datetime(start_date).date()) &
            (filtered_data['fault_start_time'].dt.date <= pd.to_datetime(end_date).date())
        ]
    
    filtered_data = filtered_data.reset_index(drop=True)
    return filtered_data.drop('monthly_counts', axis=1).to_dict('records'), [0]

# 修改图表和预警信息的回调函数
@app.callback(
    [Output('monthly-chart', 'figure'),
     Output('warning-table', 'data')],
    [Input('fault-table', 'selected_rows'),
     Input('fault-table', 'data')]
)
def update_displays(selected_rows, current_table_data):
    if not selected_rows:
        selected_rows = [0]
    
    # 将当前表格数据转换回 DataFrame
    current_df = pd.DataFrame(current_table_data)
    
    # 获取选中行的数据
    selected_row = current_df.iloc[selected_rows[0]]
    
    # 使用多个条件匹配确保找到正确的行
    mask = (processed_data['device_name'] == selected_row['device_name']) & \
           (processed_data['phase_name'] == selected_row['phase_name']) & \
           (processed_data['fault_name'] == selected_row['fault_name']) & \
           (processed_data['fault_start_time'] == pd.to_datetime(selected_row['fault_start_time']))
    
    selected_row_data = processed_data[mask].iloc[0]
    selected_index = processed_data[mask].index[0]
    
    # 准备图表数据
    chart_data = pd.DataFrame({
        'month': all_months,
        'count': [selected_row_data['monthly_counts'].get(month, 0) for month in all_months]
    })
    
    # 创建图表
    fig = px.bar(
        data_frame=chart_data,
        x='month',
        y='count',
        title=f"设备 {selected_row_data['device_name']} - {pd.to_datetime(selected_row_data['fault_start_time']).date()} 的预警分布",
        labels={'month': '月份', 'count': '预警次数'}
    )
    
    # 自定义图表样式
    fig.update_layout(
        plot_bgcolor='white',
        xaxis=dict(
            title='月份',
            tickangle=45,
            gridcolor='lightgray',
            tickmode='array',
            ticktext=chart_data['month'],
            tickvals=chart_data['month']
        ),
        yaxis=dict(
            title='预警次数',
            gridcolor='lightgray'
        ),
        margin=dict(t=50, l=50, r=50, b=50)
    )
    
    # 获取对应的预警信息
    warning_df = warnings[selected_index]
    warning_data = warning_df[['start_time', 'end_time', 'alarm_info']].to_dict('records')
    
    return fig, warning_data

# 运行应用
if __name__ == '__main__':
    app.run_server(debug=True) 