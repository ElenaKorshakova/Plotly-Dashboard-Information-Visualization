import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd


# load data
data = pd.read_csv('data.csv')

# get list of indicators and groups
indicators = data['Indicator'].unique().tolist()
groups = data['Group'].unique().tolist()

# get list of available time periods+labels, start dates and country codes
time_periods = sorted(data['Time Period'].unique().tolist())
period2label = dict(data.groupby('Time Period').first()['Time Period Label'])
period2start = dict(data.groupby('Time Period').first()['Start Date'])
state2code = dict(data.groupby('State').first()['code'])

# set colors of background and text to be used
colors = {
    'background': '#0c0f26',
    'text': '#adb2bd'
}

# create instance of dash app
app = dash.Dash(__name__)
server = app.server

# create app layout
app.layout = html.Div([
    html.Label('Mental Health During the COVID-19 Pandemic in the US', className='title'),

    html.Div([
        html.Div([
            # Header
            html.Label('The COVID-19 pandemic has exacerbated mental health issues for many '
                       'people -- anxiety and depression have become the most common disorder '
                       'associated with a constant feeling of worry.', className='description'),

            # Type of disorder indicators radio items
            html.Div([html.Label('Type of Disorder', className='big-title')], className='wrapper'),
            dcc.RadioItems(
                options=[{'label': ind, 'value': ind} for ind in indicators],
                value=indicators[0],
                id='indicator',
            ),

            # Time period slider
            html.Label('Time Period', className='big-title'),
            dcc.Slider(
                min=time_periods[0],
                max=time_periods[-1],
                marks={i: period2start[i] for i in time_periods},
                value=time_periods[0],
                id='time-period',
            ),

            # Map
            dcc.Graph(
                id='map'
            ),
        ], className='col-left'),

        html.Div([
            # Demographic group select
            html.Label('Demographic group', className='big-title'),
            dcc.Dropdown(
                options=[{'label': gr, 'value': gr} for gr in groups],
                value=groups[0],
                clearable=False,
                id='group'
            ),

            dcc.Graph(
                id='bar'
            ),

            # Subgroup select
            html.Label('Sub-group', className='big-title'),
            dcc.Dropdown(
                options=[],
                value=[],
                clearable=False,
                id='sub-group',
                multi=True
            ),

            dcc.Graph(
                id='line'
            ),

        ], className='col-right'),
    ], className='main-container'),

    # Data source
    html.Div([
        html.Label('Data Source: '),
        html.A(['CDC Household Pulse Survey'], style={'color': colors['text']},
               href='https://data.cdc.gov/NCHS/Indicators-of-Anxiety-or-Depression-Based-on-Repor/8pt5-q6wp')
    ], className='data-source', style={'color': colors['text']})

], style={'columnCount': 1, 'backgroundColor': colors['background'], 'color': colors['text']}, className='back')


# callback to update subgroups select when main demographic group is changed
@app.callback(
    [Output(component_id='sub-group', component_property='options'),
     Output(component_id='sub-group', component_property='value')],
    [Input(component_id='group', component_property='value')]
)
def update_sub_groups(group):
    group2subgroup = {gr: data.loc[data['Group'] == gr, 'Subgroup'].unique().tolist() for gr in groups}
    return [{'label': gr, 'value': gr} for gr in group2subgroup[group]], group2subgroup[group][:1]


# callback to update map on change of type order indicator and time period
@app.callback(
    Output(component_id='map', component_property='figure'),
    [Input(component_id='indicator', component_property='value'),
     Input(component_id='time-period', component_property='value')]
)
def update_map(indicator, time_period):
    # get data for given indicator and time period
    map_data = data[data['Indicator'] == indicator]
    map_data = map_data[map_data['Time Period'] == time_period]

    # create plotly figure (map-Choropleth) based on the data
    fig = go.Figure(data=go.Choropleth(
        locations=map_data['code'],
        z=map_data['Value'].astype(float),
        locationmode='USA-states',
        colorscale='Blues',
        colorbar_title="Percentage",
        hovertext=map_data['State'],
        marker_line_color=colors['background'],
        marker_line_width=2
    ))

    # update figure layout
    fig.update_layout(
        title_text='',
        geo_scope='usa',
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor=colors['background'],
        paper_bgcolor=colors['background'],
        font_color=colors['text'],
        geo=dict(lakecolor=colors['background'],
                 bgcolor=colors['background'],
                 coastlinecolor=colors['background'],
                 visible=False)
    )

    return fig


# callback to update line plot on change of
# groups, subgroups and indicator (type of disorder)
@app.callback(
    Output(component_id='line', component_property='figure'),
    [Input(component_id='indicator', component_property='value'),
     Input(component_id='group', component_property='value'),
     Input(component_id='sub-group', component_property='value')]
)
def update_line(indicator, group, sub_group):
    # get subset of data for the indicator and group
    line_data = data[data['Indicator'] == indicator]
    line_data = line_data[line_data['Group'] == group]
    # get blue colors
    color_blues = px.colors.sequential.Blues

    # create instance of plotly figure
    fig = go.Figure()

    # iterate over each subgroups chosen in the corresponding select
    # and add a line for this subgroup
    for i, gr in enumerate(sub_group):
        sub_data = line_data.loc[line_data['Subgroup'] == gr, ['Time Period', 'Value', 'Low CI', 'High CI']]
        sub_data = sub_data.dropna().sort_values('Time Period')
        x = [period2start[i] for i in sub_data['Time Period']]
        y = sub_data['Value']
        fig.add_trace(go.Scatter(x=x, y=y, name=gr,
                                 mode='lines', showlegend=False,
                                 line=dict(color=color_blues[i % len(color_blues)])))

    # update figure
    fig.update_layout(
        title_text='',
        margin=dict(l=10, r=10, t=10, b=50),
        height=250,
        plot_bgcolor=colors['background'],
        paper_bgcolor=colors['background'],
        font_color=colors['text'],

    )
    fig.update_xaxes(showgrid=False,)
    fig.update_yaxes(nticks=7, showgrid=False,)

    return fig


# callback to update demographic group bar on change of
# indicator (type of disorder), group and time period
@app.callback(
    Output(component_id='bar', component_property='figure'),
    [Input(component_id='indicator', component_property='value'),
     Input(component_id='group', component_property='value'),
     Input(component_id='time-period', component_property='value')]
)
def update_bar(indicator, group, time_period):
    # get subset of data for this indicator, group, timeperiod
    bar_data = data[data['Indicator'] == indicator]
    bar_data = bar_data[bar_data['Group'] == group]
    bar_data = bar_data[bar_data['Time Period'] == time_period]

    # get data of only 3 columns
    # sort data by value in ascending order
    # drop rows if data is missing
    bar_data = bar_data[['Subgroup', 'Value', 'Low CI']]
    bar_data = bar_data.sort_values('Value', ascending=False)
    bar_data = bar_data.dropna()

    x = bar_data['Subgroup']
    y = bar_data['Value']

    # if group is state, get codes for this states instead of full names to fit well
    if group == 'By State':
        x = [state2code[i] for i in bar_data['Subgroup']]

    # create figure
    fig = go.Figure(data=go.Bar(x=x, y=y, marker_line_color=colors['background'],
                                marker_color='rgba(13, 87, 161, 1)'))

    # update layout
    fig.update_layout(
        title_text='',
        margin=dict(l=10, r=10, t=10, b=40),
        height=250,
        plot_bgcolor=colors['background'],
        paper_bgcolor=colors['background'],
        font_color=colors['text'],
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showline=False, linewidth=2, linecolor='black')
    fig.update_yaxes(showgrid=False, zeroline=False, showline=False, linewidth=2, linecolor='black')

    return fig


# run server
if __name__ == '__main__':
    app.run_server(debug=False)
