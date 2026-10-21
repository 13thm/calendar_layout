#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_lunar_2027.py — 生成 2027 全年农历/节气/节日数据
输出 data/lunar2027.js（index.html 通过 <script src> 引入，file:// 可用）
字段: days{"MM-DD": {lm:农历月名, ld:农历日名, t:节气, f:节日, r:法定/传统(红)}}
"""
import cnlunar, datetime, json, re, os

Y = 2027
# 公历节日（按月日）
SOLAR_FEST = {
    (1,1):"元旦",(2,14):"情人节",(3,8):"妇女节",(3,12):"植树节",(4,1):"愚人节",
    (5,1):"劳动节",(5,4):"青年节",(6,1):"儿童节",(9,10):"教师节",(10,1):"国庆节",
    (11,11):"双十一?",(12,24):"平安夜",(12,25):"圣诞节",
}
SOLAR_FEST.pop((11,11))  # 不需要的删掉
# 农历节日（按农历月/日）
LUNAR_FEST = {
    (1,1):"春节",(1,15):"元宵节",(5,5):"端午节",(7,7):"七夕",(8,15):"中秋节",
    (9,9):"重阳节",(12,8):"腊八节",(12,23):"小年",
}
# 红色标记（法定+传统大节）
RED_FEST = {"元旦","除夕","春节","元宵节","清明节","劳动节","端午节","七夕","中秋节","国庆节","重阳节"}

# 家人生日（农历月/日 → 名字），转换为 2027 公历日期；腊月/冬月生日若属上一农历年尾巴则取年内那次
BIRTHDAYS = [(8,11,"老妈"),(11,29,"老爸"),(4,25,"老弟"),(6,26,"老公"),(3,3,"悠悠"),
             (12,27,"妈妈"),(8,1,"爸爸"),(9,14,"外婆"),(1,6,"外公"),(8,4,"自己")]

def weekday_fest(dt):
    if dt.month==5 and dt.weekday()==6 and 8<=dt.day<=14: return "母亲节"
    if dt.month==6 and dt.weekday()==6 and 15<=dt.day<=21: return "父亲节"
    return None

days, gz, sx = {}, "", ""
d0 = datetime.date(Y,1,1)

# 预扫全年，为每个生日选定公历日期（优先农历2027丁未年的那次）
_lu = []
for i in range(365):
    dt = d0 + datetime.timedelta(days=i)
    a = cnlunar.Lunar(datetime.datetime(dt.year,dt.month,dt.day), godType='8char')
    _lu.append((dt, a.lunarMonth, a.lunarDay, a.lunarYear))
BIRTH_SOLAR = {}
for lm, ld, name in BIRTHDAYS:
    ms = [t for t in _lu if t[1]==lm and t[2]==ld]
    if not ms: continue
    pick = next((t for t in ms if t[3]==Y), ms[0])
    BIRTH_SOLAR[pick[0]] = name
    print(f"  生日 {name} 农历{lm}月{ld}日 → {pick[0]}")

for i in range(365):
    dt = d0 + datetime.timedelta(days=i)
    a = cnlunar.Lunar(datetime.datetime(dt.year,dt.month,dt.day), godType='8char')
    lm = re.sub(r'[大小]$','',a.lunarMonthCn)          # 正月大 → 正月
    ld = a.lunarDayCn
    t  = a.todaySolarTerms if a.todaySolarTerms != "无" else ""
    gz, sx = a.year8Char, a.chineseYearZodiac

    f = SOLAR_FEST.get((dt.month,dt.day)) or LUNAR_FEST.get((a.lunarMonth,a.lunarDay)) or weekday_fest(dt) or ""
    if t == "清明": f = "清明节"                        # 清明既是节气也是节日
    if a.lunarMonth==12 and a.lunarDay>=29:             # 除夕：正月初一的前一天
        nxt = cnlunar.Lunar(datetime.datetime(dt.year,dt.month,dt.day)+datetime.timedelta(days=1), godType='8char')
        if (nxt.lunarMonth,nxt.lunarDay)==(1,1): f="除夕"
    days[f"{dt.month:02d}-{dt.day:02d}"] = {"lm":lm,"ld":ld,"t":t,"f":f,"r":1 if f in RED_FEST else 0,"bd":BIRTH_SOLAR.get(dt,"")}

out = {"gz":gz,"sx":sx,"days":days}
js = "/* 2027 农历数据 · 由 scripts/gen_lunar_2027.py 生成 */\nconst LUNAR=" + json.dumps(out,ensure_ascii=False,separators=(",",":")) + ";"
path = os.path.join(os.path.dirname(__file__),"..","data","lunar2027.js")
open(path,"w",encoding="utf-8").write(js)
print(f"已生成 {path}（{len(days)} 天，{gz}{sx}年）")
# 打印关键节日核对
for k,v in days.items():
    if v["f"] in RED_FEST: print(f'  {k} {v["f"]}（{v["lm"]}{v["ld"]}）')
