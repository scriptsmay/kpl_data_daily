# KPL 数据标注文档

本文档详细标注了 KPL 数据采集系统中每个命名空间（namespace）的数据文件中各字段的中文含义。

---

## 目录

1. [seasons-list - 赛季列表](#seasons-list---赛季列表)
2. [season - 赛季信息](#season---赛季信息)
3. [player-stats - 选手统计数据](#player-stats---选手统计数据)
4. [all-player-stats - 所有选手数据](#all-player-stats---所有选手数据)
5. [player-hero-summary - 选手英雄胜场统计](#player-hero-summary---选手英雄胜场统计)
6. [team-members - 战队人员信息](#team-members---战队人员信息)
7. [player-abilities - 选手能力数据](#player-abilities---选手能力数据)
8. [player-career-wuyan - 选手职业生涯数据](#player-career-wuyan---选手职业生涯数据)
9. [season-records - 赛事回顾数据](#season-records---赛事回顾数据)
10. [player-win-stats - 选手获胜数据统计](#player-win-stats---选手获胜数据统计)
11. [player-lose-stats - 选手失败数据统计](#player-lose-stats---选手失败数据统计)
12. [win-affinity-analysis - 获胜时选手亲近度分析](#win-affinity-analysis---获胜时选手亲近度分析)
13. [team-damage-distribution - 战队选手伤害分布](#team-damage-distribution---战队选手伤害分布)
14. [hero-win-rate - 联盟英雄胜率](#hero-win-rate---联盟英雄胜率)

---

## seasons-list - 赛季列表

**API**: `/seasons/list?project=KPL`  
**命名空间**: `seasons-list`  
**更新频率**: 固定，约 3 月更新一次（新赛季启动前）

### 数据结构

```json
[
  {
    "tournament_id": "KPL2026S1",
    "tournament_name": "KPL2026 春季赛",
    "project": "KPL",
    "season_type": "联赛",
    "is_latest": 1
  }
]
```

### 字段说明

| 字段名            | 类型    | 中文含义 | 说明                                   |
| ----------------- | ------- | -------- | -------------------------------------- |
| `tournament_id`   | string  | 赛事 ID  | 赛季的唯一标识符，如 `KPL2026S1`       |
| `tournament_name` | string  | 赛事名称 | 赛季的完整中文名称                     |
| `project`         | string  | 项目类型 | 赛事所属项目，固定为 `KPL`             |
| `season_type`     | string  | 赛季类型 | `联赛` 或 `杯赛`                       |
| `is_latest`       | integer | 是否最新 | `1` 表示当前最新赛季，`0` 表示历史赛季 |

---

## season - 赛季信息

**API**: `/season/{season_id}`  
**命名空间**: `season`  
**更新频率**: 固定，不更新

### 数据结构

```json
{
  "tournament_id": "KPL2026S1",
  "tournament_name": "KPL2026 春季赛",
  "project": "KPL",
  "season_type": "联赛",
  "is_latest": 1,
  "start_date": "2026-01-13",
  "end_date": "2026-04-12"
}
```

### 字段说明

| 字段名            | 类型    | 中文含义 | 说明                            |
| ----------------- | ------- | -------- | ------------------------------- |
| `tournament_id`   | string  | 赛事 ID  | 赛季的唯一标识符                |
| `tournament_name` | string  | 赛事名称 | 赛季的完整中文名称              |
| `project`         | string  | 项目类型 | 赛事所属项目                    |
| `season_type`     | string  | 赛季类型 | `联赛` 或 `杯赛`                |
| `is_latest`       | integer | 是否最新 | `1` 表示当前最新赛季            |
| `start_date`      | string  | 开始日期 | 赛季开始日期，格式 `YYYY-MM-DD` |
| `end_date`        | string  | 结束日期 | 赛季结束日期，格式 `YYYY-MM-DD` |

---

## player-stats - 选手统计数据

**API**: `/openapi/player_stats?season_id={season_id}`  
**命名空间**: `player-stats`  
**更新频率**: 不固定（赛季期间每日更新，赛季结束后不更新）

### 数据结构（部分字段）

```json
{
  "msg": "successful",
  "code": 200,
  "data": {
    "sys_id": 2183,
    "playerName": "无言",
    "displayName": "KSG.无言",
    "realName": "赵昊宇",
    "teamName": "KSG",
    "TeamId": "KPL2026S1_ytg",
    "position": "对抗路",
    "SeasonID": "KPL2026S1",
    "avgtenmingold": 6490.02,
    "matchCount": 64,
    "total_participate_kill": 107,
    "total_participate_death": 104,
    "total_participate_assist": 246
  }
}
```

### 字段说明

#### 基础信息

| 字段名        | 类型    | 中文含义 | 说明                                               |
| ------------- | ------- | -------- | -------------------------------------------------- |
| `sys_id`      | integer | 系统 ID  | 选手在系统中的唯一标识                             |
| `playerName`  | string  | 选手名   | 选手的游戏 ID（不含战队前缀）                      |
| `displayName` | string  | 显示名称 | 选手的完整显示名（含战队前缀）                     |
| `realName`    | string  | 真实姓名 | 选手的真实姓名                                     |
| `teamName`    | string  | 战队名称 | 所属战队简称                                       |
| `TeamId`      | string  | 战队 ID  | 战队在系统中的唯一标识                             |
| `position`    | string  | 位置     | 选手在战队中的位置（对抗路/打野/中路/发育路/游走） |
| `SeasonID`    | string  | 赛季 ID  | 当前统计的赛季标识                                 |

#### 经济数据

| 字段名          | 类型  | 中文含义        | 说明                             |
| --------------- | ----- | --------------- | -------------------------------- |
| `avgtenmingold` | float | 10 分钟平均经济 | 比赛进行到 10 分钟时的平均经济值 |

#### 团战数据 - 前期

| 字段名                                | 类型    | 中文含义             | 说明                                 |
| ------------------------------------- | ------- | -------------------- | ------------------------------------ |
| `earlyGame_big_fight_num`             | integer | 前期大型团战次数     | 游戏前期参与的大型团战总次数         |
| `earlyGame_big_fight_wins`            | integer | 前期大型团战胜利次数 | 游戏前期赢得的大型团战次数           |
| `earlyGame_big_fight_draws`           | integer | 前期大型团战平局次数 | 游戏前期平局的大型团战次数           |
| `earlyGame_big_fight_winRate`         | float   | 前期大型团战胜率     | 前期大型团团的胜率（0-1 之间的小数） |
| `earlyGame_total_big_fight_damage`    | integer | 前期大型团战总伤害   | 前期大型团战中造成的总伤害           |
| `earlyGame_total_fight_take_damage`   | integer | 前期团战承受总伤害   | 前期团战中承受的总伤害               |
| `earlyGame_bigFightavgDamagePerFight` | float   | 前期大型团战平均伤害 | 前期每次大型团战的平均伤害           |

#### 团战数据 - 中期

| 字段名                              | 类型    | 中文含义             | 说明                         |
| ----------------------------------- | ------- | -------------------- | ---------------------------- |
| `midGame_big_fight_num`             | integer | 中期大型团战次数     | 游戏中期参与的大型团战总次数 |
| `midGame_big_fight_wins`            | integer | 中期大型团战胜利次数 | 游戏中期赢得的大型团战次数   |
| `midGame_big_fight_draws`           | integer | 中期大型团战平局次数 | 游戏中期平局的大型团战次数   |
| `midGame_big_fight_winRate`         | float   | 中期大型团战胜率     | 中期大型团团的胜率           |
| `midGame_total_big_fight_damage`    | integer | 中期大型团战总伤害   | 中期大型团战中造成的总伤害   |
| `midGame_total_fight_take_damage`   | integer | 中期团战承受总伤害   | 中期团战中承受的总伤害       |
| `midGame_bigFightavgDamagePerFight` | float   | 中期大型团战平均伤害 | 中期每次大型团战的平均伤害   |

#### 团战数据 - 后期

| 字段名                               | 类型    | 中文含义             | 说明                         |
| ------------------------------------ | ------- | -------------------- | ---------------------------- |
| `lateGame_big_fight_num`             | integer | 后期大型团战次数     | 游戏后期参与的大型团战总次数 |
| `lateGame_big_fight_wins`            | integer | 后期大型团战胜利次数 | 游戏后期赢得的大型团战次数   |
| `lateGame_big_fight_draws`           | integer | 后期大型团战平局次数 | 游戏后期平局的大型团战次数   |
| `lateGame_big_fight_winRate`         | float   | 后期大型团战胜率     | 后期大型团团的胜率           |
| `lateGame_total_big_fight_damage`    | integer | 后期大型团战总伤害   | 后期大型团战中造成的总伤害   |
| `lateGame_total_fight_take_damage`   | integer | 后期团战承受总伤害   | 后期团战中承受的总伤害       |
| `lateGame_bigFightavgDamagePerFight` | float   | 后期大型团战平均伤害 | 后期每次大型团战的平均伤害   |

#### 团战伤害数据

| 字段名                    | 类型    | 中文含义             | 说明                                  |
| ------------------------- | ------- | -------------------- | ------------------------------------- |
| `bigFightMaxdamage`       | integer | 大型团战最大伤害     | 单场大型团战中造成的最高伤害          |
| `bigFighttMaxblastdamage` | integer | 大型团战最大爆发伤害 | 单场大型团战中的最高爆发伤害          |
| `bigFightAvgblastdamage`  | float   | 大型团战平均爆发伤害 | 大型团战中每次爆发的平均伤害          |
| `bigFightMaxToCDamage`    | integer | 大型团战对C伤害      | 单场大型团战中对对方C位造成的最高伤害 |
| `bigFightAvgToCDamage`    | float   | 大型团战平均对C伤害  | 大型团战中对对方C位造成的平均伤害     |

#### 控制与支援数据

| 字段名            | 类型    | 中文含义         | 说明                         |
| ----------------- | ------- | ---------------- | ---------------------------- |
| `maxControlTime`  | integer | 最大控制时间     | 单场最高控制时长（单位：秒） |
| `avgControlTime`  | float   | 平均控制时间     | 平均每场控制时长（单位：秒） |
| `avgGankNum`      | float   | 平均 Gank 次数   | 平均每场 Gank 次数           |
| `avgGankKill`     | float   | 平均 Gank 击杀   | 平均每场 Gank 成功击杀数     |
| `maxGankKillRate` | float   | 最大 Gank 击杀率 | 最高 Gank 击杀率             |
| `maxIntrudeTime`  | integer | 最大入侵时间     | 单场最长入侵时长（单位：秒） |
| `avgIntrudeTime`  | float   | 平均入侵时间     | 平均每场入侵时长（单位：秒） |
| `totalDropNum`    | integer | 总掉点次数       | 总计掉点（失误）次数         |

#### 团战参与数据

| 字段名                                | 类型    | 中文含义               | 说明                               |
| ------------------------------------- | ------- | ---------------------- | ---------------------------------- |
| `bigFightTotalKillCNum`               | integer | 大型团战总击杀数       | 大型团战中的总击杀数               |
| `matchCount`                          | integer | 比赛场数               | 参与的比赛总场数                   |
| `total_river_time`                    | integer | 总河道时间             | 在河道区域的总停留时间（单位：秒） |
| `avg_river_rate`                      | float   | 平均河道率             | 平均河道视野占有率                 |
| `total_min_10_lind_kill`              | integer | 10 分钟线杀总数        | 10 分钟内的线杀总次数              |
| `avg_min_10_lind_kill_rate`           | float   | 10 分钟线杀平均率      | 10 分钟内线杀的平均比率            |
| `total_open_fight_num`                | integer | 总开团次数             | 主动发起团战的总次数               |
| `total_open_fight_success_num`        | integer | 总开团成功次数         | 主动开团成功的次数                 |
| `total_open_big_fight_num`            | integer | 总开大型团战次数       | 主动发起大型团战的次数             |
| `total_open_big_fight_success_num`    | integer | 总开大型团战成功次数   | 主动发起大型团战成功的次数         |
| `total_support_num`                   | integer | 总支援次数             | 支援队友的总次数                   |
| `total_support_success_num`           | integer | 总支援成功次数         | 支援成功的次数                     |
| `total_support_big_fight_num`         | integer | 总支援大型团战次数     | 支援大型团战的次数                 |
| `total_support_big_fight_success_num` | integer | 总支援大型团战成功次数 | 支援大型团战成功的次数             |
| `total_support_kill`                  | integer | 总支援击杀             | 支援过程中获得的击杀数             |

#### 综合团战数据

| 字段名                          | 类型    | 中文含义           | 说明                             |
| ------------------------------- | ------- | ------------------ | -------------------------------- |
| `total_participate_num`         | integer | 总参团数           | 参与团战的总次数                 |
| `total_big_fight_num`           | integer | 总大型团战数       | 参与大型团战的总次数             |
| `total_team_fight_win`          | integer | 团队战斗胜利数     | 团队战斗胜利的总次数             |
| `total_team_fight_draw`         | integer | 团队战斗平局数     | 团队战斗平局的总次数             |
| `total_team_fight_winrate`      | float   | 团队战斗胜率       | 团队战斗的胜率                   |
| `total_participate_win`         | integer | 参团胜利数         | 参团并获胜的次数                 |
| `total_participate_draw`        | integer | 参团平局数         | 参团并平局的次数                 |
| `total_participate_winrate`     | float   | 参团胜率           | 参团时的胜率                     |
| `total_fight_win`               | integer | 战斗胜利数         | 参与战斗胜利的总次数             |
| `total_fight_draw`              | integer | 战斗平局数         | 参与战斗平局的总次数             |
| `total_fight_winrate`           | float   | 战斗胜率           | 参与战斗的胜率                   |
| `total_team_fight_num`          | integer | 总团队战斗数       | 参与团队战斗的总次数             |
| `total_fight_team_par_rate`     | float   | 战斗团队参与率     | 参与团队战斗的比率               |
| `total_team_big_fight_num`      | integer | 总团队大型团战数   | 参与团队大型团战的总次数         |
| `total_team_big_fight_par_rate` | float   | 团队大型团战参与率 | 参与团队大型团战的比率           |
| `avg_fight_death_avg_rank`      | float   | 战斗死亡平均排名   | 战斗中死亡次数的平均排名（推测） |

#### 伤害与承伤数据

| 字段名                             | 类型    | 中文含义                    | 说明                                |
| ---------------------------------- | ------- | --------------------------- | ----------------------------------- |
| `max_big_fight_to_C_lethal_damage` | integer | 大型团战对 C 位最大致命伤害 | 大型团战中对 C 位造成的最大致命伤害 |
| `avg_big_fight_to_C_lethal_damage` | float   | 大型团战对 C 位平均致命伤害 | 大型团战中对 C 位造成的平均致命伤害 |
| `total_participate_kill`           | integer | 参团总击杀                  | 参团时的总击杀数                    |
| `total_participate_death`          | integer | 参团总死亡                  | 参团时的总死亡数                    |
| `total_participate_assist`         | integer | 参团总助攻                  | 参团时的总助攻数                    |
| `total_participate_healCnt`        | integer | 参团总治疗量                | 参团时的总治疗量                    |
| `total_participate_damage`         | integer | 参团总伤害                  | 参团时造成的总伤害                  |
| `total_participate_take_damage`    | integer | 参团总承伤                  | 参团时承受的总伤害                  |
| `total_big_fight_kill`             | integer | 大型团战总击杀              | 大型团战中的总击杀数                |
| `total_big_fight_death`            | integer | 大型团战总死亡              | 大型团战中的总死亡数                |
| `total_big_fight_assist`           | integer | 大型团战总助攻              | 大型团战中的总助攻数                |
| `total_big_fight_damage`           | integer | 大型团战总伤害              | 大型团战中造成的总伤害              |
| `total_big_fight_take_damage`      | integer | 大型团战总承伤              | 大型团战中承受的总伤害              |
| `total_big_fight_healCnt`          | integer | 大型团战总治疗量            | 大型团战中的总治疗量                |

#### 单杀与伤害效率

| 字段名                             | 类型    | 中文含义             | 说明                             |
| ---------------------------------- | ------- | -------------------- | -------------------------------- |
| `total_single_kill`                | integer | 总单杀数             | 1v1 单杀的总次数                 |
| `total_big_fight_time`             | integer | 大型团战总时间       | 大型团战的总持续时间（单位：秒） |
| `big_fight_per_second_damage`      | float   | 大型团战每秒伤害     | 大型团战中每秒造成的伤害（DPS）  |
| `big_fight_damage_percentage`      | float   | 大型团战伤害占比     | 大型团战中伤害占团队总伤害的比例 |
| `big_fight_per_second_take_damage` | float   | 大型团战每秒承伤     | 大型团战中每秒承受的伤害         |
| `big_fight_take_damage_percentage` | float   | 大型团战承伤占比     | 大型团战中承伤占团队总承伤的比例 |
| `avg_big_fight_gold_income`        | float   | 大型团战平均经济收益 | 大型团战中的平均经济收益         |
| `avg_big_fight_exp_income`         | float   | 大型团战平均经验收益 | 大型团战中的平均经验收益         |
| `big_fight_kill_per_match`         | float   | 大型团战场均击杀     | 每场大型团战的平均击杀数         |
| `big_fight_death_per_match`        | float   | 大型团战场均死亡     | 每场大型团战的平均死亡数         |
| `big_fight_assist_per_match`       | float   | 大型团战场均助攻     | 每场大型团战的平均助攻数         |
| `avg_big_fight_damage`             | float   | 大型团战平均伤害     | 大型团战中的平均伤害             |

#### 参团率数据

| 字段名                               | 类型    | 中文含义         | 说明                         |
| ------------------------------------ | ------- | ---------------- | ---------------------------- |
| `total_participate_time`             | integer | 参团总时间       | 参与团战的总时间（单位：秒） |
| `participate_per_second_damage`      | float   | 参团每秒伤害     | 参团时每秒造成的伤害         |
| `participate_damage_percentage`      | float   | 参团伤害占比     | 参团时伤害占团队总伤害的比例 |
| `participate_per_second_take_damage` | float   | 参团每秒承伤     | 参团时每秒承受的伤害         |
| `participate_take_damage_percentage` | float   | 参团承伤占比     | 参团时承伤占团队总承伤的比例 |
| `avg_participate_gold_income`        | float   | 参团平均经济收益 | 参团时的平均经济收益         |
| `avg_participate_exp_income`         | float   | 参团平均经验收益 | 参团时的平均经验收益         |
| `participate_kill_per_match`         | float   | 参团场均击杀     | 参团时的场均击杀数           |
| `participate_death_per_match`        | float   | 参团场均死亡     | 参团时的场均死亡数           |
| `participate_assist_per_match`       | float   | 参团场均助攻     | 参团时的场均助攻数           |
| `participate_death_rate`             | float   | 参团死亡率       | 参团时的死亡率               |

#### 战斗数据

| 字段名                         | 类型    | 中文含义         | 说明                         |
| ------------------------------ | ------- | ---------------- | ---------------------------- |
| `total_fight_time`             | integer | 战斗总时间       | 参与战斗的总时间（单位：秒） |
| `total_fight_num`              | integer | 战斗总次数       | 参与战斗的总次数             |
| `total_fight_team_num`         | integer | 战斗团队次数     | 参与团队战斗的次数           |
| `fight_participate_rate`       | float   | 战斗参与率       | 参与战斗的比率               |
| `fight_per_second_damage`      | float   | 战斗每秒伤害     | 战斗中每秒造成的伤害         |
| `fight_damage_percentage`      | float   | 战斗伤害占比     | 战斗中伤害占团队总伤害的比例 |
| `fight_per_second_take_damage` | float   | 战斗每秒承伤     | 战斗中每秒承受的伤害         |
| `fight_take_damage_percentage` | float   | 战斗承伤占比     | 战斗中承伤占团队总承伤的比例 |
| `avg_fight_gold_income`        | float   | 战斗平均经济收益 | 战斗中的平均经济收益         |
| `avg_fight_exp_income`         | float   | 战斗平均经验收益 | 战斗中的平均经验收益         |
| `total_fight_kill`             | integer | 战斗总击杀       | 战斗中的总击杀数             |
| `total_fight_death`            | integer | 战斗总死亡       | 战斗中的总死亡数             |
| `total_fight_assist`           | integer | 战斗总助攻       | 战斗中的总助攻数             |
| `total_fight_damage`           | integer | 战斗总伤害       | 战斗中造成的总伤害           |
| `total_fight_take_damage`      | integer | 战斗总承伤       | 战斗中承受的总伤害           |
| `total_fight_healCnt`          | integer | 战斗总治疗量     | 战斗中的总治疗量             |
| `fight_kill_per_match`         | float   | 战斗场均击杀     | 战斗中的场均击杀数           |
| `fight_death_per_match`        | float   | 战斗场均死亡     | 战斗中的场均死亡数           |
| `fight_assist_per_match`       | float   | 战斗场均助攻     | 战斗中的场均助攻数           |

#### 资源控制数据

| 字段名                               | 类型  | 中文含义            | 说明                              |
| ------------------------------------ | ----- | ------------------- | --------------------------------- |
| `steal_monster_per_match`            | float | 场均抢野数          | 每场抢夺野怪的平均次数            |
| `steal_monster_rate_per_match`       | float | 场均抢野率          | 每场抢夺野怪的平均比率            |
| `avg_position_ten_min_gold_distinct` | float | 10 分钟经济差平均值 | 10 分钟时与对位选手的经济差平均值 |
| `avg_ten_min_exp`                    | float | 10 分钟平均经验     | 10 分钟时的平均经验值             |
| `avg_position_ten_min_exp_distinct`  | float | 10 分钟经验差平均值 | 10 分钟时与对位选手的经验差平均值 |

#### 10 分钟数据

| 字段名                              | 类型  | 中文含义              | 说明                            |
| ----------------------------------- | ----- | --------------------- | ------------------------------- |
| `avg_ten_min_kill`                  | float | 10 分钟平均击杀       | 10 分钟时的平均击杀数           |
| `avg_ten_min_assist`                | float | 10 分钟平均助攻       | 10 分钟时的平均助攻数           |
| `avg_ten_min_participate_kill`      | float | 10 分钟平均参团击杀   | 10 分钟时参与击杀的平均数       |
| `avg_ten_min_participate_kill_rate` | float | 10 分钟平均参团击杀率 | 10 分钟时参团击杀的平均比率     |
| `avg_ten_min_death`                 | float | 10 分钟平均死亡       | 10 分钟时的平均死亡数           |
| `avg_ten_min_recover`               | float | 10 分钟平均重生次数   | 10 分钟时的平均重生次数（推测） |
| `avg_six_min_participate_rate`      | float | 6 分钟平均参团率      | 6 分钟时的平均参团率            |
| `avg_ten_min_participate_rate`      | float | 10 分钟平均参团率     | 10 分钟时的平均参团率           |

#### 控制数据

| 字段名                            | 类型    | 中文含义              | 说明                         |
| --------------------------------- | ------- | --------------------- | ---------------------------- |
| `per_five_min_skill_control_time` | float   | 每 5 分钟技能控制时间 | 每 5 分钟技能控制的平均时长  |
| `total_control_time`              | integer | 总控制时间            | 技能控制的总时长（单位：秒） |

---

## all-player-stats - 所有选手数据

**API**: `/api/all-player-stats?season={season_id}`  
**命名空间**: `all-player-stats`  
**更新频率**: 不固定（赛季期间每日更新，赛季结束后不更新）

### 数据结构

```json
{
  "code": 200,
  "data": {
    "avg_assists": 3.97,
    "avg_assists_rank": 7,
    "avg_kills": 1.7,
    "avg_kills_rank": 8,
    "avg_deaths": 1.69,
    "avg_deaths_rank": 10,
    "kda_ratio": 3.36,
    "kda_ratio_rank": 7,
    "win_rate": "59.4%",
    "win_rate_rank": 5,
    "damage_share": "18.2%",
    "damage_taken_share": "22.9%",
    "economy_share": "21.0%",
    "player_name": "KSG.无言",
    "player_position": "对抗路",
    "team_name": "KSG",
    "total_matches": 64.0
  },
  "total_players": 114
}
```

### 字段说明

#### 基础信息

| 字段名               | 类型        | 中文含义       | 说明                           |
| -------------------- | ----------- | -------------- | ------------------------------ |
| `player_name`        | string      | 选手名称       | 选手的完整显示名（含战队前缀） |
| `player_position`    | string      | 选手位置       | 选手在战队中的位置             |
| `player_unique_id`   | string      | 选手唯一 ID    | 选手在联盟中的唯一标识         |
| `team_name`          | string      | 战队名称       | 所属战队简称                   |
| `season`             | string      | 赛季 ID        | 当前统计的赛季标识             |
| `stage_name`         | null/string | 阶段名称       | 比赛阶段名称（可能为空）       |
| `total_matches`      | float       | 总比赛场数     | 参与的比赛总场数               |
| `total_matches_rank` | integer     | 总比赛场数排名 | 在场次数上的联盟排名           |

#### KDA 数据

| 字段名                        | 类型    | 中文含义       | 说明                                   |
| ----------------------------- | ------- | -------------- | -------------------------------------- |
| `avg_kills`                   | float   | 场均击杀       | 平均每场击杀数                         |
| `avg_kills_rank`              | integer | 场均击杀排名   | 在场均击杀上的联盟排名                 |
| `avg_deaths`                  | float   | 场均死亡       | 平均每场死亡数                         |
| `avg_deaths_rank`             | integer | 场均死亡排名   | 在场均死亡上的联盟排名                 |
| `avg_assists`                 | float   | 场均助攻       | 平均每场助攻数                         |
| `avg_assists_rank`            | integer | 场均助攻排名   | 在场均助攻上的联盟排名                 |
| `kda_ratio`                   | float   | KDA 比率       | 击杀死亡助攻比率（(击杀 + 助攻)/死亡） |
| `kda_ratio_rank`              | integer | KDA 比率排名   | 在 KDA 上的联盟排名                    |
| `avg_kill_participation`      | string  | 平均参团率     | 参与击杀的比率（百分比字符串）         |
| `avg_kill_participation_rank` | integer | 平均参团率排名 | 在参团率上的联盟排名                   |

#### 胜率数据

| 字段名          | 类型    | 中文含义 | 说明                     |
| --------------- | ------- | -------- | ------------------------ |
| `win_rate`      | string  | 胜率     | 比赛胜率（百分比字符串） |
| `win_rate_rank` | integer | 胜率排名 | 在胜率上的联盟排名       |

#### 伤害数据

| 字段名                         | 类型    | 中文含义         | 说明                       |
| ------------------------------ | ------- | ---------------- | -------------------------- |
| `damage_share`                 | string  | 伤害占比         | 伤害占团队总伤害的比例     |
| `damage_share_rank`            | integer | 伤害占比排名     | 在伤害占比上的联盟排名     |
| `damage_taken_share`           | string  | 承伤占比         | 承伤占团队总承伤的比例     |
| `damage_taken_share_rank`      | integer | 承伤占比排名     | 在承伤占比上的联盟排名     |
| `damage_per_minute`            | float   | 每分钟伤害       | 每分钟造成的平均伤害       |
| `damage_per_minute_rank`       | integer | 每分钟伤害排名   | 在每分钟伤害上的联盟排名   |
| `damage_taken_per_minute`      | float   | 每分钟承伤       | 每分钟承受的平均伤害       |
| `damage_taken_per_minute_rank` | integer | 每分钟承伤排名   | 在每分钟承伤上的联盟排名   |
| `damage_per_death`             | float   | 每次死亡伤害     | 每次死亡前造成的平均伤害   |
| `damage_per_death_rank`        | integer | 每次死亡伤害排名 | 在每次死亡伤害上的联盟排名 |

#### 经济数据

| 字段名                    | 类型    | 中文含义       | 说明                         |
| ------------------------- | ------- | -------------- | ---------------------------- |
| `economy_share`           | string  | 经济占比       | 经济占团队总经济的比例       |
| `economy_share_rank`      | integer | 经济占比排名   | 在经济占比上的联盟排名       |
| `economy_per_minute`      | float   | 每分钟经济     | 每分钟获得的平均经济         |
| `economy_per_minute_rank` | integer | 每分钟经济排名 | 在每分钟经济上的联盟排名     |
| `economy_to_damage`       | float   | 经济转化率     | 经济转化为伤害的效率         |
| `economy_to_damage_rank`  | integer | 经济转化率排名 | 在经济转化率上的联盟排名     |
| `economy_to_tank`         | float   | 经济承伤比     | 经济转化为承伤的效率（推测） |
| `economy_to_tank_rank`    | integer | 经济承伤比排名 | 在经济承伤比上的联盟排名     |

#### 经济来源细分

| 字段名                          | 类型  | 中文含义         | 说明                     |
| ------------------------------- | ----- | ---------------- | ------------------------ |
| `avg_economy_from_soldier`      | float | 平均小兵经济     | 从小兵获得的平均经济     |
| `avg_economy_from_hero`         | float | 平均英雄经济     | 从击杀英雄获得的平均经济 |
| `avg_economy_from_jungle`       | float | 平均野区经济     | 从野区获得的平均经济     |
| `avg_economy_from_self_jungle`  | float | 平均自家野区经济 | 从自家野区获得的平均经济 |
| `avg_economy_from_enemy_jungle` | float | 平均敌方野区经济 | 从敌方野区获得的平均经济 |
| `avg_economy_from_top_lane`     | float | 平均对抗路经济   | 从对抗路线获得的平均经济 |
| `avg_economy_from_mid_lane`     | float | 平均中路经济     | 从中路线获得的平均经济   |
| `avg_economy_from_adc_lane`     | float | 平均发育路经济   | 从发育路线获得的平均经济 |

#### 经济来源占比

| 字段名                                 | 类型  | 中文含义         | 说明                             |
| -------------------------------------- | ----- | ---------------- | -------------------------------- |
| `economy_from_soldier_percentage`      | float | 小兵经济占比     | 小兵经济占总经济的百分比         |
| `economy_from_hero_percentage`         | float | 英雄经济占比     | 击杀英雄获得经济占总经济的百分比 |
| `economy_from_jungle_percentage`       | float | 野区经济占比     | 野区经济占总经济的百分比         |
| `economy_from_self_jungle_percentage`  | float | 自家野区经济占比 | 自家野区经济占总经济的百分比     |
| `economy_from_enemy_jungle_percentage` | float | 敌方野区经济占比 | 敌方野区经济占总经济的百分比     |
| `economy_from_top_lane_percentage`     | float | 对抗路经济占比   | 对抗路线经济占总经济的百分比     |
| `economy_from_mid_lane_percentage`     | float | 中路经济占比     | 中路线经济占总经济的百分比       |
| `economy_from_adc_lane_percentage`     | float | 发育路经济占比   | 发育路线经济占总经济的百分比     |

#### 伤害目标分布

| 字段名                         | 类型  | 中文含义         | 说明                       |
| ------------------------------ | ----- | ---------------- | -------------------------- |
| `damage_to_top_percentage`     | float | 对对抗路伤害占比 | 对对抗路选手造成的伤害占比 |
| `damage_to_jungle_percentage`  | float | 对打野伤害占比   | 对打野选手造成的伤害占比   |
| `damage_to_mid_percentage`     | float | 对中路伤害占比   | 对中路选手造成的伤害占比   |
| `damage_to_adc_percentage`     | float | 对发育路伤害占比 | 对发育路选手造成的伤害占比 |
| `damage_to_support_percentage` | float | 对游走伤害占比   | 对游走选手造成的伤害占比   |

#### 野区资源控制

| 字段名                  | 类型    | 中文含义           | 说明                       |
| ----------------------- | ------- | ------------------ | -------------------------- |
| `avg_jungle_kills`      | float   | 场均刷野数         | 平均每场刷野怪的数量       |
| `avg_jungle_kills_rank` | integer | 场均刷野数排名     | 在场均刷野数上的联盟排名   |
| `jungle_share`          | string  | 刷野占比           | 刷野占团队总刷野的比例     |
| `jungle_share_rank`     | integer | 刷野占比排名       | 在刷野占比上的联盟排名     |
| `avg_blue_buff`         | float   | 平均蓝 buff 数     | 平均每场获得的蓝 buff 数量 |
| `avg_blue_buff_rank`    | integer | 平均蓝 buff 数排名 | 在蓝 buff 数上的联盟排名   |
| `avg_red_buff`          | float   | 平均红 buff 数     | 平均每场获得的红 buff 数量 |
| `avg_red_buff_rank`     | integer | 平均红 buff 数排名 | 在红 buff 数上的联盟排名   |
| `total_blue_buff`       | float   | 总蓝 buff 数       | 获得的蓝 buff 总数         |
| `total_blue_buff_rank`  | integer | 总蓝 buff 数排名   | 在总蓝 buff 数上的联盟排名 |
| `total_red_buff`        | float   | 总红 buff 数       | 获得的红 buff 总数         |
| `total_red_buff_rank`   | integer | 总红 buff 数排名   | 在总红 buff 数上的联盟排名 |

#### 中立资源控制

| 字段名                               | 类型    | 中文含义             | 说明                           |
| ------------------------------------ | ------- | -------------------- | ------------------------------ |
| `master_control_rate`                | string  | 主宰控制率           | 对主宰的控制率                 |
| `master_control_rate_rank`           | integer | 主宰控制率排名       | 在主宰控制率上的联盟排名       |
| `dark_master_control_rate`           | string  | 暗影主宰控制率       | 对暗影主宰的控制率             |
| `dark_master_control_rate_rank`      | integer | 暗影主宰控制率排名   | 在暗影主宰控制率上的联盟排名   |
| `baron_control_rate`                 | string  | 暴君控制率           | 对暴君的控制率                 |
| `baron_control_rate_rank`            | integer | 暴君控制率排名       | 在暴君控制率上的联盟排名       |
| `dark_baron_control_rate`            | string  | 暗影暴君控制率       | 对暗影暴君的控制率             |
| `dark_baron_control_rate_rank`       | integer | 暗影暴君控制率排名   | 在暗影暴君控制率上的联盟排名   |
| `neutral_resource_control_rate`      | string  | 中立资源控制率       | 对中立资源的总体控制率         |
| `neutral_resource_control_rate_rank` | integer | 中立资源控制率排名   | 在中立资源控制率上的联盟排名   |
| `total_master_kills`                 | float   | 总主宰击杀数         | 击杀主宰的总次数               |
| `total_master_kills_rank`            | integer | 总主宰击杀数排名     | 在总主宰击杀数上的联盟排名     |
| `total_dark_master_kills`            | float   | 总暗影主宰击杀数     | 击杀暗影主宰的总次数           |
| `total_dark_master_kills_rank`       | integer | 总暗影主宰击杀数排名 | 在总暗影主宰击杀数上的联盟排名 |
| `total_baron_kills`                  | float   | 总暴君击杀数         | 击杀暴君的总次数               |
| `total_baron_kills_rank`             | integer | 总暴君击杀数排名     | 在总暴君击杀数上的联盟排名     |
| `total_dark_baron_kills`             | float   | 总暗影暴君击杀数     | 击杀暗影暴君的总次数           |
| `total_dark_baron_kills_rank`        | integer | 总暗影暴君击杀数排名 | 在总暗影暴君击杀数上的联盟排名 |

#### 单场最佳数据

| 字段名                         | 类型    | 中文含义         | 说明                       |
| ------------------------------ | ------- | ---------------- | -------------------------- |
| `max_kills_single_game`        | float   | 单场最高击杀     | 单场比赛中的最高击杀数     |
| `max_kills_single_game_rank`   | integer | 单场最高击杀排名 | 在单场最高击杀上的联盟排名 |
| `max_deaths_single_game`       | float   | 单场最高死亡     | 单场比赛中的最高死亡数     |
| `max_deaths_single_game_rank`  | integer | 单场最高死亡排名 | 在单场最高死亡上的联盟排名 |
| `max_assists_single_game`      | float   | 单场最高助攻     | 单场比赛中的最高助攻数     |
| `max_assists_single_game_rank` | integer | 单场最高助攻排名 | 在单场最高助攻上的联盟排名 |

#### 一血数据

| 字段名                          | 类型    | 中文含义         | 说明                       |
| ------------------------------- | ------- | ---------------- | -------------------------- |
| `first_blood_count`             | float   | 一血次数         | 获得一血的总次数           |
| `first_blood_count_rank`        | integer | 一血次数排名     | 在一血次数上的联盟排名     |
| `fastest_first_blood_time`      | string  | 最快一血时间     | 最快获得一血的时间（秒）   |
| `fastest_first_blood_time_rank` | integer | 最快一血时间排名 | 在最快一血时间上的联盟排名 |

#### 10 分钟数据

| 字段名                           | 类型    | 中文含义              | 说明                             |
| -------------------------------- | ------- | --------------------- | -------------------------------- |
| `ten_min_damage_per_minute`      | float   | 10 分钟每分钟伤害     | 10 分钟时的每分钟伤害            |
| `ten_min_damage_per_minute_rank` | integer | 10 分钟每分钟伤害排名 | 在 10 分钟每分钟伤害上的联盟排名 |
| `ten_min_damage_share`           | string  | 10 分钟伤害占比       | 10 分钟时伤害占团队的比例        |
| `ten_min_damage_share_rank`      | integer | 10 分钟伤害占比排名   | 在 10 分钟伤害占比上的联盟排名   |

#### 伤害分布详情

| 字段名                          | 类型   | 中文含义         | 说明                                |
| ------------------------------- | ------ | ---------------- | ----------------------------------- |
| `damage_distribution_by_player` | string | 按选手分伤害分布 | JSON 字符串，记录对各选手造成的伤害 |

#### 其他数据

| 字段名         | 类型   | 中文含义     | 说明                 |
| -------------- | ------ | ------------ | -------------------- |
| `last_updated` | string | 最后更新时间 | 数据最后更新的时间戳 |

---

## player-hero-summary - 选手英雄胜场统计

**API**: `/api/player-hero-summary/{season_id}`  
**命名空间**: `player-hero-summary`  
**更新频率**: 不固定（赛季期间每日更新，赛季结束后不更新）

### 数据结构

```json
{
  "code": 200,
  "data": {
    "hero_id": "536",
    "hero_name": "夏洛特",
    "player_name": "KSG.无言",
    "total_matches": 15,
    "win_matches": 12,
    "win_rate": "80%"
  },
  "total": 1298,
  "season": "KPL2026S1"
}
```

### 字段说明

#### 数据字段

| 字段名          | 类型    | 中文含义   | 说明                             |
| --------------- | ------- | ---------- | -------------------------------- |
| `hero_id`       | string  | 英雄 ID    | 英雄的唯一标识符                 |
| `hero_name`     | string  | 英雄名称   | 英雄的中文名称                   |
| `player_name`   | string  | 选手名称   | 使用该英雄的选手名称             |
| `total_matches` | integer | 总使用场数 | 使用该英雄的总比赛场数           |
| `win_matches`   | integer | 胜场数     | 使用该英雄获胜的场数             |
| `win_rate`      | string  | 胜率       | 使用该英雄的胜率（百分比字符串） |

#### 元数据

| 字段名        | 类型    | 中文含义 | 说明                       |
| ------------- | ------- | -------- | -------------------------- |
| `season`      | string  | 赛季 ID  | 当前统计的赛季标识         |
| `total`       | integer | 总记录数 | 数据库中符合条件的总记录数 |
| `description` | string  | 描述     | 数据描述信息               |
| `filters`     | object  | 筛选条件 | 查询时使用的筛选条件       |

---

## team-members - 战队人员信息

**API**: `/{season_id}/{teamname}`  
**命名空间**: `team-members`  
**更新频率**: 固定，不更新

### 数据结构

```json
[
  {
    "EnickName": "KSG.无言",
    "teamName": "KSG",
    "oss_url": "https://hero-wind.oss-cn-shanghai.aliyuncs.com/.../KSG.无言.png",
    "position": "对抗路",
    "player_unique_id": "KPLP01538"
  }
]
```

### 字段说明

| 字段名             | 类型   | 中文含义    | 说明                                                    |
| ------------------ | ------ | ----------- | ------------------------------------------------------- |
| `EnickName`        | string | 选手昵称    | 选手的完整显示名（含战队前缀）                          |
| `teamName`         | string | 战队名称    | 所属战队简称                                            |
| `oss_url`          | string | 头像 URL    | 选手头像图片的 OSS 地址                                 |
| `position`         | string | 位置        | 选手在战队中的位置（对抗路/打野/中路/发育路/游走/教练） |
| `player_unique_id` | string | 选手唯一 ID | 选手在联盟中的唯一标识                                  |

---

## player-abilities - 选手能力数据

**API**: `/api/player-abilities/{season_id}`  
**命名空间**: `player-abilities`  
**更新频率**: 不固定（赛季期间每日更新，赛季结束后不更新）

### 数据结构

```json
{
  "code": 200,
  "data": {
    "player_name": "KSG.无言",
    "player_position": "对抗路",
    "team_name": "KSG",
    "season": "KPL2026S1",
    "overall_rating": 87.75,
    "overall_rank": 19.0,
    "position_rank": 5.0,
    "damage_output": 86,
    "durability": 50,
    "early_game": 75,
    "economy": 75,
    "initiation": 85,
    "invasion_ability": 80,
    "late_game": 94,
    "map_control": 89,
    "mid_game": 98,
    "support_ability": 83,
    "tankiness": 92,
    "teamfight": 82
  },
  "total_players": 114
}
```

### 字段说明

#### 基础信息

| 字段名            | 类型   | 中文含义   | 说明               |
| ----------------- | ------ | ---------- | ------------------ |
| `player_name`     | string | 选手名称   | 选手的完整显示名   |
| `player_position` | string | 选手位置   | 选手在战队中的位置 |
| `team_name`       | string | 战队名称   | 所属战队简称       |
| `season`          | string | 赛季 ID    | 当前统计的赛季标识 |
| `total_matches`   | float  | 总比赛场数 | 参与的比赛总场数   |

#### 综合评分

| 字段名                   | 类型   | 中文含义     | 说明                               |
| ------------------------ | ------ | ------------ | ---------------------------------- |
| `overall_rating`         | float  | 综合评分     | 选手的综合能力评分（0-100）        |
| `overall_rank`           | float  | 综合排名     | 在联盟中的综合排名                 |
| `overall_rank_change`    | float  | 综合排名变化 | 相比上次的排名变化（负数表示下降） |
| `overall_rank_trend`     | string | 综合排名趋势 | 排名趋势（`UP`/`DOWN`/`SAME`）     |
| `previous_overall_rank`  | float  | 上次综合排名 | 上一次的综合排名                   |
| `position_rank`          | float  | 位置排名     | 在同位置选手中的排名               |
| `position_rank_change`   | float  | 位置排名变化 | 相比上次的位置排名变化             |
| `position_rank_trend`    | string | 位置排名趋势 | 位置排名趋势                       |
| `previous_position_rank` | float  | 上次位置排名 | 上一次的位置排名                   |

#### 能力维度评分

| 字段名                           | 类型    | 中文含义         | 说明                          |
| -------------------------------- | ------- | ---------------- | ----------------------------- |
| `damage_output`                  | integer | 输出能力         | 伤害输出能力评分（0-100）     |
| `damage_output_overall_rank`     | float   | 输出能力总排名   | 在联盟中的输出能力排名        |
| `damage_output_position_rank`    | float   | 输出能力位置排名 | 在同位置中的输出能力排名      |
| `durability`                     | integer | 生存能力         | 生存/持久能力评分（0-100）    |
| `durability_overall_rank`        | float   | 生存能力总排名   | 在联盟中的生存能力排名        |
| `durability_position_rank`       | float   | 生存能力位置排名 | 在同位置中的生存能力排名      |
| `early_game`                     | integer | 前期能力         | 游戏前期表现评分（0-100）     |
| `early_game_overall_rank`        | float   | 前期能力总排名   | 在联盟中的前期能力排名        |
| `early_game_position_rank`       | float   | 前期能力位置排名 | 在同位置中的前期能力排名      |
| `economy`                        | integer | 经济能力         | 经济发育能力评分（0-100）     |
| `economy_overall_rank`           | float   | 经济能力总排名   | 在联盟中的经济能力排名        |
| `economy_position_rank`          | float   | 经济能力位置排名 | 在同位置中的经济能力排名      |
| `initiation`                     | integer | 开团能力         | 先手开团能力评分（0-100）     |
| `initiation_overall_rank`        | float   | 开团能力总排名   | 在联盟中的开团能力排名        |
| `initiation_position_rank`       | float   | 开团能力位置排名 | 在同位置中的开团能力排名      |
| `invasion_ability`               | integer | 入侵能力         | 入侵敌方野区能力评分（0-100） |
| `invasion_ability_overall_rank`  | float   | 入侵能力总排名   | 在联盟中的入侵能力排名        |
| `invasion_ability_position_rank` | float   | 入侵能力位置排名 | 在同位置中的入侵能力排名      |
| `late_game`                      | integer | 后期能力         | 游戏后期表现评分（0-100）     |
| `late_game_overall_rank`         | float   | 后期能力总排名   | 在联盟中的后期能力排名        |
| `late_game_position_rank`        | float   | 后期能力位置排名 | 在同位置中的后期能力排名      |
| `map_control`                    | integer | 地图控制         | 地图控制能力评分（0-100）     |
| `map_control_overall_rank`       | float   | 地图控制总排名   | 在联盟中的地图控制排名        |
| `map_control_position_rank`      | float   | 地图控制位置排名 | 在同位置中的地图控制排名      |
| `mid_game`                       | integer | 中期能力         | 游戏中期表现评分（0-100）     |
| `mid_game_overall_rank`          | float   | 中期能力总排名   | 在联盟中的中期能力排名        |
| `mid_game_position_rank`         | float   | 中期能力位置排名 | 在同位置中的中期能力排名      |
| `support_ability`                | integer | 支援能力         | 支援队友能力评分（0-100）     |
| `support_ability_overall_rank`   | float   | 支援能力总排名   | 在联盟中的支援能力排名        |
| `support_ability_position_rank`  | float   | 支援能力位置排名 | 在同位置中的支援能力排名      |
| `tankiness`                      | integer | 抗伤能力         | 承受伤害能力评分（0-100）     |
| `tankiness_overall_rank`         | float   | 抗伤能力总排名   | 在联盟中的抗伤能力排名        |
| `tankiness_position_rank`        | float   | 抗伤能力位置排名 | 在同位置中的抗伤能力排名      |
| `teamfight`                      | integer | 团战能力         | 团队战斗能力评分（0-100）     |
| `teamfight_overall_rank`         | float   | 团战能力总排名   | 在联盟中的团战能力排名        |
| `teamfight_position_rank`        | float   | 团战能力位置排名 | 在同位置中的团战能力排名      |

#### 数据完整性

| 字段名              | 类型    | 中文含义     | 说明                      |
| ------------------- | ------- | ------------ | ------------------------- |
| `data_completeness` | integer | 数据完整性   | 数据完整度百分比（0-100） |
| `created_at`        | string  | 创建时间     | 数据创建的时间戳          |
| `last_updated`      | string  | 最后更新时间 | 数据最后更新的时间戳      |

#### 位置平均数据

`position_averages` 对象包含各位置选手在各能力维度上的平均值，用于对比参考。

---

## player-career-wuyan - 选手职业生涯数据

**API**: `/api/player-career?player_name=KSG.%E6%97%A0%E8%A8%80`  
**命名空间**: `player-career-wuyan`  
**更新频率**: 固定，每日更新（比赛结束后）

### 数据结构

```json
{
  "code": 200,
  "data": {
    "career_summary": {
      "total_battles": 90,
      "win_battles": 52,
      "lose_battles": 38,
      "win_rate": "57.8%",
      "total_kills": 151,
      "total_deaths": 146,
      "total_assists": 346,
      "kda_ratio": 3.4,
      "mvp_count": 8
    },
    "hero_stats": [
      {
        "hero_name": "夏洛特",
        "battles": 19,
        "wins": 14,
        "loses": 5,
        "win_rate": "73.7%"
      }
    ],
    "match_details": [
      {
        "match_id": "2026032101",
        "match_date": "2026-03-21",
        "opponent_team_name": "北京 WB",
        "match_is_win": true,
        "match_score": "3:1",
        "battles_by_bo": [...]
      }
    ]
  }
}
```

### 字段说明

#### 职业生涯总结 (career_summary)

| 字段名               | 类型    | 中文含义     | 说明                                |
| -------------------- | ------- | ------------ | ----------------------------------- |
| `total_battles`      | integer | 总小局数     | 职业生涯总比赛小局数（BO 中的单局） |
| `win_battles`        | integer | 胜局数       | 职业生涯获胜的小局数                |
| `lose_battles`       | integer | 负局数       | 职业生涯失败的小局数                |
| `win_rate`           | string  | 胜率         | 职业生涯胜率（百分比字符串）        |
| `total_kills`        | integer | 总击杀       | 职业生涯总击杀数                    |
| `total_deaths`       | integer | 总死亡       | 职业生涯总死亡数                    |
| `total_assists`      | integer | 总助攻       | 职业生涯总助攻数                    |
| `kda_ratio`          | float   | KDA 比率     | 职业生涯 KDA（(击杀 + 助攻)/死亡）  |
| `mvp_count`          | integer | MVP 次数     | 获得 MVP 的总次数                   |
| `match_wins`         | integer | 获胜大场数   | 获胜的比赛大场数（BO 系列赛）       |
| `match_loses`        | integer | 失败大场数   | 失败的比赛大场数                    |
| `match_win_rate`     | string  | 大场胜率     | 比赛大场的胜率                      |
| `total_matches`      | integer | 总大场数     | 职业生涯总比赛大场数                |
| `first_season_id`    | string  | 首个赛季 ID  | 职业生涯首个赛季标识                |
| `last_season_id`     | string  | 最近赛季 ID  | 职业生涯最近赛季标识                |
| `first_match_id`     | string  | 首场比赛 ID  | 职业生涯首场比赛标识                |
| `last_match_id`      | string  | 最近比赛 ID  | 职业生涯最近比赛标识                |
| `date_range`         | string  | 日期范围     | 职业生涯日期范围                    |
| `seasons_covered`    | array   | 覆盖赛季列表 | 职业生涯涉及的赛季列表              |
| `season_type_filter` | string  | 赛季类型筛选 | 筛选条件（`all` 表示全部）          |

#### 英雄统计 (hero_stats)

| 字段名      | 类型    | 中文含义 | 说明                 |
| ----------- | ------- | -------- | -------------------- |
| `hero_name` | string  | 英雄名称 | 英雄的中文名称       |
| `hero_id`   | string  | 英雄 ID  | 英雄的唯一标识符     |
| `battles`   | integer | 使用场数 | 使用该英雄的比赛场数 |
| `wins`      | integer | 胜场数   | 使用该英雄获胜的场数 |
| `loses`     | integer | 负场数   | 使用该英雄失败的场数 |
| `win_rate`  | string  | 胜率     | 使用该英雄的胜率     |

#### 比赛详情 (match_details)

| 字段名               | 类型    | 中文含义     | 说明                       |
| -------------------- | ------- | ------------ | -------------------------- |
| `match_id`           | string  | 比赛 ID      | 比赛的唯一标识符           |
| `match_date`         | string  | 比赛日期     | 比赛进行的日期             |
| `opponent_team_name` | string  | 对手战队名称 | 对手战队的名称             |
| `match_is_win`       | boolean | 比赛是否获胜 | 该场比赛（大场）是否获胜   |
| `match_score`        | string  | 比赛比分     | 比赛的最终比分（如 `3:1`） |
| `season_id`          | string  | 赛季 ID      | 比赛所属赛季标识           |
| `team_name`          | string  | 战队名称     | 选手所属战队               |
| `schedule_id`        | string  | 赛程 ID      | 比赛在赛程中的标识         |
| `total_battles`      | integer | 总小局数     | 该场比赛的小局总数         |
| `wins`               | integer | 获胜小局数   | 该场比赛获胜的小局数       |
| `loses`              | integer | 失败小局数   | 该场比赛失败的小局数       |

#### 单局详情 (battles_by_bo)

| 字段名          | 类型    | 中文含义 | 说明                                      |
| --------------- | ------- | -------- | ----------------------------------------- |
| `battle_id`     | string  | 小局 ID  | 单局比赛的唯一标识符                      |
| `bo`            | integer | 第几局   | 在 BO 系列赛中是第几局                    |
| `hero_name`     | string  | 使用英雄 | 该局使用的英雄名称                        |
| `hero_id`       | string  | 英雄 ID  | 该局使用英雄的唯一标识符                  |
| `kills`         | integer | 击杀数   | 该局的击杀数                              |
| `deaths`        | integer | 死亡数   | 该局的死亡数                              |
| `assists`       | integer | 助攻数   | 该局的助攻数                              |
| `kda`           | string  | KDA      | 该局的 KDA 数据（格式：`击杀/死亡/助攻`） |
| `is_win`        | boolean | 是否获胜 | 该局是否获胜                              |
| `is_mvp`        | boolean | 是否 MVP | 该局是否获得 MVP                          |
| `game_duration` | integer | 游戏时长 | 该局比赛的持续时间（单位：秒）            |

---

## season-records - 赛事回顾数据

**API**: `/api/records?season={season_id}`  
**命名空间**: `season-records`  
**更新频率**: 不固定（赛季期间每日更新，赛季结束后不更新）

### 数据结构

```json
[
  {
    "record_id": 1505,
    "date": "2026-03-28",
    "game_number": 1,
    "team1": "北京 JDG",
    "team2": "成都 AG 超玩会",
    "tournament": "KPL2026 春季赛",
    "content": "【北京 JDG 0:1 成都 AG 超玩会】@成都 AG 超玩会 拿下第一局比赛！...",
    "active": true
  }
]
```

### 字段说明

| 字段名        | 类型    | 中文含义 | 说明                                           |
| ------------- | ------- | -------- | ---------------------------------------------- |
| `record_id`   | integer | 记录 ID  | 赛事回顾记录的唯一标识符                       |
| `date`        | string  | 比赛日期 | 比赛进行的日期                                 |
| `game_number` | integer | 第几局   | 该场比赛中的第几小局                           |
| `team1`       | string  | 战队 1   | 比赛中的第一支战队                             |
| `team2`       | string  | 战队 2   | 比赛中的第二支战队                             |
| `tournament`  | string  | 赛事名称 | 比赛所属的赛事名称                             |
| `content`     | string  | 比赛内容 | 比赛的详细文字回顾（含关键时间点、选手表现等） |
| `active`      | boolean | 是否有效 | 该记录是否有效（`true` 表示有效）              |

---

## player-win-stats - 选手获胜数据统计

**API**: `/api/player-win-stats/{season_id}`  
**命名空间**: `player-win-stats`  
**更新频率**: 不固定（赛季期间每日更新，赛季结束后不更新）

### 数据结构

```json
{
  "code": 200,
  "data": {
    "player_name": "KSG.无言",
    "season": "KPL2026S1",
    "avg_kills": 2.16,
    "avg_deaths": 0.95,
    "avg_assists": 5.18,
    "avg_kda": 7.75,
    "avg_gold": 10414.0,
    "avg_game_duration": 898.9,
    "win_rate": "59.4%",
    "heroes_used": ["曹操", "吕布", "白起", ...],
    "damage_10min_details": [...],
    "economy_10min_details": [...]
  }
}
```

### 字段说明

#### 基础统计

| 字段名                  | 类型   | 中文含义          | 说明                         |
| ----------------------- | ------ | ----------------- | ---------------------------- |
| `player_name`           | string | 选手名称          | 选手的完整显示名             |
| `season`                | string | 赛季 ID           | 当前统计的赛季标识           |
| `valid_10min_matches`   | float  | 有效 10 分钟场数  | 有完整 10 分钟数据的比赛场数 |
| `invalid_10min_matches` | float  | 无效 10 分钟场数  | 10 分钟数据无效的比赛场数    |
| `valid_10min_rate`      | float  | 10 分钟数据有效率 | 10 分钟数据有效的比率        |

#### KDA 统计（获胜场次）

| 字段名        | 类型  | 中文含义 | 说明                   |
| ------------- | ----- | -------- | ---------------------- |
| `avg_kills`   | float | 场均击杀 | 获胜场次中的平均击杀数 |
| `avg_deaths`  | float | 场均死亡 | 获胜场次中的平均死亡数 |
| `avg_assists` | float | 场均助攻 | 获胜场次中的平均助攻数 |
| `avg_kda`     | float | 平均 KDA | 获胜场次中的平均 KDA   |

#### 经济统计（获胜场次）

| 字段名                     | 类型  | 中文含义            | 说明                                     |
| -------------------------- | ----- | ------------------- | ---------------------------------------- |
| `avg_gold`                 | float | 平均经济            | 获胜场次中的平均总经济                   |
| `avg_economy_10min`        | float | 10 分钟平均经济     | 获胜场次中 10 分钟时的平均经济           |
| `avg_economy_10min_ratio`  | float | 10 分钟平均经济占比 | 获胜场次中 10 分钟时经济占团队的平均比例 |
| `avg_economy_diff_10min`   | float | 10 分钟平均经济差   | 获胜场次中 10 分钟时与对位的经济差       |
| `economy_10min_per_minute` | float | 10 分钟每分钟经济   | 获胜场次中 10 分钟时的每分钟经济         |

#### 伤害统计（获胜场次）

| 字段名                    | 类型  | 中文含义            | 说明                                     |
| ------------------------- | ----- | ------------------- | ---------------------------------------- |
| `avg_hurt_to_hero`        | float | 平均英雄伤害        | 获胜场次中对英雄造成的平均伤害           |
| `avg_be_hurt_by_hero`     | float | 平均承受英雄伤害    | 获胜场次中承受英雄的平均伤害             |
| `avg_ten_min_damage`      | float | 10 分钟平均伤害     | 获胜场次中 10 分钟时造成的平均伤害       |
| `avg_damage_10min_ratio`  | float | 10 分钟平均伤害占比 | 获胜场次中 10 分钟时伤害占团队的平均比例 |
| `damage_10min_per_minute` | float | 10 分钟每分钟伤害   | 获胜场次中 10 分钟时的每分钟伤害         |
| `damage_per_minute`       | float | 每分钟伤害          | 获胜场次中的每分钟伤害                   |
| `damage_taken_per_minute` | float | 每分钟承伤          | 获胜场次中的每分钟承受伤害               |

#### 团战统计（获胜场次）

| 字段名                       | 类型  | 中文含义             | 说明                                   |
| ---------------------------- | ----- | -------------------- | -------------------------------------- |
| `avg_big_fight_damage`       | float | 大型团战平均伤害     | 获胜场次中大型团战的平均伤害           |
| `avg_big_fight_damage_taken` | float | 大型团战平均承伤     | 获胜场次中大型团战的平均承受伤害       |
| `avg_big_fight_carry_damage` | float | 大型团战平均核心伤害 | 获胜场次中大型团战对核心位的平均伤害   |
| `avg_big_fight_carry_kills`  | float | 大型团战平均核心击杀 | 获胜场次中大型团战对核心位的平均击杀数 |

#### 资源控制（获胜场次）

| 字段名                   | 类型  | 中文含义     | 说明                             |
| ------------------------ | ----- | ------------ | -------------------------------- |
| `avg_blue_buff`          | float | 平均蓝 buff  | 获胜场次中平均获得的蓝 buff 数量 |
| `avg_red_buff`           | float | 平均红 buff  | 获胜场次中平均获得的红 buff 数量 |
| `avg_kill_monster_count` | float | 平均刷野数   | 获胜场次中平均刷野怪数量         |
| `avg_invasion_jungle`    | float | 平均入侵野区 | 获胜场次中平均入侵野区次数       |
| `avg_invasion_duration`  | float | 平均入侵时长 | 获胜场次中平均入侵持续时间       |
| `avg_river_duration`     | float | 平均河道时长 | 获胜场次中平均在河道停留时间     |

#### 控制与支援（获胜场次）

| 字段名                      | 类型  | 中文含义     | 说明                         |
| --------------------------- | ----- | ------------ | ---------------------------- |
| `avg_control_duration`      | float | 平均控制时长 | 获胜场次中技能控制的平均时长 |
| `avg_support_attempts`      | float | 平均支援次数 | 获胜场次中平均支援次数       |
| `avg_team_fights_initiated` | float | 平均开团次数 | 获胜场次中平均发起团战的次数 |

#### 其他统计（获胜场次）

| 字段名                       | 类型  | 中文含义         | 说明                               |
| ---------------------------- | ----- | ---------------- | ---------------------------------- |
| `avg_game_duration`          | float | 平均游戏时长     | 获胜场次的平均比赛时长（单位：秒） |
| `avg_heal_count`             | float | 平均治疗量       | 获胜场次中的平均治疗量             |
| `avg_horizon_value`          | float | 平均视野价值     | 获胜场次中的平均视野价值（推测）   |
| `avg_solo_kills`             | float | 平均单杀         | 获胜场次中的平均单杀次数           |
| `avg_team_damage_ratio`      | float | 团队伤害占比     | 获胜场次中伤害占团队的比例         |
| `above_avg_economy_total`    | float | 经济高于平均场数 | 经济高于平均值的场数               |
| `above_avg_economy_wins`     | float | 经济高于平均胜场 | 经济高于平均值且获胜的场数         |
| `above_avg_economy_win_rate` | float | 经济高于平均胜率 | 经济高于平均值时的胜率             |

#### 使用英雄列表

| 字段名        | 类型  | 中文含义     | 说明                           |
| ------------- | ----- | ------------ | ------------------------------ |
| `heroes_used` | array | 使用英雄列表 | 获胜场次中使用过的英雄名称列表 |

#### 10 分钟详情 (damage_10min_details / economy_10min_details)

| 字段名                                     | 类型    | 中文含义            | 说明                       |
| ------------------------------------------ | ------- | ------------------- | -------------------------- |
| `battle_id`                                | string  | 小局 ID             | 单局比赛的唯一标识符       |
| `hero_name`                                | string  | 英雄名称            | 该局使用的英雄             |
| `position`                                 | string  | 位置                | 选手位置                   |
| `personal_damage` / `personal_economy`     | integer | 个人伤害/经济       | 该局的个人伤害/经济        |
| `team_total_damage` / `team_total_economy` | integer | 团队总伤害/经济     | 该局的团队总伤害/经济      |
| `damage_ratio` / `economy_ratio`           | float   | 伤害/经济占比       | 占团队总伤害/经济的比例    |
| `is_valid_10min`                           | boolean | 10 分钟数据是否有效 | 该局的 10 分钟数据是否有效 |
| `match_number`                             | integer | 比赛编号            | 该场大场中的第几小局       |
| `schedule_id`                              | string  | 赛程 ID             | 比赛在赛程中的标识         |
| `team_id`                                  | string  | 战队 ID             | 战队的唯一标识符           |

---

## player-lose-stats - 选手失败数据统计

**API**: `/api/player-lose-stats/{season_id}`  
**命名空间**: `player-lose-stats`  
**更新频率**: 不固定（赛季期间每日更新，赛季结束后不更新）

### 数据结构与字段说明

与 `player-win-stats` 结构基本相同，但统计的是**失败场次**的数据。

额外字段：

| 字段名                          | 类型  | 中文含义         | 说明                     |
| ------------------------------- | ----- | ---------------- | ------------------------ |
| `lose_matches`                  | float | 失败场数         | 失败的总场数             |
| `teammates_details`             | array | 队友详情         | 与选手配合的队友详细数据 |
| `teammates_avg_invasion_jungle` | float | 队友平均入侵野区 | 队友的平均入侵野区次数   |

#### 队友详情 (teammates_details)

| 字段名                  | 类型    | 中文含义     | 说明                     |
| ----------------------- | ------- | ------------ | ------------------------ |
| `teammate_name`         | string  | 队友名称     | 队友的完整显示名         |
| `positions`             | array   | 位置列表     | 队友在战队中的位置       |
| `matches_together`      | integer | 配合场数     | 与该队友配合的场数       |
| `total_invasion_jungle` | integer | 总入侵野区   | 配合时的总入侵野区次数   |
| `avg_invasion_jungle`   | float   | 平均入侵野区 | 配合时的平均入侵野区次数 |

---

## win-affinity-analysis - 获胜时选手亲近度分析

**API**: `/api/{season_id}/win-affinity-analysis`  
**命名空间**: `win-affinity-analysis`  
**更新频率**: 不固定（赛季期间每日更新，赛季结束后不更新）

### 数据结构

```json
{
  "code": 200,
  "data": {
    "player_pairs_analysis": [
      {
        "player_pair": "西安 WE.忆安 + 西安 WE.昭珏",
        "player1": "西安 WE.忆安",
        "player2": "西安 WE.昭珏",
        "avg_win_affinity": 59.543,
        "win_games": 9,
        "teams_count": 1,
        "teams_played": ["西安 WE"],
        "recent_wins": [...]
      }
    ]
  }
}
```

### 字段说明

#### 选手组合分析 (player_pairs_analysis)

| 字段名               | 类型    | 中文含义       | 说明                                         |
| -------------------- | ------- | -------------- | -------------------------------------------- |
| `player_pair`        | string  | 选手组合       | 两位选手的组合名称（格式：`选手 1+ 选手 2`） |
| `player1`            | string  | 选手 1         | 组合中的第一位选手                           |
| `player2`            | string  | 选手 2         | 组合中的第二位选手                           |
| `avg_win_affinity`   | float   | 平均获胜亲近度 | 获胜时的平均亲近度分数                       |
| `total_win_affinity` | float   | 总获胜亲近度   | 获胜时的总亲近度分数                         |
| `win_games`          | integer | 获胜场数       | 两位选手一起获胜的场数                       |
| `win_dates_count`    | integer | 获胜日期数     | 获胜的不同日期数量                           |
| `teams_count`        | integer | 战队数量       | 两位选手一起效力过的战队数量                 |
| `teams_played`       | array   | 效力战队列表   | 两位选手一起效力过的战队名称列表             |

#### 最近获胜记录 (recent_wins)

| 字段名          | 类型    | 中文含义   | 说明                       |
| --------------- | ------- | ---------- | -------------------------- |
| `battle_id`     | string  | 小局 ID    | 单局比赛的唯一标识符       |
| `date`          | string  | 比赛日期   | 比赛进行的日期（中文格式） |
| `opponent`      | string  | 对手战队   | 对手战队的名称             |
| `team`          | string  | 所属战队   | 两位选手所属的战队         |
| `bo_round`      | integer | 第几局     | 在 BO 系列赛中是第几局     |
| `affinity_rate` | float   | 亲近度比率 | 该局的亲近度比率（百分比） |

---

## team-damage-distribution - 战队选手伤害分布

**API**: `/api/team-damage-distribution/{season_id}/{team_name}`  
**命名空间**: `team-damage-distribution`  
**更新频率**: 不固定（赛季期间每日更新，赛季结束后不更新）

### 数据结构

```json
{
  "code": 200,
  "data": {
    "players": [
      {
        "player_name": "KSG.无言",
        "player_position": "对抗路",
        "total_matches": 64,
        "damage_by_player": [...],
        "damage_to_positions": [...],
        "damage_to_positions_total": [...],
        "damage_to_positions_average": [...]
      }
    ]
  }
}
```

### 字段说明

#### 选手伤害数据 (players)

| 字段名             | 类型    | 中文含义    | 说明                   |
| ------------------ | ------- | ----------- | ---------------------- |
| `player_name`      | string  | 选手名称    | 选手的完整显示名       |
| `player_position`  | string  | 选手位置    | 选手在战队中的位置     |
| `player_unique_id` | string  | 选手唯一 ID | 选手在联盟中的唯一标识 |
| `total_matches`    | integer | 总比赛场数  | 参与的比赛总场数       |

#### 对各选手伤害 (damage_by_player)

| 字段名        | 类型    | 中文含义   | 说明                 |
| ------------- | ------- | ---------- | -------------------- |
| `player_name` | string  | 被伤害选手 | 被造成伤害的选手名称 |
| `damage`      | integer | 伤害值     | 对该选手造成的总伤害 |

#### 对各位置伤害占比 (damage_to_positions)

| 字段名       | 类型   | 中文含义 | 说明                                   |
| ------------ | ------ | -------- | -------------------------------------- |
| `position`   | string | 位置     | 目标位置（top/jungle/mid/adc/support） |
| `percentage` | string | 伤害占比 | 对该位置造成的伤害占比（百分比字符串） |

#### 对各位置伤害总量 (damage_to_positions_total)

| 字段名     | 类型    | 中文含义 | 说明                 |
| ---------- | ------- | -------- | -------------------- |
| `position` | string  | 位置     | 目标位置             |
| `damage`   | integer | 伤害总量 | 对该位置造成的总伤害 |

#### 对各位置平均伤害占比 (damage_to_positions_average)

| 字段名       | 类型   | 中文含义     | 说明                       |
| ------------ | ------ | ------------ | -------------------------- |
| `position`   | string | 位置         | 目标位置                   |
| `percentage` | string | 平均伤害占比 | 平均每场对该位置的伤害占比 |

---

## hero-win-rate - 联盟英雄胜率

**API**: `/api/hero-win-rate/{season_id}?position={position}`  
**命名空间**: `hero-win-rate`  
**更新频率**: 不固定（赛季期间每日更新，赛季结束后不更新）

### 数据结构

```json
{
  "code": 200,
  "data": [
    {
      "hero_id": "503",
      "hero_name": "狂铁",
      "position": "对抗路",
      "total_matches": 181,
      "win_matches": 101,
      "lose_matches": 80,
      "win_rate": "55.8%",
      "rank": 1,
      "mvp_count": 12,
      "mvp_rate": "6.6%",
      "total_players": 22,
      "total_matchup_heroes": 13,
      "matchups": [...]
    }
  ]
}
```

### 字段说明

#### 英雄基础数据

| 字段名                 | 类型    | 中文含义     | 说明                         |
| ---------------------- | ------- | ------------ | ---------------------------- |
| `hero_id`              | string  | 英雄 ID      | 英雄的唯一标识符             |
| `hero_name`            | string  | 英雄名称     | 英雄的中文名称               |
| `position`             | string  | 位置         | 英雄的主要位置               |
| `total_matches`        | integer | 总出场数     | 该英雄在联盟中的总出场场数   |
| `win_matches`          | integer | 胜场数       | 该英雄获胜的总场数           |
| `lose_matches`         | integer | 负场数       | 该英雄失败的总场数           |
| `win_rate`             | string  | 胜率         | 该英雄的胜率（百分比字符串） |
| `rank`                 | integer | 排名         | 该英雄在位置内的胜率排名     |
| `mvp_count`            | integer | MVP 次数     | 该英雄获得 MVP 的总次数      |
| `mvp_rate`             | string  | MVP 率       | 该英雄获得 MVP 的比率        |
| `total_players`        | integer | 使用选手数   | 使用该英雄的选手总数         |
| `total_matchup_heroes` | integer | 对线英雄数   | 与该英雄对线过的英雄总数     |
| `last_updated`         | string  | 最后更新时间 | 数据最后更新的时间戳         |

#### 对线数据 (matchups)

| 字段名       | 类型    | 中文含义 | 说明                               |
| ------------ | ------- | -------- | ---------------------------------- |
| `enemy_hero` | string  | 对线英雄 | 对线的敌方英雄名称                 |
| `hero_id`    | string  | 英雄 ID  | 对线英雄的唯一标识符               |
| `total`      | integer | 对线场数 | 与该英雄对线的总场数               |
| `wins`       | integer | 胜场数   | 与该英雄对线获胜的场数             |
| `losses`     | integer | 负场数   | 与该英雄对线失败的场数             |
| `win_rate`   | string  | 胜率     | 与该英雄对线的胜率（百分比字符串） |

---

## 附录：位置代码对照表

| 代码      | 中文名称 | 说明        |
| --------- | -------- | ----------- |
| `top`     | 对抗路   | 上路/对抗路 |
| `jungle`  | 打野     | 打野位      |
| `mid`     | 中路     | 中路/法师位 |
| `adc`     | 发育路   | 下路/射手位 |
| `support` | 游走     | 辅助/游走位 |

---

## 附录：赛季 ID 命名规则

| 前缀  | 含义       | 示例                         |
| ----- | ---------- | ---------------------------- |
| `KPL` | KPL 联赛   | `KPL2026S1`（2026 春季赛）   |
| `KIC` | 世界冠军杯 | `KIC2023`（2023 世界冠军杯） |
| `KCC` | 挑战者杯   | `KCC2025`（2025 挑战者杯）   |

**联赛后缀说明**：

- `S1` = 春季赛
- `S2` = 夏季赛
- `S3` = 年度总决赛

---

## 文档版本

- **版本**: 1.0
- **最后更新**: 2026-03-30
- **数据版本**: 基于 KPL2026S1 赛季数据

---

**备注**: 本文档中部分字段的含义为推测，已用"推测"标注，待后续核实确认。
