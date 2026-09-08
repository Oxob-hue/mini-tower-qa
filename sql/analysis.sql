-- MiniTower 平衡/概率数据分析查询集（W3）
-- 用法：任意 SQLite 客户端打开 results/w3.db 后逐条执行；
--      也可由 scripts/w3_report.py 自动执行并生成报告。

-- ### Q1 各编队通关质量排行（通关率/三星率/平均时长/漏怪总量）
SELECT team_id,
       COUNT(*)                                        AS runs,
       SUM(clear)                                      AS clears,
       SUM(three_star)                                 AS stars,
       ROUND(SUM(clear) * 100.0 / COUNT(*), 2)         AS clear_rate,
       ROUND(SUM(three_star) * 100.0 / COUNT(*), 2)    AS star_rate,
       ROUND(AVG(end_time), 2)                         AS avg_duration,
       SUM(leaked)                                     AS total_leaked
FROM sim_runs
GROUP BY team_id
ORDER BY SUM(clear) DESC, AVG(end_time);

-- ### Q2 高防关（1-2）：编队是否含真实伤害术师 → 漏怪与三星率差异
SELECT CASE WHEN team_id LIKE '%caster_c%'
            THEN '含真伤术师 caster_c' ELSE '不含真伤术师'
       END                                             AS composition,
       COUNT(*)                                        AS runs,
       SUM(leaked)                                     AS leaked,
       ROUND(SUM(three_star) * 100.0 / COUNT(*), 2)    AS star_rate,
       ROUND(AVG(lives_left), 2)                       AS avg_lives
FROM sim_runs
WHERE stage_id = '1-2'
GROUP BY composition;

-- ### Q3 干员伤害占比排行（json_each 展开 dmg_by_op，跨局聚合）
SELECT je.key                                         AS operator,
       SUM(je.value)                                  AS total_damage,
       COUNT(DISTINCT r.id)                           AS runs
FROM sim_runs AS r, json_each(r.dmg_by_op) AS je
GROUP BY je.key
ORDER BY SUM(je.value) DESC;

-- ### Q4 保底开关对整体 6★ 率的影响（招募）
SELECT pity_enabled,
       COUNT(*)                                       AS runs,
       SUM(pulls)                                     AS pulls,
       SUM(n6)                                        AS n6,
       ROUND(SUM(n6) * 100.0 / SUM(pulls), 4)         AS rate6_pct
FROM recruit_runs
GROUP BY pity_enabled
ORDER BY pity_enabled;

-- ### Q5 三星与漏怪的关联（通关质量画像）
SELECT three_star,
       COUNT(*)                                       AS runs,
       ROUND(AVG(leaked), 3)                          AS avg_leaked,
       ROUND(AVG(lives_left), 2)                      AS avg_lives
FROM sim_runs
GROUP BY three_star
ORDER BY three_star;

-- ### Q6 关卡×编队时长窗口（性能与平衡的粗粒度基线）
SELECT stage_id,
       team_id,
       COUNT(*)                                       AS runs,
       ROUND(MIN(end_time), 2)                        AS min_dur,
       ROUND(AVG(end_time), 2)                        AS avg_dur,
       ROUND(MAX(end_time), 2)                        AS max_dur
FROM sim_runs
GROUP BY stage_id, team_id
ORDER BY stage_id, avg_dur;
