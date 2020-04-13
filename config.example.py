redis_server = 'localhost'
redis_port = 6379
bot_token = 'Your_bot_token_here'
bot_name = 'Your_Bot_Username_here'
helptext = '''**用法**
**请在游玩之前将你的 Arcaea 账户与你的 Telegram 进行绑定。**
大致步骤如下：
- 对于房主
`/newmp Title` 以创建一个新房间，房主为创建者，目前暂不支持更改。__第一轮的歌曲默认为 Nhelv FTR__ 。
例： `/newmp Cyanoxygen's Room`
`/set songid pst|prs|ftr` 选择本轮游戏的谱面，需要自行查找歌曲 ID
例： `/set nhelv ftr`
`/start` 开始本轮游戏，如果你在开始之前没有设置谱面，将自动使用上一轮的谱面
例： `/start`

- 对于玩家
`/listmp` 列出群组内已经创建的房间
`/joinmp <ID>` 加入指定 ID 的房间，你不能加入处于游戏中的房间。
`/stats` 可以查看房间的状态，本轮歌曲以及玩家情况。
`/history` 可以查看房间历史记录。

- 结算
4 分钟后机器人会自行查询成绩并公布结果。排名暂时只支持分数排名。
如果在结算时某玩家游玩的谱面与设定不一致，则该玩家会被自动移出，剩余合法成绩继续结算。


- 结束房间
/leave 退出当前加入的房间。
__若房主退出，本房间自动关闭。__房主可以手动关闭房间，此时房间内所有人都会被移出。
'''

help_text_bindarc = '''用法：
`/bindarc <Arcaea user code>`
将你的 Telegram 账户与你的 Arcaea 账户绑定。'''

help_text_rand = '''拿不准打什么歌？那就用这个抽抽看！支持十连哦！
超 大 奖 池 抽 到 手 抽 筋 
注意：按曲包抽歌一次只能抽一首。
用法：
`/roll pst|prs|ftr <连抽数>`
`/roll 1-10 <连抽数>`
`/roll <曲包> pst|prs|ftr`
栗子： `/roll ftr`
栗子： `/roll 9 10`
栗子： `/roll chunithm ftr`
'''

help_text_aset = '''为歌曲添加一个别名。
觉得歌曲/曲包 ID 比较难记？现在可以添加别名啦！
别名也不允许包含空格哟
用法： `/aset <歌曲 ID 或 曲包 ID> 别名1 别名2 ...`
栗子： `/aset grievouslady 病女`
栗子： `/aset yugamu 病女包`'''

help_text_newmp = '''在当前群组新建一个房间。
用法：
/newmp 房间标题
房间的 ID 是加入房间的唯一凭据。
例：
/newmp 出来Arc
'''
help_text_joinmp = '''加入一个当前群组的房间。
用法：
/joinmp 房间 ID
'''

recent_template = '''**{0}** 的最近一次成绩
玩家 PTT：{1}
谱面：{2}
定数：{3}
分数：{4}
游玩表现：{5:.3f}
Pure {6} (+{7})
Far {8}
Lost {9}
上传时间：{10}
Arcaea ID `{11}`
'''

mpinfo_template = '''房间信息 {0} ：
房间标题：{1}
创建者：{2}
当前人数：{3}
当前谱面：{4}
状态：{5}
'''

mpinfo_detailed_template = '''房间信息：
ID      ：{0}
标题    ：{1}
创建者  ：{2}
房主    ：{3}
当前歌曲：{4}
局      ：{5}
玩家    ：{6}
'''

scoreboard_peritem_tempate = '''{0} **第 {1} 名**
{2} 分数：{3} 定数：{4:3f} Pure {5} (+{6}) Far {7} Lost {8}

'''

help_text_chhost = '''设置房间的房主。
`/host <Arcaea Name>`
只有房间的创建者或当前的房主才能设置房主；或者房主退出时自动轮换下一个玩家。

`/host h1r`
'''

help_text_song = '''设置本轮的谱面。
`/song <歌曲 ID 或别名> <难度>`

被你和驴坑了？那么在开始之前先来设置谱面吧。
如果在某一轮开始时并没有设置谱面，那么上一轮的谱面将会被使用。
如果不指定难度，难度默认为 PRS。（笑）
栗子： /song 世征 ftr
'''
