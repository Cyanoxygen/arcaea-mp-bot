#!/usr/bin/env python3
from pyrogram import Client, Filters
from datetime import datetime, timedelta
from arcaea import *
from config import *
import logging
import random
from time import sleep, strftime
from RedisClient import *
import subprocess


freemem_command = """free | awk 'FNR == 2 {print ($7/1048576)"GB / "($2/1048576)"GB" }'"""
loadavg_command = 'cat /proc/loadavg | cut -d" " -f1-3'
uptime_command = 'cat /proc/uptime | cut -d" " -f1'
diffindex = ['pst', 'prs', 'ftr']
diffindex_full = ['Past', 'Present', 'Future']
banned_userids = ['000000001', '000000002']

mplistener = Listener()
bot = Client(
    bot_name,
    bot_token=bot_token
)
logger = logging.Logger('arcbot')


def pickrandom(mode, filter, count=1, level=''):
    chosen = []
    if mode == 'diff':
        diff = filter
        while len(chosen) < count:
            dup = False
            song = random.choice(songlist)
            for s in chosen:
                if song['id'] == s[3]:
                    dup = True
            if not dup:
                chosen.append([song['title_ja'] if song['title_ja'] else song['title'],
                               diff, song['levels'][diffindex.index(diff)], song['id']])

    elif mode == 'rating':
        diff_list = []
        rating = filter
        for song in songlist:
            if rating in song['levels']:
                diff_list.append(song)
        if len(diff_list) >= count:
            while len(chosen) < count:
                dup = False
                song = random.choice(diff_list)
                for s in chosen:
                    if song['id'] == s[3]:
                        dup = True
                if not dup:
                    chosen.append([song['title_ja'] if song['title_ja'] else song['title'],
                                   diffindex[song['levels'].index(rating)], rating, song['id']])
        else:
            for i in range(0, count):
                dup = False
                song = random.choice(diff_list)
                for s in chosen:
                    if song['id'] == s[3]:
                        dup = True
                if not dup:
                    chosen.append([song['title_ja'] if song['title_ja'] else song['title'],
                                   diffindex[song['levels'].index(rating)], rating, song['id']])
    elif mode == 'pack':
        pack = filter
        packsongs = []
        for s in songlist:
            if s['set'] == pack:
                packsongs.append(s)
        song = random.choice(packsongs)
        chosen.append([song['title_ja'] if song['title_ja'] else song['title'],
                       level.upper(), song['levels'][diffindex.index(level)], song['id']])
    return chosen


def curtime():
    return int(datetime.now().timestamp())


def onException(e):
    print(e)


def allowed_groups():
    decoded = []
    res = RedisClient.smembers('allowed_groups')
    if res:
        for r in res:
            decoded.append(r.decode('utf-8'))
        return decoded
    return []

def onAddmp(title, host, group, members=10):
    ident = str(int(RedisClient.incr('lastid')))
    mplistener.addmp(ident, host, title, members)
    RedisClient.sadd('joined', host)
    RedisClient.hset('joined_mp', host, ident)
    RedisClient.sadd(f'mplist:{group}', str(mplistener.mplist[ident].id))
    RedisClient.sadd(f'mplist:all', str(mplistener.mplist[ident].id))
    RedisClient.hset('mpgroup', ident, group)
    return ident


def onJoinmp(ident, player):
    mplistener.mplist[ident].add_member(player)
    RedisClient.sadd('joined', player)
    RedisClient.hset('joined_mp', player, ident)


def onRemove(mp, user, reason):
    group = findGroupbymp(mp.id)
    username = findArcName(user)
    reasontext = '其他原因'
    if reason == '':
        reasontext = '主动退出'
    if reason == 'invdiffkick':
        reasontext = '错误的谱面难度'
    elif reason == 'invsongkick':
        reasontext = '错误的歌曲'
    RedisClient.srem('joined', user)
    RedisClient.hdel('joined_mp', user)
    delmsg(bot.send_message(chat_id=group, text=f'{findArcName(user)} 已离开房间 {mp.id} "{mp.title}"。原因：{reasontext}'), 30)


def onScoreComplete(mp: Multiplayer):
    round = mp.round_current
    group = findGroupbymp(mp.id)
    ranklist = ''
    emojilist = ['🥇', '🥈', '🥉', ]
    scores = mp.scores[f'round_{round}']
    cursong = mp.cur_song()
    beatmap = f'{findSongName(cursong[0])[0]} {diffindex[cursong[1]].upper()}'
    if len(scores) > 3:
        for i in scores[3:]:
            emojilist.append('🎱')
    for score in scores:
        ranklist += scoreboard_peritem_tempate.format(
            emojilist.pop(0), len(ranklist) + 1, score.name, score.score, score.rating, 
            score.counts[0], score.counts[1], score.counts[2], score.counts[3]
        )
    bot.send_message(chat_id=group, text=f'{mp.id} 号房间 "{mp.title}" 的第 {round} 轮对战结果：\n谱面：{beatmap}\n{ranklist}')


def onClose(mp):
    group = findGroupbymp(mp.id)
    title = mp.title
    creator = findArcName(mp.creator)
    bot.send_message(chat_id=group, text=f'{creator} 创建的房间 {mp.id} - {title} 已关闭。')
    for m in mp.members:
        RedisClient.srem('joined', m)
        RedisClient.hdel('joined_mp', m)

    RedisClient.srem(f'mplist:{group}', mp.id)
    RedisClient.srem(f'mplist:all', mp.id)
    RedisClient.hdel(f'mpgroup', mp.id)


def onHostChange(mp, past, present):
    group = findGroupbymp(mp.id)
    pastname = findArcName(past)
    pstname = findArcName(present)
    delmsg(bot.send_message(chat_id=group, text=f'{mp.id} 号房间 "{mp.title}" 的房主由 {pastname} 更改为 {pstname}。'), 30)

def onStop(mp: Multiplayer):
    group = findGroupbymp(mp.id)
    delmsg(bot.send_message(chat_id=group, text=f'{mp.id} 号房间 {mp.title} 的第 {mp.round_current} 轮对局结束了！请各位耐心等待结果喔~'), 30)


def findmpbyuser(user):
    res = RedisClient.hget('joined_mp', user)
    if res:
        res = res.decode('utf-8')
    return res


def findGroupbymp(ident):
    res = RedisClient.hget('mpgroup', ident)
    if res:
        res = res.decode('utf-8')
    return res


def listmpingroup(group):
    res = RedisClient.smembers(f'mplist:{group}')
    if res:
        decoded = []
        for i in res:
            decoded.append(i.decode('utf-8'))
        return decoded
    return res


def mpinGroup(ident, group):
    return RedisClient.sismember(f'mplist:{group}', str(ident))


def mpexists(ident):
    isexist = RedisClient.sismember('mplist:all', ident)
    if not isexist:
        return False
    try:
        mp = mplistener.mplist[ident]
    except KeyError:
        return False
    if mplistener.mplist[ident].status != 'closed':
        return True
    else:
        return False


def onRmMember(group, ident, player):
    RedisClient.srem('joined', player)
    RedisClient.hdel('joined_mp', player)


def isJoined(player):
    return RedisClient.sismember('joined', player)


def delmsg(msg, timeout=10):
    sleep(timeout)
    try:
        msg.delete()
    except:
        pass


def onBindArc(userid, arccode):
    res = User_exists(arccode)
    if res['status'] == 'ok':
        RedisClient.hset('arcaea', userid, arccode)
        RedisClient.hset('tguser', arccode, userid)
        RedisClient.hset('arcname', res['usercode'], res['username'])
        RedisClient.hset('arcid', res['username'], res['usercode'])
        RedisClient.hset('arcptt', res['usercode'], res['ptt'])
        RedisClient.sadd('boundarc', arccode)
        return res
    else:
        return res

def findArcbyName(name):
    res = RedisClient.hget('arcid', name)
    if res:
        res = res.decode('utf-8')
    return res


def findArcbyUser(tguser):
    res = RedisClient.hget('arcaea', str(tguser))
    if res:
        res = res.decode('utf-8')
    return res


def findArcName(usercode):
    res = RedisClient.hget('arcname', usercode)
    if res:
        res = res.decode('utf-8')
    return res


def findSongName(songid):
    for song in songlist:
        if song['id'] == songid:
            return song['title_ja'] if song['title_ja'] else song['title'], song['levels']


def findSongbyAny(query):
    if query in pull_songalias():
        return getsongbyalias(query)
    elif query in songs_by_id:
        return query
    else:
         return None


def findPackName(packid):
    for pack in packlist:
        if pack['id'] == packid:
            return pack['title']


def set_songalias(song, alias):
    RedisClient.hset('h_songaliases', alias, song)
    RedisClient.sadd('hasaliases', song)
    RedisClient.sadd(f'songaliases:{song}', alias)
    RedisClient.sadd(f'songaliases:all', alias)


def set_packalias(pack, alias):
    RedisClient.hset('h_packaliases', alias, pack)
    RedisClient.sadd('hasaliases', pack)
    RedisClient.sadd('packaliases:all', alias)
    RedisClient.sadd(f'packaliases:{pack}', alias)


def hasalias(id):
    return RedisClient.sismember('hasalias', id)


def pull_packalias(pack=''):
    decoded = []
    if pack == '':
        res = RedisClient.smembers('packaliases:all')
    else:
        res = RedisClient.smembers(f'packaliases:{pack}')
    if res:
        for i in res:
            decoded.append(i.decode('utf-8'))
        return decoded
    return res


def pull_songalias(song=''):
    decoded = []
    if song == '':
        res = RedisClient.smembers('songaliases:all')
    else:
        res = RedisClient.smembers(f'songaliases:{song}')
    if res:
        for i in res:
            decoded.append(i.decode('utf-8'))
        return decoded
    return res


def getpackbyalias(alias=''):
    res = RedisClient.hget('h_packaliases', alias)
    if res:
        res = res.decode('utf-8')
    return res


def getsongbyalias(alias=''):
    res = RedisClient.hget('h_songaliases', alias)
    if res:
        res = res.decode('utf-8')
    return res


@bot.on_message(Filters.group & Filters.new_chat_members, group=0)
def handler_grpcheck(cli, msg):
    if msg.chat.id not in allowed_groups():
        bot.send_message(chat_id=msg.chat.id, text='我没有主人允许不能在这里工作，请联系主人来获得允许吧~')
        bot.send_message(chat_id=bot_master_id, text=f'群组 {msg.chat.title} ({msg.chat.id}) 将我拉入群组。')
        bot.leave_chat(chat_id=msg.chat.id)


@bot.on_message(Filters.command(['aset', f'aset@{bot_name}']))
def handler_aset(cli, msg):
    item = ''
    mode = 'song'
    if len(msg.command) == 1:
        delmsg(msg.reply(help_text_aset))
        delmsg(msg, timeout=1)
        return
    elif len(msg.command) < 3:
        delmsg(msg.reply('信息量过小（'))
        delmsg(msg, timeout=1)
        return
    elif msg.command[1].lower() in songs_by_id:
        item = msg.command[1].lower()
        mode = 'song'
    elif msg.command[1].lower() in packid_list:
        item = msg.command[1].lower()
        mode = 'pack'
    else:
        delmsg(msg.reply('检查下歌曲/曲包 ID 是否正确呢？'))
        delmsg(msg, timeout=0)
        return
    aliases = msg.command[2:]
    name = ''
    pstaliases = ''
    if mode == 'song':
        for alias in aliases:
            set_songalias(item, alias.lower())
        name = findSongName(item)
        pstaliases = ' '.join(pull_songalias(item))
    else:
        for alias in aliases:
            set_packalias(item, alias.lower())
        name = findPackName(item)
        pstaliases = ' '.join(pull_packalias(item))
    delmsg(msg.reply(f'成功增加了 {name} 的别名\n现有的别名：\n{pstaliases}'), 15)
    delmsg(msg, 0)


@bot.on_message(Filters.command(['aget', f'aget@{bot_name}']))
def handler_aget(cli, msg):
    if len(msg.command) != 2:
        delmsg(msg.reply('请指定一个别名（'))
        delmsg(msg)
        return
    ref = ''
    other_aliases = ''
    alias = msg.command[1].lower()
    if RedisClient.sismember('songaliases:all', alias):
        ref = getsongbyalias(alias)
        name = findSongName(ref)[0]
        other_aliases = ' '.join(pull_songalias(ref))
        delmsg(msg.reply(f'它是歌曲 {name} 的别名。它的别名有：\n{other_aliases}'), 15)
    elif RedisClient.sismember('packaliases:all', alias):
        ref = getpackbyalias(alias)
        name = findPackName(ref)
        other_aliases = ' '.join(pull_packalias(ref))
        delmsg(msg.reply(f'它是曲包 {name} 的别名。它的别名有：\n{other_aliases}'), 15)
    delmsg(msg, 0)


@bot.on_message(Filters.group & Filters.command(['mpinfo', f'mpinfo@{bot_name}']))
def handle_mpinfo(cli, msg):
    user = msg.from_user.id
    arcid = findArcbyUser(user)
    if not arcid: 
        delmsg(msg.reply('必须先使用 /bindarc 绑定你的 Arcaea 才可以加入房间（'))
        delmsg(msg)
        return
    if not isJoined(arcid):
        delmsg(msg.reply('你没有加入房间（'))
        delmsg(msg)
        return
    mp = mplistener.mplist[findmpbyuser(arcid)]
    members = ''
    for m in mp.members:
        members += findArcName(m)
    cursong = mp.cur_song()
    delmsg(msg.reply(mpinfo_detailed_template.format(
        mp.id, mp.title, findArcName(mp.creator), findArcName(mp.host), f'{findSongName(cursong[0])[0]} {diffindex[cursong[1]]}',
        mp.round_current, mp.status, members
    )), 20)


@bot.on_message(Filters.group & Filters.command(['newmp', f'newmp@{bot_name}']))
def handler_newmp(client, msg):
    if len(msg.command) < 2:
        delmsg(msg.reply(help_text_newmp))
        return
    user = msg.from_user.id
    if not findArcbyUser(user):
        delmsg(msg.reply('必须先使用 /bindarc 绑定你的 Arcaea 才可以创建房间（'))
        return
    if isJoined(findArcbyUser(user)):
        delmsg(msg.reply('你已经加入了房间，所以不能创建新房间（'))
        return
    title = ' '.join(msg.command[1:])
    group = str(msg.chat.id)
    ident = onAddmp(title=title, group=group, host=findArcbyUser(user))
    mplistener.mplist[ident].set_song('nhelv', 'ftr')
    mp = mplistener.mplist[ident]
    cursong = mp.cur_song()
    info = mpinfo_template.format(
        mp.id, mp.title, findArcName(findArcbyUser(user)), len(mp.members),
        f"{findSongName(cursong[0])[0]} {diffindex[cursong[1]].upper()}",
        mp.status
    )
    mp.regcall('onClose', onClose)
    mp.regcall('onHostChange', onHostChange)
    mp.regcall('onScoreComplete', onScoreComplete)
    mp.regcall('onRemove', onRemove)
    mp.regcall('onStop', onStop)
    msg.reply(f'房间创建成功，ID 为 {ident}\n{info}')


@bot.on_message(Filters.group & Filters.command('dump'))    # Debug function
def handler_dump(cli, msg):
    if findArcbyUser(msg.from_user.id):
        user = findArcbyUser(msg.from_user.id)
        if isJoined(user):
            mp = mplistener.mplist[findmpbyuser(user)]
            if user == mp.creator:
                delmsg(msg.reply(f'Info of {mp.id} :\n`{mp}`'), 20)


@bot.on_message(Filters.group & Filters.command(['leave', f'leave@{bot_name}']))
def handler_leave(cli, msg):
    user = msg.from_user.id
    if not findArcbyUser(user):
        delmsg(msg.reply('必须先使用 /bindarc 绑定你的 Arcaea 才可以进行此操作（'))
        return
    arcid = findArcbyUser(user)
    if not isJoined(arcid):
        delmsg(msg.reply('你没有加入房间啊（'))
        return
    mpid = RedisClient.hget('joined_mp', arcid).decode('utf-8')
    mplistener.mplist[mpid].rm_member(arcid)
    

@bot.on_message(Filters.group & Filters.command(['next', f'next@{bot_name}']))
def handler_next(cli, msg):
    tguser = msg.from_user.id
    arcuser = findArcbyUser(tguser)
    if not arcuser:
        delmsg(msg.reply('你还没有绑定你的 Arcaea 哟~\n快使用 /bindarc 绑定吧~'))
        return
    if not isJoined(arcuser):
        delmsg(msg.reply('你没有加入房间 :('))
        return
    mp = mplistener.mplist[findmpbyuser(arcuser)]
    if arcuser not in [mp.host, mp.creator]:
        delmsg(msg.reply('你不是该房间的房主或创建者 :( '))
        return
    mp.nextround()
    cursong = mp.cur_song()
    delmsg(bot.send_message(chat_id=msg.chat.id, 
                     text=f'房间 {mp.id} "{mp.title}" 的第 {mp.round_current} 轮已经开始了！'
                          f'你们有 {threshold} 秒的时间游玩 {findSongName(cursong[0])[0]} {diffindex[cursong[1]]}。'), 30)


@bot.on_message(Filters.group & Filters.command(['joinmp', f'joinmp@{bot_name}']))
def handler_joinmp(cli, msg):
    group = msg.chat.id
    if len(msg.command) < 2:
        delmsg(msg.reply(help_text_joinmp))
        return
    user = msg.from_user.id
    if not findArcbyUser(user):
        delmsg(msg.reply('必须先使用 /bindarc 绑定你的 Arcaea 才可以加入房间 :P'))
        return
    arcid = findArcbyUser(user)
    if isJoined(arcid):
        delmsg(msg.reply('你已经加入了某个房间 :P'))
        delmsg(msg, 0)
        return
    ident = msg.command[1]
    if not ident.isdigit():
        delmsg(msg.reply('错误的房间 ID :('))
        return
    if not mpexists(ident):
        delmsg(msg.reply('房间不存在或已关闭 :('))
        delmsg(msg, 0)
        return
    if not mpinGroup(ident, group):
        delmsg(msg.reply('该房间不在本群组内 :('))
        delmsg(msg, 0)
        return
    mp = mplistener.mplist[ident]
    if mp.status != 'idle':
        delmsg(msg.reply('该房间正在游戏中，不能加入 :('))
        delmsg(msg, 0)
        return
    onJoinmp(mp.id, arcid)
    msg.reply(f'{findArcName(arcid)} 已加入 {mp.id} 号房间 {mp.title} ，准备好接受挑战了吗？\n现有人数：{len(mp.members)}')
    delmsg(msg, 0)


@bot.on_message(Filters.group & Filters.command(['host', f'host@{bot_name}']))
def handler_host(cli, msg):
    if len(msg.command) < 2:
        delmsg(msg.reply(help_text_chhost))
        return
    user = findArcbyUser(msg.from_user.id)
    if not isJoined(user):
        delmsg(msg.reply('你当前未加入任何房间。:('))
        return
    mpid = findmpbyuser(user)
    mp = mplistener.mplist[mpid]
    if user not in (mp.host, mp.creator):
        delmsg(msg.reply('你不是这个房间的房主或创建者，无法更改房间设置 :('))
        return
    name = msg.command[1]
    user = findArcbyName(name)
    if user:
        if user in mp.members:
            mp.change_host(user)
            return
        else:
            delmsg(msg.reply('该用户不在该房间内 :('))
    else:
        delmsg(msg.reply('未找到该用户 :('))
    delmsg(msg, 0)


@bot.on_message(Filters.group & Filters.command(['song', f'song@{bot_name}']))
def handler_song(cli, msg):
    if len(msg.command) < 2:
        delmsg(msg.reply(help_text_song))
        return
    tguser = msg.from_user.id
    arcuser = findArcbyUser(tguser)
    diff = 'prs'
    song = ''
    if not arcuser:
        delmsg(msg.reply('你还没有绑定你的 Arcaea 哟~\n快使用 /bindarc 绑定吧~'))
        return
    if not isJoined(arcuser):
        delmsg(msg.reply('你没有加入房间 :('))
        return
    mp = mplistener.mplist[findmpbyuser(arcuser)]
    if arcuser not in [mp.host, mp.creator]:
        delmsg(msg.reply('你不是该房间的房主或创建者 :( '))
        return
    song = findSongbyAny(msg.command[1].lower())
    if not song:
        delmsg(msg.reply('找不到该谱面 :('))
        return
    if msg.command[2].lower() in diffindex:
        diff = msg.command[2].lower()
    mp.set_song(song, diff)
    delmsg(msg.reply(f'房间 {mp.id} {mp.title} 的歌曲设置为 {findSongName(song)[0]} {diff.upper()}'))


@bot.on_message(Filters.group & Filters.command(['listmp', f'listmp@{bot_name}']))
def handle_listmp(cli, msg):
    group = msg.chat.id
    mps = listmpingroup(group)
    if not mps:
        delmsg(msg.reply('当前群组内并没有房间 :(\n快使用 /newmp 创建一个吧！'))
        return
    list_text = ''
    if len(mps) == 0:
        delmsg(msg.reply('当前群组内并没有房间 :(\n快使用 /newmp 创建一个吧！'))
        return
    for mp in mps:
        _mp = None
        try:
            _mp = mplistener.mplist[mp]
            if _mp.status == 'closed':
                continue
        except KeyError:
            continue
        list_text += f'ID ：{_mp.id} 创建者：{findArcName(_mp.creator)} 人数：{len(_mp.members)}\n标题：{_mp.title}\n' \
                     f'歌曲：{findSongName(_mp.cur_song()[0])[0]} {diffindex[_mp.cur_song()[1]]}\n\n'
    delmsg(msg.reply(f'本群组内的房间：\n{list_text}'), 60)
    delmsg(msg, 0)


@bot.on_message(Filters.command(['recent', f'recent@{bot_name}']))
def handler_recent(client, message):
    userid = '0'
    if message.reply_to_message is not None:
        if findArcbyUser(message.reply_to_message.from_user.id) is not None:
            userid = findArcbyUser(message.reply_to_message.from_user.id)
        else:
            delmsg(message.reply('这个用户还没有绑定 Arcaea 呢（'))
            delmsg(msg=message, timeout=1)
            return
    elif findArcbyUser(message.from_user.id) is not None:
        userid = findArcbyUser(message.from_user.id)
    else:
        delmsg(message.reply('貌似你还没有绑定到你的 Arcaea 账号哦~\n快使用 /bindarc 绑定你的 Arcaea 账号吧~'))
        delmsg(message, 1)
    try:
        score = Score(userid)
        message.reply(recent_template.format(
            score.name, score.ptt, f'{findSongName(score.song_id)[0]} {diffindex[score.difficulty].upper()}',
            score.const, score.score, score.rating,
            score.counts[0], score.counts[1], score.counts[2], score.counts[3],
            datetime.fromtimestamp(score.playtime / 1000), score.user
        ))
        RedisClient.hdel('arcid', score.name)
        RedisClient.hset('arcname', score.user, score.name)
        RedisClient.hset('arcid', score.name, score.user)
        RedisClient.hset('arcptt', score.user, score.ptt)
    except Exception as e:
        delmsg(message.reply(f'请求数据失败了呢... >_<\n详细信息在下面：\n{e.__traceback__}\n{e}'))
        delmsg(message, 1)
        return


@bot.on_message(Filters.command(['bindarc', f'bindarc@{bot_name}']))
def handler_bindarc(client, message):
    if len(message.command) == 1:
        delmsg(message.reply(help_text_bindarc))
        return
    if len(message.command) > 2:
        message.reply(f'格式错误，你只需要输入 9 位数的 ID 即可')
        return
    try:
        usercode = int(message.command[1], base=10)
    except ValueError as e:
        print(e)
        message.reply(f'格式错误，请输入 9 位数 ID')
        return
    if len(message.command[1]) != 9:
        print(f'Invalid ID {message.command[1]}')
        message.reply('检查一下你的 ID 是不是填错了呢？')
        return
    tmpmsg = message.reply('咱的反射弧太长，在获取信息的过程中请稍候~')
    try:
        res = onBindArc(str(message.from_user.id), message.command[1])
    except Exception as e:
        delmsg(message.reply(f'请求数据失败了呢... >_<\n详细信息在下面：\n{e.__traceback__}\n{e}'))
        delmsg(tmpmsg, 0)
        return

    if res['status'] == 'error':
        print(f'Invalid ID F {message.command[1]}')
        delmsg(message.reply('没有找到相关信息，检查一下你的 ID 是不是填错了呢？'))
        delmsg(tmpmsg, 0)
        return
    else:
        delmsg(message.reply(f"Arcaea {res['usercode']} ({res['username']}) 绑定成功。"))
        delmsg(tmpmsg, 0)
        delmsg(message, 0)


@bot.on_message(Filters.command(['roll', f'roll@{bot_name}']))
def handler_roll(client, message):
    if len(message.command) == 1:
        message.reply(help_text_rand)
        return
    if len(message.command) <= 3:
        picked = []
        mode = 'diff'
        filter = ''
        song_str = ''
        level = ''
        count = 1
        if message.command[1].lower() in ['pst', 'prs', 'ftr']:
            mode = 'diff'
            filter = message.command[1].lower()
        elif message.command[1] in ['1', '2', '3', '4', '5', '6', '7', '8', '9', '9+', '10']:
            mode = 'rating'
            filter = message.command[1]
        elif message.command[1].lower() in packid_list:
            if len(message.command) == 2:
                message.reply('没有指定难度。\n从曲包中抽谱面只能抽一首歌！')
                return
            if message.command[2].lower() not in ['pst', 'prs', 'ftr']:
                message.reply('错误的难度关键字（')
                return
            mode = 'pack'
            filter = message.command[1].lower()
            level = message.command[2].lower()
        elif message.command[1].lower() in pull_packalias():
            if len(message.command) == 2:
                message.reply('没有指定难度。\n从曲包中抽谱面只能抽一首歌！')
                return
            if message.command[2].lower() not in ['pst', 'prs', 'ftr']:
                message.reply('错误的难度关键字（')
                return
            mode = 'pack'
            alias = message.command[1].lower()
            filter = getpackbyalias(alias)
            level = message.command[2].lower()
        try:
            if mode != 'pack':
                count = int(message.command[2])
        except IndexError:
            count = 1
        except ValueError:
            delmsg(message.reply(f'格式错误'))
            return
        if count < 1:
            message.reply('等等，这不是个正确的数哇...')
            return
        if count > 20:
            message.reply('连抽数只能在 20 以内（')
            return
        picked = pickrandom(mode=mode, filter=filter, count=count, level=level)  # Randomly pick a song
        for s in picked:
            song_str += f'`{s[0]} {s[1].upper()}{s[2]}`\n'
        message.reply(f'抽到的歌曲：\n{song_str}')
        return
    else:
        message.reply(f'我从中找不到任何可以用于筛选谱面的条件（')


@bot.on_message(Filters.command(['start', f'start@{bot_name}']))
def handler_start(client, message):
    message.reply('Hi there!')


@bot.on_message(Filters.command(['ping', f'ping@{bot_name}']))
def handler_ping(cli, msg):
    uptime = subprocess.getoutput(uptime_command)
    loadavg = subprocess.getoutput(loadavg_command)
    freemem = subprocess.getoutput(freemem_command)
    uptime = str(timedelta(seconds=int(float(uptime))))
    delmsg(msg.reply(f'I\'m alive.\nYour ID:`{msg.from_user.id}`\nChat ID:{msg.chat.id}\nUptime: `{uptime}`\nLoadavg: `{loadavg}`\nFree: `{freemem}`'), 30)
    delmsg(msg, 0)

@bot.on_message(Filters.command(['howto', f'howto@{bot_name}']))
def handle_howto(client, message):
    message.reply(helptext)


@bot.on_message(Filters.private & Filters.command('listgrps'))
def handler_m_listgrps(cli, msg):
    if msg.from_user.id != bot_master_id:
        return
    msg.reply(f'Allowed groups:\n{allowed_groups()}')


@bot.on_message(Filters.private & Filters.command('addgrp'))
def handler_m_addgrp(cli, msg):
    if msg.from_user.id != bot_master_id:
        return
    if msg.command.__len__() > 1:
        grps = msg.command[1:]
        for grp in grps:
            RedisClient.sadd('allowed_groups', grp)
        msg.reply(f'{grps} was added into allowed groups.')


@bot.on_message(Filters.private & Filters.command('remgrp'))
def handler_m_remgrp(cli, msg):
    if msg.from_user.id != bot_master_id:
        return
    if msg.command.__len__() > 1:
        grps = msg.command[1:]
        for grp in grps:
            RedisClient.srem('allowed_groups', grp)
        msg.reply(f'{grps} was removed from allowed groups.')


def main():
    # Clear database
    RedisClient.delete('mplist*', 'joined', 'joined_mp', 'mpgroup')
    mplistener.start()
    bot.run()


if __name__ == '__main__':
    main()
