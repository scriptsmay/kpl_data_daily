# 关于 API 的说明文档

## 获取所有赛季列表数据

- API: http://47.102.210.150:5006/seasons/list?project=KPL
- 描述: 获取赛季数据
- 命名空间: seasons-list
- 参数: 无
- 返回: 所有赛季列表数据，实际返回数据参考： ./archive/seasons-list.json
- 更新频率: 固定，大概3月左右更新一次，只在新赛季启动前才更新

## 查询指定赛季信息

- API: http://47.102.210.150:5006/season/KCC2025
- 描述: 获取赛季信息
- 命名空间: season
- 参数: season_id - 赛季ID, 写在url中
- 示例：http://47.102.210.150:5006/season/{season_id}
- 返回: 赛季信息，实际返回数据参考： ./archive/season.KCC2025.json
- 更新频率: 固定，不更新

## 获取指定赛季的选手统计数据

- API: http://47.103.107.144/openapi/player_stats?season_id=KCC2025
- 描述: 获取选手数据
- 命名空间: player_stats
- 参数: season_id - 赛季ID
- 返回: 选手数据，实际返回数据参考： ./archive/player_stats.KCC2025.json
- 更新频率: 不固定，赛季没结束前，每日更新；赛季结束后，不更新

## 获取指定赛季的所有选手数据

- API: http://47.102.210.150:5035/api/all-player-stats?season=KCC2025
- 描述: 获取指定赛季的所有选手数据
- 命名空间: all-player-stats
- 参数: season - 赛季ID
- 返回: 赛季所有选手数据，实际返回数据参考： ./archive/all-player-stats.KCC2025.json
- 更新频率: 不固定，赛季没结束前，每日更新；赛季结束后，不更新

## 选手英雄胜场简要统计

- API: http://47.102.210.150:5028/api/player-hero-summary/KCC2025
- 描述: 获取指定赛季的选手英雄胜场简要统计
- 命名空间: player-hero-summary
- 参数: season_id - 赛季ID ，写在url中
- 示例：http://47.102.210.150:5028/api/player-hero-summary/{season_id}
- 返回: 赛季所有选手英雄胜场简要统计，实际返回数据参考： ./archive/player-hero-summary.KCC2025.json
- 更新频率: 不固定，赛季没结束前，每日更新；赛季结束后，不更新

## 获取指定赛季的战队人员信息数据

- API: http://47.102.210.150:5006/KPL2026S1/KSG
- 描述: 获取指定赛季的战队人员信息数据
- 命名空间: team-members
- 参数: season_id - 赛季ID ，写在url中; teamname - 战队名称，写在url中
- 示例：http://47.102.210.150:5006/{season_id}/{teamname}
- 返回: 赛季的战队人员信息数据，实际返回数据参考： ./archive/team_members.KPL2026S1.KSG.json
- 更新频率：固定，不更新

## 赛季选手能力数据

- API: http://47.102.210.150:5035/api/player-abilities/KCC2025
- 描述: 指定赛季的所有选手能力数据
- 命名空间: player-abilities
- 参数: season_id - 赛季ID ，写在url中
- 示例：http://47.102.210.150:5035/api/player-abilities/{season_id}
- 返回: 赛季所有选手能力数据，实际返回数据参考： ./archive/player-abilities.KCC2025.json
- 更新频率: 不固定，赛季没结束前，每日更新；赛季结束后，不更新

## 查询无言选手职业生涯数据

- API: http://47.102.210.150:5049/api/player-career?player_name=KSG.%E6%97%A0%E8%A8%80
- 描述: 查询无言选手的职业生涯数据
- 命名空间: player-career-wuyan
- 参数: 固定（我只关注这个选手）
- 返回: 非常多数据的职业生涯数据，实际返回数据参考： ./archive/ksg.wuyan.json
- 更新频率: 固定，每日更新（参与比赛结束后更新）

## 赛事回顾数据

- API: http://47.102.210.150:5022/api/records?season=KCC2025
- 描述: 获取指定赛季的赛事回顾数据
- 命名空间: season-records
- 参数: season - 赛季ID
- 示例：http://47.102.210.150:5022/api/records?season=KCC2025
- 返回: 赛季的赛事回顾数据，实际返回数据参考： ./archive/records.KCC2025.json
- 更新频率: 不固定，赛季没结束前，每日更新；赛季结束后，不更新

## 赛季选手获胜数据统计

- API: http://47.102.210.150:5028/api/player-win-stats/KPL2026S1
- 描述: 获取指定赛季的选手获胜数据统计
- 命名空间: player-win-stats
- 参数: season_id - 赛季ID ，写在url中
- 示例：http://47.102.210.150:5028/api/player-win-stats/{season_id}
- 返回: 赛季所有选手获胜数据统计，实际返回数据参考： ./archive/player-win-stats.KPL2026S1.json
- 更新频率: 不固定，赛季没结束前，每日更新；赛季结束后，不更新

## 赛季选手失败数据统计

- API: http://47.102.210.150:5028/api/player-lose-stats/KPL2026S1
- 描述: 获取指定赛季的选手失败数据统计
- 命名空间: player-lose-stats
- 参数: season_id - 赛季ID ，写在url中
- 示例：http://47.102.210.150:5028/api/player-lose-stats/{season_id}
- 返回: 赛季所有选手失败数据统计，实际返回数据参考： ./archive/player-lose-stats.KPL2026S1.json
- 更新频率: 不固定，赛季没结束前，每日更新；赛季结束后，不更新

## 赛季 获胜时选手亲近度分析：选手组合在获胜情况下的平均亲近度

- API: http://47.102.210.150:5029/api/KPL2026S1/win-affinity-analysis
- 描述: 获取指定赛季的 获胜时选手亲近度分析：选手组合在获胜情况下的平均亲近度
- 命名空间: win-affinity-analysis
- 参数: season_id - 赛季ID ，写在url中
- 示例：http://47.102.210.150:5029/api/{season_id}/win-affinity-analysis
- 返回: 赛季所有选手亲近度分析：选手组合在获胜情况下的平均亲近度，实际返回数据参考： ./archive/win-affinity-analysis.KPL2026S1.json
- 更新频率: 不固定，赛季没结束前，每日更新；赛季结束后，不更新

## 战队选手伤害分布

- API: http://47.102.210.150:5035/api/team-damage-distribution/KPL2026S1/KSG
- 描述: 获取指定赛季的 指定战队 选手伤害分布
- 命名空间: team-damage-distribution
- 参数: season_id - 赛季ID ，写在url中; teamname - 战队名称，写在url中
- 示例：http://47.102.210.150:5035/api/team-damage-distribution/{season_id}/{team_name}
- 返回: 赛季的 战队选手伤害分布，实际返回数据参考： ./archive/team-damage-distribution.KPL2026S1.KSG.json
- 更新频率: 不固定，赛季没结束前，每日更新；赛季结束后，不更新

## 赛季联盟英雄胜率

- API: http://47.102.210.150:5035/api/hero-win-rate/KCC2025?position=%E5%AF%B9%E6%8A%97%E8%B7%AF
- 描述: 获取指定赛季、指定位置的 联盟英雄胜率
- 命名空间: hero-win-rate
- 参数: season_id - 赛季ID ，写在url中; position - 位置（对抗路），写在url中(因为无言的位置就是对抗路)
- 示例：http://47.102.210.150:5035/api/hero-win-rate/{season_id}?position={position}
- 返回: 赛季的 联盟英雄胜率，实际返回数据参考： ./archive/hero-win-rate.KCC2025.json
- 更新频率: 不固定，赛季没结束前，每日更新；赛季结束后，不更新
