# 用例-需求追踪矩阵（RTM / Test Case Matrix，W1~W3）

> 目的：证明「每一条测试用例都对应到一条需求条目（REQ）」，且覆盖了 公式/边界/顺序/胜负/守卫
> 等不同测试类型。面试可据此讲"怎么从需求拆用例"。
> W1/W2 行为级用例见下方（tests/test_rules.py 20 条 + test_smoke.py 12 条）；
> W3 数值三件套与数据层见文末附录。期望值全部来自需求文档手工推导，非实现抄写。

图例：类别 = 🧮公式 / 🔲边界 / 🔀顺序 / ⚖️胜负 / 🛡守卫 / 🧪回归

## 伤害结算 DMG

| 用例（tests/test_rules.py） | REQ | 类别 | 关键断言 |
|---|---|---|---|
| TestDamageRules::test_dmg001_physical_armor_subtraction | REQ-DMG-001 | 🧮 | atk100 vs def30 → 每击 70 |
| TestDamageRules::test_dmg001_floor_5pct_when_armor_wins | REQ-DMG-001/004 | 🔲🧮 | atk95 vs def100 → ⌈95×5%⌉=5（防 BUG-002） |
| TestDamageRules::test_dmg004_floor_never_below_one | REQ-DMG-004 | 🔲 | atk20 vs def1000 → 下限 1，绝不 0/负 |
| TestDamageRules::test_dmg002_true_damage_ignores_armor | REQ-DMG-002 | 🧮 | def1000 不减伤，2 击击杀 hp600 |
| TestDamageRules::test_dmg003_crit_multiplies_after_armor | REQ-DMG-003 | 🔀 | 先减免后暴击：(100−30)×2=140 |
| TestDamageRules::test_dmg005_first_attack_delay_equals_interval | REQ-DMG-005 | 🔲 | 首次命中时刻 = interval |
| TestDamageRules::test_dmg005_attack_interval_kept_after_miss | REQ-DMG-005 + STG-004 | 🔲🧪 | 空挥不改节拍、漏怪清场判胜非超时（防 BUG-001） |

## 技能 SKL

| 用例 | REQ | 类别 | 关键断言 |
|---|---|---|---|
| TestSkillRules::test_skl001_skill_on_every_nth_landed_hit | REQ-SKL-001 | 🔀🧮 | N=3：普普通技 普普通技；技能无视防御 200（防 BUG-003） |
| TestSkillRules::test_skl002_skill_every_one_fires_every_hit | REQ-SKL-001 | 🔲 | N=1 边界：每次命中都是技能 |
| TestSkillRules::test_skl001_no_skill_when_disabled | REQ-SKL-002 | 🔲 | skill_every=0 永不触发 |
| TestSkillRules::test_skl003_skill_affected_by_crit | REQ-SKL-003 | 🔀 | 技能 200 × 暴击 1.5 = 300 |
| TestSkillRules::test_skl001_missed_attack_does_not_advance_skill_counter | REQ-SKL-001 | 🔲 | 空挥不计入命中计数（敌方晚入场场景） |

## 索敌 TGT

| 用例 | REQ | 类别 | 关键断言 |
|---|---|---|---|
| TestTargetingRules::test_tgt001_targets_furthest_enemy_first | REQ-TGT-001 | 🔀 | 两敌同场先杀位置更靠前（近终点）的敌人 |

## 关卡规则 STG

| 用例 | REQ | 类别 | 关键断言 |
|---|---|---|---|
| TestStageRules::test_stg002_leak_deducts_enemy_leak_value | REQ-STG-002 | 🧮 | leak=3 → lives 10−3=7 |
| TestStageRules::test_stg005_three_star_lives_equal_boundary | REQ-STG-005 | 🔲⚖️ | 剩余生命 == 三星线 → 3★ |
| TestStageRules::test_stg005_three_star_lives_below_boundary | REQ-STG-005 | 🔲⚖️ | 剩余生命 < 三星线 → 非 3★ |
| TestStageRules::test_stg003_defeat_when_base_reaches_zero | REQ-STG-003 | ⚖️ | 第三只漏怪到达瞬间判负，end_time 精确 |
| TestStageRules::test_stg004_no_premature_victory_between_waves | REQ-STG-004 | 🔲⚖️ | 波间隔 20s 不得提前判胜 |
| TestStageRules::test_stg006_timeout_guard_returns_defeat | REQ-STG-006 | 🛡 | 打不死且到不了终点 → 600s 判 timeout |
| TestStageRules::test_victory_reason_and_leak_count_when_single_leak | REQ-STG-004 | 🧪⚖️ | 单漏怪清场 → victory 非 timeout（BUG-001 回归） |

## 覆盖率小结

- REQ 覆盖：DMG-001~005、SKL-001~003、TGT-001、STG-002~006 均有**行为级**用例；
  CFG 域由 `tests/test_smoke.py::TestLoader` 覆盖（加载/坏配置/引用完整性）。
- 补充冒烟/确定性/批量结构：`tests/test_smoke.py`（12 条）。
- 缺陷复盘：`docs/defects.md`（BUG-001 真实 + BUG-002/003 W2 演练，均有回归用例锁定）。

---

# W3 用例-需求追踪矩阵（RTM 附录：数值三件套 + 数据层）

图例：类别 = 🎲概率 / ⚖️平衡 / 📈膨胀 / 🗄数据

## 招募概率（tests/test_probability.py，10 条）

| 用例 | REQ | 类别 | 关键断言 |
|---|---|---|---|
| TestRecruitEngine::test_prb001_seed_reproducible_sequence | REQ-PRB-001 | 🎲 | seed 固定 → 5000 抽出货序列一致 |
| TestRecruitEngine::test_prb006_probabilities_sum_to_one | REQ-PRB-006 | 🎲 | p6+p5+p4=1 且稀有度越高概率越低 |
| TestRecruitEngine::test_prb005_pity_resets_after_six_star | REQ-PRB-003/005 | 🎲 | cap=10 无软保底 → 6★ 必现于第 10/20/30 抽 |
| TestRecruitEngine::test_prb003_inclusive_gap_bounded_by_cap | REQ-PRB-003 | 🎲 | 20 万抽 6★ 间隔 ≤ 100 |
| TestRecruitEngine::test_prb004_soft_pity_rate_increases | REQ-PRB-004 | 🎲 | 软保底概率单调不减 |
| TestRecruitEngine::test_config_validation | REQ-PRB-006 | 🎲 | 非法概率/保底参数被拒 |
| TestRecruitEngine::test_recruit_data_file_loads | REQ-PRB-006 | 🎲 | recruit.json 可加载且字段正确 |
| TestHypothesisTests::test_prb002_no_pity_chi2_goodness_of_fit | REQ-PRB-002 | 🎲 | 200 万抽 χ²<5.991（实测 0.146） |
| TestHypothesisTests::test_prb002_no_pity_six_star_rate_ci_contains_declared | REQ-PRB-002 | 🎲 | 6★ 率在声明值 95% 二项 CI 内 |
| TestHypothesisTests::test_pity_improves_overall_rate_within_gap_bound | REQ-PRB-007 | 🎲 | 保底后整体率 > 基础率且间隔有界 |

## 平衡回归与膨胀校验（tests/test_balance.py，10 条）

| 用例 | REQ | 类别 | 关键断言 |
|---|---|---|---|
| TestBalanceRegression::test_bal001_team_a_on_1_1_always_three_star | REQ-BAL-001 | ⚖️ | 2000 局 1-1 编队A 通关/三星率 ≥0.999 |
| TestBalanceRegression::test_bal001_team_a_duration_in_design_band | REQ-BAL-001 | ⚖️ | 时长 ∈ (24,33)s（基准 28.0） |
| TestBalanceRegression::test_bal002_team_b_on_1_2_three_star_stable | REQ-BAL-002 | ⚖️ | 1-2 编队B 三星率 ≥0.99、时长 ∈ (52,58)s |
| TestBalanceRegression::test_weak_team_on_1_2_leaks_but_no_star_any_seed | REQ-BAL-003 | ⚖️ | 单近卫每局漏 3、0% 三星（跨 seed 稳定） |
| TestBalanceRegression::test_dmg_aggregation_sanity | REQ-DATA-004 | 🗄 | Σ干员伤害 == 总局伤害（含零输出干员语义） |
| TestInflationAndCountercheck::test_anl001_no_inflation_on_armorless_targets | REQ-ANL-001 | 📈 | 0 防 DPS 跨度 <3.2（实测 2.56） |
| TestInflationAndCountercheck::test_anl001_rarity_gap_within_design | REQ-ANL-001 | 📈 | 6★/4★ 平均强度 ≤3.0（实测 ≈2.46） |
| TestInflationAndCountercheck::test_anl003_high_defense_exposes_physical_weakness | REQ-ANL-003 | 📈 | def100 跨度 >8（实测 ≈25.5） |
| TestInflationAndCountercheck::test_anl002_true_damage_is_the_counter | REQ-ANL-002 | 📈 | def100 真伤优势 ≥10×（实测 ≈25.2） |
| TestInflationAndCountercheck::test_anl004_theory_consistency_on_true_damage | REQ-ANL-004 | 📈 | 理论口径与防御无关（真伤） |

## 数据层（tests/test_db.py，6 条）

| 用例 | REQ | 类别 | 关键断言 |
|---|---|---|---|
| TestDataLayer::test_sql_file_parses_more_than_five_queries | REQ-DATA-003 | 🗄 | analysis.sql ≥6 条查询可解析 |
| TestDataLayer::test_q1_team_ranking_counts_match_inserts | REQ-DATA-001 | 🗄 | Q1 落库行数与插入一致 |
| TestDataLayer::test_q2_caster_composition_difference | REQ-DATA-003 | 🗄 | Q2 编队构成分组正确 |
| TestDataLayer::test_q3_operator_damage_share_sum_equals_total | REQ-DATA-004 | 🗄 | json_each 聚合 == dmg_total |
| TestDataLayer::test_q4_recruit_pity_effect_rows | REQ-DATA-002/003 | 🗄 | Q4 保底分组且保底率更高 |
| TestDataLayer::test_schema_roundtrip_records | REQ-DATA-001/002 | 🗄 | schema 回放行数正确 |

> W3 全量 = 10+10+6 = 26 条；连同 W1/W2 共 **58 条**，全绿。
> 真实数据报告：`docs/w3-report.md`；复现：`python scripts/w3_report.py`。

---

# W4 用例-需求追踪矩阵（RTM 附录：性能 + 平衡调参）

图例：类别 = 🕐性能 / 📐伸缩 / 🧪基线机制 / ⚖️调参故事

## 性能（tests/test_perf.py，6 条）

| 用例 | REQ | 类别 | 关键断言 |
|---|---|---|---|
| TestPerformanceGuards::test_perf001_single_run_under_absolute_guard | REQ-PERF-001 | 🕐 | 1-1 编队A 单局 <5ms（实测 0.09ms） |
| TestPerformanceGuards::test_perf002_peak_memory_bounded | REQ-PERF-002 | 🕐 | 单局峰值 <100MB（实测 ≈9KB） |
| TestScaleCurve::test_perf004_tenfold_enemies_tenfold_time_approx | REQ-PERF-004 | 📐 | ×10 敌人伸缩比 ∈(5,25)（实测 ≈9.9） |
| TestBaselineMachinery::test_check_within_baseline_respects_factor | REQ-PERF-003 | 🧪 | ≤基线×1.5 PASS；超限 FAIL |
| TestBaselineMachinery::test_serialize_roundtrip_preserves_data | REQ-PERF-005 | 🧪 | baseline JSON 往返无损 |
| TestBaselineMachinery::test_load_missing_baseline_returns_none | REQ-PERF-006 | 🧪 | 无基线文件 → None（首次运行跳过比对） |

## 平衡调参故事线（tests/test_tuning.py，4 条）

| 用例 | REQ | 类别 | 关键断言 |
|---|---|---|---|
| TestTuningStory::test_baseline_critical_team_meets_design | REQ-BAL-005 | ⚖️ | 磐石+惊雷@1-2 通关/三星率 ≥0.99（基线绿） |
| TestTuningStory::test_red_after_over_nerf | REQ-BAL-005 | ⚖️ | 惊雷 atk 140→98：三星率 <95%（实测 43%，红） |
| TestTuningStory::test_green_after_tuning_to_suggestion | REQ-BAL-005 | ⚖️ | 采纳 atk=112：三星率 ≥0.99（回归绿） |
| TestTuningStory::test_suggestion_floor_locates_boundary | REQ-BAL-005 | ⚖️ | 109 达标 / 106 不达标（自证区间来自测试） |

> W4 全量 = 6+4 = 10 条；连同 W1–W3 共 **68 条**，全绿。
> 报告：`docs/w4-report.md`；复现：`python scripts/w4_bench.py` / `python scripts/w4_tune_demo.py`。

---

# W5 用例-需求追踪矩阵（RTM 附录：AI 辅助 + 每日回归）

图例：类别 = 🤖AI / 🧪闸门 / ⚖️CI

## AI 辅助（tests/test_ai.py，11 条）

| 用例 | REQ | 类别 | 关键断言 |
|---|---|---|---|
| TestSchemaGate::test_non_json_output_rejected | REQ-AI-001 | 🧪 | 非 JSON 回复被拒、审计留痕 pending |
| TestSchemaGate::test_missing_and_wrong_field_types_rejected | REQ-AI-001 | 🧪 | 缺字段/类型错 → AIOutputError |
| TestSchemaGate::test_enum_out_of_domain_rejected | REQ-AI-001 | 🧪 | risk 枚举外值被拒 |
| TestSchemaGate::test_valid_stub_output_passes_and_audited | REQ-AI-001/006 | 🧪 | 合法输出通过且 schema_ok=True |
| TestTestPointsGeneration::test_novel_boundaries_quantified | REQ-AI-002 | 🤖 | 与已知覆盖比对 → novel_count>0 且不重复 |
| TestTestPointsGeneration::test_human_review_workflow | REQ-AI-002/006 | 🧪 | pending→approved 复核流转 |
| TestRiskCrossValidation::test_ai_over_aggressive_interval_is_corrected_by_engine | REQ-AI-004 | 🤖 | AI 给 atk≥100 → 引擎实测 109 → 不一致并修正；floor 真边界自证 |
| TestRiskCrossValidation::test_sane_ai_interval_passes_consistency | REQ-AI-004 | 🤖 | AI 给 atk≥115 → 与引擎一致放行 |
| TestRiskCrossValidation::test_risk_assessment_pipeline_shape | REQ-AI-003 | 🤖 | risk/reasons/建议区间结构完整 |
| TestFailureClustering::test_cluster_and_accuracy | REQ-AI-005 | 🤖 | 聚类计数一致、与真实根因准确率 100% |
| TestAuditPersistence::test_append_with_unwritable_path_does_not_break | REQ-AI-006/007 | 🧪 | 审计落盘失败静默降级，内存审计保留 |

> W5 全量 = 11 条；连同 W1–W4 共 **79 条**，全绿。
> 报告：`docs/w5-report.md`；复现：`python scripts/w5_ai_demo.py`。
> CI：`.github/workflows/daily-balance.yml`（每日 02:00 UTC → 全量测试 + `scripts/ci_daily_balance.py` 平衡回归）。
