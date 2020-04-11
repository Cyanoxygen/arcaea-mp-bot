redis_server = '192.168.1.254'
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
