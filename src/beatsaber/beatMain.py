
import typing
import os
from bsor.Bsor import *
from bsor.Scoring import *
import plotly.express as px
import plotly.graph_objects as go
import aiohttp
import asyncio

import pprint

# initialises a pretty printer
pp = pprint.PrettyPrinter(indent=4)

# We can now print with pp.pprint()

# use copy to make sure we don't break the original figure dictionary
import copy

# the function we'll use to print figure dictionaries
def pply(plyfig, data=False):

    # the data option allows us to control whether the data is printed or not
    if not data:
        po = copy.deepcopy(plyfig)
        po['data'] = [{i:trace[i] for i in trace if i not in ['x', 'y', 'z']} for trace in po['data']]

        pp.pprint(po)
    else:
        pp.pprint(plyfig)

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


def read_map(filename, fig=None, suffix = ''):
    showLeft = True #and False
    showRight = True #and False
    showPause = True #and False
    Angle = True# and False
    angle_score = False

    print('File name :    ', os.path.basename(filename))
    with open(filename, "rb") as f:
        m = make_bsor(f)

    stats = calc_stats(m)

    print('finished ')

    if not fig:
        from plotly.subplots import make_subplots
        fig = make_subplots(rows=2, cols=2,horizontal_spacing = 0.1,vertical_spacing = 0.05, specs=[
                                                                      [{"secondary_y": True},{}], #'rowspan':2
                                                                      [{},{"secondary_y": True}]
                                                                      ])

        #fig = go.Figure(layout_yaxis_range=[-1,136])
        fig.update_yaxes(nticks=50)
        color_l = 'red'
        color_r = 'blue'
        color_c = 'palevioletred'
    else:
        idx =filename.rindex('/')+1
        if not suffix:
            suffix='- ' + filename[idx:idx+4]
        color_l = 'green'
        color_r = 'yellow'
        color_c = 'lightgrey'
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
        x = [n.event_time for n in m.notes if n.colorType == 0 ]
        y = [n.score for n in m.notes if n.colorType == 0]
        add_trace(fig, x, y, color_l, 'Left' + suffix)
    if showRight:
        x = [n.event_time for n in m.notes if n.colorType == 1 ]
        y = [n.score for n in m.notes if n.colorType == 1 ]
        add_trace(fig, x, y, color_r, 'Right' + suffix)
    if Angle:
        x = [n.event_time for n in m.notes if hasattr(n,'cut') and n.cut.directionOk]
        y = [abs(abs(n.cut.cutAngle)- 90) for n in m.notes if hasattr(n,'cut') and n.cut.directionOk]
        add_trace(fig, x, y, color_c, 'Angle' + suffix)

    bad,miss,bomb = [0,0],[0,0],[0,0]

    for n in m.notes:
        if n.event_type == NOTE_EVENT_BAD:
            bad[n.colorType] = bad[n.colorType] + 1
            pass
        elif n.event_type == NOTE_EVENT_MISS:
            miss[n.colorType] = bad[n.colorType] + 1
            pass
        elif n.event_type == NOTE_EVENT_BOMB:
            bomb[n.colorType - 3] = bomb[n.colorType - 3] + 1
            pass
        if n.score > 0:
            index = n.lineIndex + 4*n.noteLineLayer
            if index > 11 or index < 0:
                index = 0

    combo = 0
    score_events = [(n.event_time,n) for n in m.notes]
    score_events.extend([(w.time,w) for w in m.walls])
    sorted_events = sorted(score_events,key=lambda x: x[0])
    max_score = 0
    multiplier = 1
    mul_progress = 0
    mul_max_progress = 2
    score = 0
    note_cnt = 0
    def inc_mul(i, progress, max_progress):
        if i >= 8:
            return i, progress, max_progress
        if progress < max_progress:
            progress = progress + 1
        if progress >= max_progress:
            i = i*2
            progress = 0
            max_progress = i * 2
        return i, progress, max_progress

    def dec_mul(i, progress, max_progress):
        progress = 0
        if i > 1:
            i = i//2
        max_progress = i * 2
        return i, progress, max_progress
    sco_x = []
    scores =[]
    max_scores = []
    avg_left = []
    avg_right = []
    avg = []
    avg_2 = []
    note_cnt_left = 0
    note_cnt_right = 0
    score_no_mul = 0
    max_score_no_mul = 0
    max_no_mul_left = 0
    max_no_mul_right = 0
    score_no_mul_left = 0
    score_no_mul_right = 0

    def get_angle_score(n):
        if hasattr(n,'cut'):
            angle_sub = abs(abs(n.cut.cutAngle)- 90)
            angle_sub = max(0, 15 - (angle_sub // 3))
            return angle_sub
        return 0

    m.fc_acc = [0]*4
    for idx,e in enumerate(sorted_events):
        note_score = e[1].score if isinstance(e[1],Note) else 0
        if angle_score:
            note_score = note_score + get_angle_score(n)

        if isinstance(e[1],Note):
            note_cnt = note_cnt + 1
            max_mul = 8 if note_cnt > 8+4+2 else 4 if note_cnt > 4+2 else 2 if note_cnt > 2 else 1
            if e[1].scoringType == NOTE_SCORE_TYPE_BURSTSLIDERELEMENT:
                max_score = max_score + max_mul * 20
                max_score_no_mul = max_score_no_mul + 20
                max_note = 20
            elif e[1].scoringType == NOTE_SCORE_TYPE_BURSTSLIDERHEAD:
                max_score = max_score + max_mul * 85
                max_score_no_mul = max_score_no_mul + 85
                max_note = 85
            else:
                max_note = 115 if not angle_score else 130
                max_score = max_score + max_mul * max_note
                max_score_no_mul = max_score_no_mul + max_note
            if note_score > 0:
                m.fc_acc[e[1].colorType*2] = m.fc_acc[e[1].colorType*2]+note_score
                m.fc_acc[e[1].colorType*2+1] = m.fc_acc[e[1].colorType*2+1]+max_note

            if e[1].colorType == 0:
                max_no_mul_left = max_no_mul_left + max_note
                score_no_mul_left = score_no_mul_left + note_score
                note_cnt_left = note_cnt_left + 1
                avg_left.append(score_no_mul_left / max_no_mul_left)
                avg_right.append(1 if len(avg_right) == 0 else avg_right[-1])

            if e[1].colorType == 1:
                max_no_mul_right = max_no_mul_right + max_note
                score_no_mul_right = score_no_mul_right + note_score
                note_cnt_right = note_cnt_right + 1
                avg_right.append(score_no_mul_right / max_no_mul_right)
                avg_left.append(1 if len(avg_left) == 0 else avg_left[-1])

        if isinstance(e[1],Wall) or isinstance(e[1],Note) and e[1].score == 0:
            multiplier,mul_progress,mul_max_progress = dec_mul(multiplier,mul_progress,mul_max_progress)
            combo = 0
        else:
            multiplier,mul_progress,mul_max_progress = inc_mul(multiplier,mul_progress,mul_max_progress)

            combo = combo + 1
            score = score + multiplier * note_score
            score_no_mul = score_no_mul + note_score
        avg.append(score_no_mul / max_score_no_mul)
        s = sum(avg) / len(avg)
        #avg_2.append(s)
        sco_x.append(e[1].event_time if isinstance(e[1],Note) else e[1].time)
        scores.append(score)
        max_scores.append(max_score)
    percent = score / max_score
    print('%d / %d' % (score, max_score))
    print('%.2f' %(percent*100))
    import plotly.graph_objects as go

    fig.add_trace(go.Scatter(x=sco_x, y=avg, name='avg'+suffix, marker=dict(
        color=color_c,
    )),secondary_y=True,row=1,col=1)

    fig.add_trace(go.Scatter(x=sco_x, y=max_scores, name='Max Score'),1,2)
    fig.add_trace(go.Scatter(x=sco_x, y=[n*percent for n in max_scores], name='Your Avg Score'+suffix, marker={'color':color_l}),1,2)
    fig.add_trace(go.Scatter(x=sco_x, y=scores, name='Score'+suffix, marker={'color':color_r}),1,2)

    #percent_scores = []
    #for i,j in zip(scores,max_scores):
    #    percent_scores.append(i / j)
    #fig.add_trace(go.Scatter(x=sco_x, y=percent_scores, name='percent'),2,1)


    right_notes = [n for n in m.notes if n.colorType == 1]
    #fig.add_trace(go.Scatter(x=sco_x, y=avg_2, name='avg_2'),2,1)
    fig.add_trace(go.Scatter(x=sco_x, y=avg_left, name='avg_left'+suffix, marker=dict(
        color=color_l,
    )),2,1)
    fig.add_trace(go.Scatter(x=sco_x, y=avg_right, name='avg_right'+suffix, marker=dict(
        color=color_r,
    )),2,1)
    fig.add_trace(go.Scatter(x=sco_x, y=avg, name='avg_no_mul'+suffix, marker=dict(
        color='green',
    )),2,1)


    stuff = zip(stats.score_at_time,stats.max_score_at_time)
    fig.add_trace(go.Scatter(x=sco_x, y=[j/l for (i,j),(k,l) in stuff], name='avg'+suffix, marker=dict(
        color='yellow',
    )),2,1)

    x = [i for i in range(-1,16)]
    yl = []
    yr = []
    an_l, an_r = [], []
    for i in x:
        yl.append(len([n for n in m.notes if n.acc_score == i and n.colorType == 0]))
        yr.append(len([n for n in m.notes if n.acc_score == i and n.colorType == 1]))
        an_l.append(len([n for n in m.notes if n.colorType == 0 and get_angle_score(n) == i]))
        an_r.append(len([n for n in m.notes if n.colorType == 1 and get_angle_score(n) == i]))


    fig.add_bar(x=x,y=yl,row=2,col=2,name='<acc left'+suffix,marker=dict(
        color=color_l,
    ))
    fig.add_bar(x=x,y=yr,row=2,col=2,name='acc right>'+suffix,marker=dict(
        color=color_r,
    ))

    if angle_score:
        fig.add_bar(x=x,y=an_l,row=2,col=2,name='<ang left'+suffix,marker=dict(
            color=color_l,
        ))
        fig.add_bar(x=x,y=an_r,row=2,col=2,name='ang right>'+suffix,marker=dict(
            color=color_r,
        ))

    x = [i for i in range(70)]
    yl = []
    yr = []
    for i in x:
        yl.append(len([n for n in m.notes if n.pre_score == i and n.colorType == 0 and n.score > 0]))
        yr.append(len([n for n in m.notes if n.pre_score == i and n.colorType == 1 and n.score > 0]))

    fig.add_bar(x=x,y=yl,row=2,col=2,name='<pre left'+suffix,marker=dict(
        color=color_l,
    ))
    fig.add_bar(x=x,y=yr,row=2,col=2,name='pre right>'+suffix,marker=dict(
        color=color_r,
    ))

    x = [i for i in range(30)]
    yll = []
    yrl = []
    for i in x:
        yll.append(len([n for n in m.notes if n.post_score == i and n.colorType == 0 and n.score > 0]))
        yrl.append(len([n for n in m.notes if n.post_score == i and n.colorType == 1 and n.score > 0]))

    fig.add_bar(x=x,y=yll,row=2,col=2,name='<post left'+suffix,marker=dict(
        color=color_l,
    ))
    fig.add_bar(x=x,y=yrl,row=2,col=2,name='post right>'+suffix,marker=dict(
        color=color_r,
    ))







    # https://stackoverflow.com/questions/65941253/plotly-how-to-toggle-traces-with-a-button-similar-to-clicking-them-in-legend
    #fig= px.scatter(x=x, y=y, color=c, title=filename)
    fig.update_layout(template='plotly_dark')
    return fig,m


if __name__ == '__main__':
    #https://api.beatleader.xyz/player/4476/scores?page=2
    #https://github.com/BeatLeader/BS-Open-Replay
    #filename = 'testData/4476-ExpertPlus-Standard-D04138A245357F230A3BFC568DE9AF89D4FAC687.bsor'
    #filename = 'D:/_TMP/Lady.bsor'
    #False True
    score_id = 890820
    #1138594?vgl=1138910
    #fig = read_map(filename)
    fig = read_map('D:/_TMP/1138594.bsor')
    fig = read_map('D:/_TMP/1138910.bsor',fig)
    fig.show()

