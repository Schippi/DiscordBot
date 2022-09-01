
import typing
import os
from Map import *
import plotly.express as px
import plotly.graph_objects as go
import aiohttp
import asyncio

def add_trace(fig,x,y,c,n):
    fig.add_trace(
        go.Scatter(x=x, y=y, mode='markers',
                   marker=dict(
                       color=c,
                        opacity=0.5
                   ),
                   name=n
                   )
    )


def read_map(filename, fig=None):
    showLeft = True
    showRight = True
    showPause = True


    print('File name :    ', os.path.basename(filename))
    with open(filename, "rb") as f:
        m = make_map(f)

    print('finished ')
    suffix=''
    if not fig:
        fig = go.Figure(layout_yaxis_range=[-1,116])
        fig.update_yaxes(nticks=50)
        color_l = 'red'
        color_r = 'blue'
    else:
        idx =filename.rindex('/')+1
        suffix='- ' + filename[idx:idx+4]
        color_l = 'green'
        color_r = 'orange'
    x = []
    y = []
    c = []
    if showPause:
        for p in m.pauses:
            for n in reversed(m.notes):
                if p.time < n.event_time:
                    #pass
                    n.event_time = n.event_time + p.duration
                else:
                    pass
                    #break
        pp = []
        for p in m.pauses:
            pp.extend([p.time+i for i in range(p.duration)])
        add_trace(fig,pp,[50 for _ in pp], 'green', 'Pauses' + suffix)

    mi =1800000
    ma = 0
    for n in m.notes:
        mi = min(n.event_time, mi)
        ma = max(ma, n.event_time)
    print(mi, ma)
    #fig.update_xaxes(nticks=round(ma/60*3))
    #fig.update_xaxes(tickmode='linear')
    fig.update_xaxes(dtick=30, tick0=100, tickmode='linear')
    #fig.update_xaxes(minor_dtick=50, minor_tick0=0, tickmode='linear')

    if showLeft:
        x = [n.event_time for n in m.notes if n.colorType == 0]
        y = [n.score for n in m.notes if n.colorType == 0]
        add_trace(fig, x, y, color_l, 'Left' + suffix)
    if showRight:
        x = [n.event_time for n in m.notes if n.colorType == 1]
        y = [n.score for n in m.notes if n.colorType == 1]
        add_trace(fig, x, y, color_r, 'Right' + suffix)

    # https://stackoverflow.com/questions/65941253/plotly-how-to-toggle-traces-with-a-button-similar-to-clicking-them-in-legend
    #fig= px.scatter(x=x, y=y, color=c, title=filename)

    return fig


if __name__ == '__main__':
    #https://api.beatleader.xyz/player/4476/scores?page=2
    #https://github.com/BeatLeader/BS-Open-Replay
    #filename = 'testData/4476-ExpertPlus-Standard-D04138A245357F230A3BFC568DE9AF89D4FAC687.bsor'
    filename = 'testData/4476-ExpertPlus-Standard-19.bsor'
    #False True
    score_id = 890820
    fig = read_map(filename)
    fig.show()

