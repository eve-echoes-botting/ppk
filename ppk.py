import time
import hashlib
import random
import requests
import discord
from discord.ext import commands, tasks
from pd import pd
import re
from datetime import datetime, timedelta
import pytz 
from itertools import zip_longest
import asyncio



async def setup(bot):
    l = ppk_cog(bot)
    await bot.add_cog(l)
    l.keeper.start()

trashbin = '\U0001F5D1'
guid = 871762312208474133
uid4o = 139179662369751041
cid = 1092302014647640125
mf = '%Y-%m-%d %H:%M:%S:%f'
jonid = 339395756568084482
jonid = 466724591109144588
ppkc = 1017423962617168015
cfgid = 1017423962617168015

def tostr(d):
    return d.strftime(mf)

def fromstr(s):
    return datetime.strptime(s, mf)

class ppk_cog(commands.Cog):
    def __init__(self, bot):
        print('ppk module loaded')
        self.bot = bot
        self.pd = pd('ppk.json')
        self.errors = []
        self.started = False

    @commands.command()
    async def ppknew(self, ctx):
        try:
            ids = []
            names = []
            namesq = ['JonSolo']
            ships = []
            num = 0
            channel_id = ppkc  # Replace with the desired channel ID
            channel = self.bot.get_channel(channel_id)
            lut = await read_lut(channel)
            while namesq and num < 50:
                await asyncio.sleep(0.1)
                n = namesq.pop()
                if ' ' in n and n[0] == '"' and n[-1] == '"':
                    n = n[1:-1]
                if n not in names:
                    num += 1
                    names.append(n)
                    d = getall(n)
                    for i in d:
                        for j in ['victim_ship_type', 'killer_ship_type']:
                            s = i[j]
                            if ' ' in s and s[0] == '"' and s[-1] == '"':
                                s = s[1:-1]
                            if s not in ships and s not in lut.keys():
                                ships.append(s)
                        for j in ['victim_name', 'killer_name']:
                            n = i[j]
                            if n not in names:
                                namesq.append(n)
            s = ''
            for i in ships:
                s += i + '\n'
                if len(s) > 1500:
                    await ctx.send(s)
                    s = ''
            await ctx.send('done')
        except Exception as e:
            await ctx.send(str(s))
            raise

    @commands.command()
    async def ppkerrors(self, ctx):
        channel_id = ppkc
        channel = self.bot.get_channel(channel_id)
        if self.errors:
            await channel.send(f'error messages: {len(self.errors)}')
        for i in self.errors:
            await channel.send(f'[error msg]({i[0].jump_url}), error in line: {i[1]}')

    @commands.command()
    async def ppk(self, ctx, *args):
        await self.ppk_do(True)

    @tasks.loop(hours = 8)
    async def keeper(self, force = False):
        return
        if self.started:
            try:
                await self.ppk_do()
                await self.ppkerrors(None)
            except Exception as e:
                channel_id = ppkc
                channel = self.bot.get_channel(channel_id)
                await channel.send(f'error: {e}, error messages: {len(self.errors)}')
                for i in self.errors:
                    await channel.send(f'[error msg]({i.jump_url}), error in line: {self.errmsg}')
        else:
            self.started = True

    async def ppk_do(self, force = False):
        b = self.bot
        channel_id = ppkc
        channel = b.get_channel(channel_id)
        cfgc = b.get_channel(cfgid)
        today = datetime.utcnow()
        start_date = today - timedelta(days=today.weekday() + 7)
        end_date = start_date + timedelta(days=7)
        week = (start_date + timedelta(1)).isocalendar()[1]
        year = (start_date + timedelta(1)).year
        if not force:
            if not await can_post(channel, week, year):
                return
        await channel.send('ppk started')
        limits = await read_limits(self, cfgc)
        lut = await read_lut(self, cfgc)
        d = get()
        ret = {}
        unknown = []
        capclasses = ['Versatile Assault Ship', 'Carrier', 'Industrial Command Ship', 'Dreadnought', 'Supercarrier', 'Force Auxiliary', 'Capital Industrial Ship']
        capkills = []
        for _, v in d.items():
            if v['victim_ship_category'] in capclasses:
                capkills.append(v)
                continue
            pilot = v['killer_name']
            isk = v['isk']
            loc = ''
            ship = v['victim_ship_type']
            if ship[0] == '"':
                ship = ship[1:]
            if ship[-1] == '"':
                ship = ship[:-1]
            killed = ship
            try:
                payout = lut[ship]['val']
                hc = lut[killed]['type']
            except:
                unknown.append(killed)
                killed = 'error'
                continue
            v = (pilot, killed, isk, loc, payout)
            if hc not in ret:
                ret[hc] = [v]
            else:
                ret[hc].append(v)

        tmp = {}
        limiterror = []
        for i, v in ret.items():
            try:
                if limits[i] < len(v):
                    tmp[i] = random.sample(v, int(limits[i]))
                else:
                    tmp[i] = ret[i]
            except:
                limiterror.append(i)

        ret = {}
        for k, v in tmp.items():
            for i in v:
                pilot, killed, isk, loc, payout = i
                if pilot not in ret:
                    ret[pilot] = [(killed, isk, loc, payout)]
                else:
                    ret[pilot].append((killed, isk, loc, payout))

        s = f'ppk week: {week}/{year}\n'
        total = 0
        for k, v in ret.items():
            d = {}
            isk = 0
            for i in v:
                isk += lut[i[0]]['val']
            total += isk

        mul = await read_budget(self, cfgc)/total
        payouts = {}
        for k, v in ret.items():
            d = {}
            isk = 0
            for i in v:
                t = lut[i[0]]['type']
                if t in d:
                    d[t] += 1
                else:
                    d[t] = 1
                isk += lut[i[0]]['val']
            s += ' '.join([k, ':', '{:.2f}'.format(isk*mul), 'cookies']) + '\n'
            payouts[k] = int(isk*mul)
            for k, v in d.items():
                s += ' '.join(['    ', str(v) + 'x', k]) + '\n'
        s += ' '.join(['total:', str(total*mul), 'cookies']) + '\n'
        if unknown:
            s += f'<@{466724591109144588}> new hull names: {unknown}' + '\n'
        if limiterror:
            s += f'<@{466724591109144588}> please set limits for: {limiterror}' + '\n'
        s += '\n'.join([x['image_url'] for x in capkills])
        msg = await channel.send(s)
        await msg.pin()
        payouts = await self.handle_payouts(channel, payouts)
        pos = '\n'.join([f'{k}: :{v}' for k, v in payouts.items()])
        await channel.send('buffered payouts:\n' + pos + '\nif you see your alt here, claim it with `.myalt <name>`')

    async def handle_payouts(self, ctx, d):
        alts = pd('alts.json')
        ret = {}
        for k, v in d.items():
            k = k.lower()
            id = None
            for ak, av in alts.items():
                if k in av:
                    id = ak
            if not id:
                ret[k] = v
            else:
                print(f'adding {k} {v}')
                await ctx.send(self.bot.cogs['Banking']._change(id, v))
        return ret

    @commands.command()
    async def myalt(self, ctx, name, member = None):
        alts = pd('alts.json')
        if ctx.message.mentions:
            k = str(ctx.message.mentions[0].id)
        else:
            k = str(ctx.author.id)
        if k not in alts:
            alts[k] = []
        alts[k].append(name.lower())
        alts.sync()
        await ctx.send(f'your alts: {alts[k]}')

async def can_post(c, week, year):
    pins = await c.pins()
    lut = {}
    for i in pins:
        if i.content.startswith(f'ppk week: {week}/{year}'):
            return False
    return True
 
async def read_budget(self, c):
    pins = await c.pins()
    lut = {}
    for i in pins:
        if i.content.startswith('ppk budget:'):
            try:
                return float(i.content.split('\n')[1])
            except:
                self.errors.append((), Nonei)

async def read_limits(self, c):
    pins = await c.pins()
    lut = {}
    for i in pins:
        if i.content.startswith('ppk limits:'):
            try:
                lines = i.content.split('\n')[1:]
                for j in lines:
                    j.replace(' ', '')
                    t, v = j.split(':')
                    lut[t] = float(v)
            except:
                self.errors.append((i, j))

    return lut

async def read_lut(self, c):
    pins = await c.pins()
    lut = {}
    for i in pins:
        if i.content.startswith('ppk lut:'):
            try:
                lines = i.content.split('\n')[1:]
                for j in lines:
                    j.replace(' ', '')
                    n, v, t = re.split(': |, ', j)
                    lut[n] = {'val': float(v), 'type': t}
            except:
                self.errors.append((i, j))

    return lut

def get():
    url = 'https://echoes.mobi/api/killmails?page=1&order%5Bdate_killed%5D=desc&victim_corp=LSR'
    url = 'https://echoes.mobi/api/killmails?page=1&order%5Bdate_killed%5D=desc&killer_corp=LSR'
    #url = 'https://echoes.mobi/api/killmails?page=1&order%5Bdate_killed%5D=desc&victim_corp=HELL'
    txt = requests.get(url).content.decode('utf-8')
    txt = txt.split('\n')
    keys = txt[0].split(',')
    values = [x.split(',') for x in txt[1:]]
    values = txt[1:]
    today = datetime.now(pytz.utc)
    start_date = today - timedelta(days=today.weekday() + 7)
    end_date = start_date + timedelta(days=7)
    d = {}
    for i in values:
        tmp = {}
        lw = False
        sv = False
        i = i.split(',')
        key = None
        for j in zip(keys,i):
            if j[0] == 'isk' and j[1] == '"':
                key = 'isk'
            kv = j[0]
            if key:
                kv = key
                key = j[0]
            if kv == 'region':
                sv = j[1].startswith('Provi')
            if kv == 'date_killed':
                date = datetime.strptime(j[1], "%Y-%m-%dT%H:%M:%S%z")
                tmp[kv] = date
                if date > start_date and date <= end_date:
                    lw = True
            else:
                tmp[kv] = j[1]
    #    if lw and sv:
        if lw:
            d[tmp['id']] = tmp
    return d

def getall(arg):
    return [*getone(arg, 'killer'), *getone(arg, 'victim')]

def getone(n, t):
    url = f'https://echoes.mobi/api/killmails?page=1&{t}_name={n}'
    txt = requests.get(url).content.decode('utf-8')
    txt = txt.split('\n')
    keys = txt[0].split(',')
    values = [x.split(',') for x in txt[1:]]
    values = txt[1:]
    d = []
    for i in values:
        if len(i) == 0:
            continue
        tmp = {}
        i = i.split(',')
        key = None
        for j in zip_longest(keys,i):
            if j[0] == 'id' and j[1] == '':
                continue
            if j[0] == 'isk' and j[1] == '"':
                key = 'isk'
            kv = j[0]
            if key:
                kv = key
                key = j[0]
            tmp[kv] = j[1]
        d.append(tmp)
    return d

