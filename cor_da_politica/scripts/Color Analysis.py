# -*- coding: utf-8 -*-
# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.3.4
#   kernelspec:
#     display_name: Python [conda env:root] *
#     language: python
#     name: conda-root-py
# ---

# +
import pandas as pd
import colorgram
import os
from pathlib import Path
import cv2
from PIL import Image
from ast import literal_eval
import numpy as np
import plotly.express as px

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from colormath.color_conversions import convert_color
from colormath.color_objects import *

pd.set_option('max_columns', None)


# -

def plot(fig):
    fig.update_layout(template='plotly_white', font_family='Roboto')
    fig.show()


# + [markdown] heading_collapsed=true
# # Color extraction

# + hidden=true
images_folder = './data/logos/png'
backgrounded_folder = './data/logos/backgrounded'

files = [f for f in os.listdir(images_folder) if '.png' in f]

for f in files:
    filename = '{}/{}'.format(images_folder, f)
    im = Image.open(filename)
    fill_color = (220,220,220)  # your new background color

    im = im.convert("RGBA")   # it had mode P after DL it from OP
    if im.mode in ('RGBA', 'LA'):
        background = Image.new(im.mode[:-1], im.size, fill_color)
        background.paste(im, im.split()[-1]) # omit transparency
        im = background

    new_filename = '{}/{}'.format(backgrounded_folder, f)

    im.convert("RGB").save(new_filename)

# + hidden=true
colors_dict = {}

for f in files:
    party_colors = []
    colors = colorgram.extract('{}/{}'.format(backgrounded_folder, f), 10)
    party = f.split('.')[0]
    print(party)

    for color in colors:
        party_colors.append({
            'rgb': [color.rgb.r, color.rgb.g, color.rgb.b],
            'hsl': [color.hsl.h, color.hsl.s, color.hsl.l],
            'proportion': color.proportion
            }
        )
    
    
    colors_dict[party] = party_colors

# + hidden=true
colors_df = pd.DataFrame.from_dict(colors_dict, orient='index')
colors_df.index.name = 'party'
cols = colors_df.columns.tolist()
colors_df = pd.melt(colors_df.reset_index(), id_vars='party', value_vars=cols).dropna().set_index('party')
colors_df = colors_df['value'].apply(pd.Series).sort_index()
colors_df.head()

# + hidden=true
colors_df.to_csv('./data/colors_with_background.csv', index=True)
# -

# # Color Prep Analysis

# + [markdown] heading_collapsed=true
# ## Remove background influence 

# + hidden=true
colors_raw = pd.read_csv('./data/colors_with_background.csv')

colors_raw['rgb'] = colors_raw['rgb'].apply(literal_eval)
colors_raw['hsl'] = colors_raw['hsl'].apply(literal_eval)

colors_raw.loc[:, 'lab'] = colors_raw['rgb'].apply(lambda x: convert_color(sRGBColor(x[0]/255, x[1]/255, x[2]/255), LabColor))
colors_raw.loc[:, 'lab'] = colors_raw['lab'].apply(lambda x: [x.lab_l, x.lab_a, x.lab_b])

colors_raw.loc[:, 'b_mean'] = (np.floor(colors_raw['rgb'].apply(lambda x: np.mean(x))/10)*10).astype(int)
colors_raw.loc[:, 'b_std'] = (colors_raw['rgb'].apply(lambda x: np.std(x)).astype(int))

colors_raw.loc[:, 'is_background'] = False
colors_raw.loc[(colors_raw['b_mean'].between(210, 220)) & (colors_raw['b_std'] <= 10), 'is_background'] = True

colors_raw.head()

# + hidden=true
colors_raw.loc[colors_raw['is_background']]

# + hidden=true
real_colors = colors_raw.loc[~colors_raw['is_background']].copy()

real_colors.loc[:, 'total_area'] = real_colors.groupby(['party'])['proportion'].transform('sum')

real_colors.loc[:, 'color_importance'] = real_colors['proportion']/real_colors['total_area']

real_colors.head()

# + hidden=true
real_colors.loc[:, ['party', 'rgb', 'hsl', 'lab', 'color_importance']].to_csv('./data/colors_cleaned.csv', index=False)

# + [markdown] heading_collapsed=true
# ## Main Colors

# + hidden=true
colors_df = pd.read_csv('./data/colors_cleaned.csv')

colors_df.loc[:, 'rank'] = colors_df.groupby(['party'])['color_importance'].rank(ascending=False)

colors_df['rgb'] = colors_df['rgb'].apply(literal_eval)
colors_df['hsl'] = colors_df['hsl'].apply(literal_eval)
colors_df['lab'] = colors_df['lab'].apply(literal_eval)

colors_df.loc[:, 'key'] = colors_df['party'] + '-' + colors_df['rank'].astype(int).astype(str)

# + hidden=true
colors_df.sort_values(by='rank', inplace=True)

colors_df.loc[:, 'cumul_importance'] = colors_df.groupby(['party'])['color_importance'].cumsum()

colors_df.head()

# + hidden=true
colors_df['party'].nunique()

# + hidden=true
px.line(colors_df, x='rank', y='cumul_importance', color='party')

# + hidden=true
# Choose colors threshold
main_colors = colors_df.copy()

# + hidden=true
df = main_colors.groupby(['party'], as_index=False).agg({'key':'count'}).sort_values(by='key')
px.bar(df, x='party', y='key')
# -

# ## Color clusters

# +
rgb_features = main_colors['rgb'].apply(pd.Series)
rgb_features.columns = ['rgb_r', 'rgb_g', 'rgb_b']

hsl_features = main_colors['hsl'].apply(pd.Series)
hsl_features.columns = ['hsl_h', 'hsl_s', 'hsl_l']

lab_features = main_colors['lab'].apply(pd.Series)
lab_features.columns = ['lab_l', 'lab_a', 'lab_b']

# features = pd.concat([rgb_features, hsl_features, lab_features], axis=1)
features = pd.concat([lab_features], axis=1)

features.head()

# +
# scaler = StandardScaler()
# scaled_features = scaler.fit_transform(features)

scaled_features = features

inertias = {}    
for k in range(1, 30):
    model = KMeans(k)
    model.fit(scaled_features)
    inertias[k] = model.inertia_
    
cluster_size_df = pd.DataFrame.from_dict(inertias, orient='index').reset_index()
cluster_size_df.columns = ['cluster_size', 'inertia']

px.line(cluster_size_df, x='cluster_size', y='inertia')

# +
# scaler = StandardScaler()
# scaled_features = scaler.fit_transform(features)

scaled_features = features
model = KMeans(5)
model.fit(scaled_features)

labels = model.labels_
# -

features_df.head()



# +
features_df = features.copy()
features_df.loc[:, 'cluster'] = labels
features_df.loc[:, 'importance'] = main_colors['color_importance']
features_df.loc[:, 'party'] = main_colors['party']


cols = ['rgb_r', 'rgb_g', 'rgb_b']
features_df.loc[:, cols] = rgb_features.loc[:, cols]

for c in cols:
    features_df.loc[:, c.split('_')[1]] = features_df[c]# * features_df['importance']

oper_dict = {
    'party':['count', 'nunique'],
    'importance':'sum',
    'r':'median',
    'g':'median',
    'b':'median',    
}

cluster_df = features_df.groupby(['cluster'], as_index=False).agg(oper_dict)

cluster_df.columns = ['cluster', 'total_colors', 'presence', 'prop_weight', 'r', 'g', 'b']

cluster_df.sort_values(by='total_colors', ascending=False, inplace=True)

cluster_df.loc[:, 'cluster'] = cluster_df['cluster'].astype(str)
# cluster_df.loc[:, 'prop_weight'] = cluster_df['total_colors']
cluster_df.loc[:, 'prop_weight'] = 1

cluster_df.loc[:, 'color'] = cluster_df.apply(lambda x: 'RGB({},{},{})'.format(int(x['r']/x['prop_weight']), 
                                                                               int(x['g']/x['prop_weight']), 
                                                                               int(x['b']/x['prop_weight'])), axis=1)

group_name = ['Claros', 'Escuros', 'Amarelos', 'Vermelhos', 'Verdes'] 
cluster_df.loc[:, 'cluster_name'] = group_name

color_map = cluster_df.set_index('cluster')['color'].to_dict()
color_names = cluster_df.set_index('cluster')['cluster_name'].to_dict()

cluster_df.head()

# +
main_colors_fit = main_colors.copy()
main_colors_fit.loc[:, 'color_label'] = features_df['cluster'].astype(str)
main_colors_fit.loc[:, 'color_cluster'] = main_colors_fit['color_label'].apply(lambda x: color_names[x])

main_colors_fit.loc[:, 'group_color_repr'] = main_colors_fit['color_label'].apply(lambda x: color_map[x])

main_colors_fit.loc[:, 'actual_color'] = main_colors_fit['rgb'].apply(lambda x: 'RGB({},{},{})'.format(x[0], x[1], x[2]))

main_colors_fit.loc[:, 'hue'] = main_colors_fit['hsl'].apply(lambda x: x[0])
main_colors_fit.loc[:, 'sat'] = main_colors_fit['hsl'].apply(lambda x: x[1])
main_colors_fit.loc[:, 'lum'] = main_colors_fit['hsl'].apply(lambda x: x[2])

actual_colors_map = main_colors_fit.set_index('key')['actual_color'].to_dict()

main_colors_fit.head()
# -

main_colors_fit.to_csv('./data/party_colors_infos.csv', index=False)

# # Data Analysis

# +
# Load data, column prep and info merge
party_df = pd.read_csv('./data/partidos_infos.csv')

party_df.loc[:, 'year'] = party_df['creation_date'].str[-4:].astype(int)
party_df.loc[:, 'number_disc'] = 10*np.floor(party_df['electoral_num']/10)

party_colors_df = pd.read_csv('./data/party_colors_infos.csv')

party_colors_df.loc[:, 'color_label'] = party_colors_df['color_label'].astype(str)

party_colors_df = pd.merge(left=party_colors_df, right=party_df, left_on='party', right_on='code', how='left')

party_colors_df.head()

# +
# All clusters view
df = party_colors_df\
        .groupby(['color_cluster', 'color_label'], as_index=False)\
        .agg({'color_importance':'sum', 'party':'nunique'})

df.loc[:, 'counter'] = 1
df.loc[:, 'total_parties'] = party_colors_df['party'].nunique()
df.loc[:, 'presence'] = 100*df['party']/df['total_parties']


df.sort_values(by='presence', ascending=False, inplace=True)

fig = px.scatter(df, x='color_cluster', y='counter', color='color_label', size='presence', text='presence',
           color_discrete_map=color_map, size_max=90)

fig.update_traces(
    marker=dict(line=dict(width=0.3,color='Black'), opacity=1))

fig.update_traces(textposition='top center', texttemplate='<b>%{text:.1f}%<b>')

fig.update_yaxes(showticklabels=False, showgrid=False, zeroline=False)
fig.update_xaxes(showgrid=False, tickfont_size=16)

fig.update_layout(
    title='Cores dos partidos, principais grupos',
    titlefont_size=20,
    xaxis_title='', 
    yaxis_title='', 
    showlegend=False)
plot(fig)

# +
df = party_colors_df.sort_values(by=['color_cluster', 'hue', 'sat', 'lum'])
df.loc[:, 'aux'] = 1

df.loc[:, 'rank'] = df['hue'].rank(method='first')
fig = px.bar(df, x='rank', y='aux', color='key',  color_discrete_map=actual_colors_map)
fig.update_yaxes(showticklabels=False, title='')
fig.update_xaxes(showticklabels=False, title='')
fig.update_traces(marker_line_color='grey', marker_line_width=0.05)
fig.update_layout(showlegend=False, 
                  title='Todas as cores encontradas nos logos dos partidos',
                  titlefont_size=18
                 )

plot(fig)

# +
df = party_colors_df.sort_values(by=['color_cluster', 'hue'])
df.loc[:, 'aux'] = 1.0
fig = px.bar(df, y='color_cluster', x=['aux', 'color_importance'], facet_col='variable',
             color='key',  color_discrete_map=actual_colors_map)
fig.update_traces(marker_line_color='grey', marker_line_width=0.05)
fig.update_xaxes(matches=None)
fig.update_layout(showlegend=False, title='5 grandes grupos de cor')

plot(fig)

# +
df = party_colors_df.sort_values(by=['color_importance', 'hue', 'party'], ascending=False)
df.loc[:, 'predominace'] = 100*df['color_importance']
                                 
fig = px.bar(df, y='party', x='predominace', color='key', 
             color_discrete_map=actual_colors_map, height=700)
fig.update_layout(
    showlegend=False, 
    yaxis_title='Partido', 
    xaxis_title='Predominância da cor (%)',
    title='Partidos e suas cores'
)
plot(fig)

# +
df = party_colors_df\
        .groupby(['party', 'color_cluster', 'color_label'], as_index=False)\
        .agg({'color_importance':'sum'})\
        .sort_values(by=['color_importance'], ascending=False)\
        .reset_index()

df.loc[:, 'predominace'] = 100*df['color_importance']
df.loc[:, 'color'] = df['color_label'].apply(lambda x: color_map[x])
df.loc[:, 'key'] = df['index'].astype(str)

aux_dict = df.set_index('key')['color'].to_dict()
                                 
fig = px.bar(df, y='party', x='predominace', color='key',
             color_discrete_map=aux_dict, height=700)

fig.update_layout(
    showlegend=False, 
    yaxis_title='Partido',
    title='Partidos e suas cores, por grupo de cor'
)
fig.update_xaxes(title='Predominância (%)')
fig.for_each_annotation(lambda a: a.update(text=a.text.split('=')[1]))
plot(fig)

# +
df = party_colors_df\
        .groupby(['party', 'color_cluster', 'color_label'], as_index=False)\
        .agg({'color_importance':'sum'})\
        .sort_values(by=['color_importance'], ascending=False)

df.loc[:, 'predominace'] = 100*df['color_importance']
                                 
fig = px.bar(df, y='party', x='predominace', color='color_label', facet_col='color_cluster',
             color_discrete_map=color_map, height=700, text='predominace')

fig.update_layout(
    showlegend=False, 
    yaxis_title='Partido',
    title='Partidos e suas cores, por grupo de cor'
)

fig.update_traces(texttemplate='%{text:.0f}%', textposition='outside')
fig.update_xaxes(title='Predominância (%)', range=[0, 130])
fig.for_each_annotation(lambda a: a.update(text=a.text.split('=')[1]))
plot(fig)
# -


