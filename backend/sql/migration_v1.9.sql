-- =============================================================================
-- 迁移：schema v1.8 → v1.9（第 3 周自动闭环）
-- -----------------------------------------------------------------------------
-- 对应 CONTRACT.md v1.9 §3.6（占用标识）与 §6.3（提醒结果由发送器产生）。
-- 设计依据：docs/week3/T1_OCCUPANCY_DESIGN.md
-- 维护人  ：汤瑾睿
-- -----------------------------------------------------------------------------
-- 升级（在目标库执行）
-- =============================================================================

ALTER TABLE charging_pile
  ADD COLUMN occupancy_id VARCHAR(40) NULL
    COMMENT '本次占用标识（到车生成/离车清空，CONTRACT §3.6）' AFTER bound_plate,
  ADD COLUMN scenario VARCHAR(20) NULL
    COMMENT '模拟场景标签（仅演示夹具用，不参与判定）' AFTER occupancy_id,
  ADD KEY idx_pile_occupancy (occupancy_id);

ALTER TABLE occupation_record
  ADD COLUMN occupancy_id VARCHAR(40) NULL
    COMMENT '落库时快照的占用标识，永不改写（CONTRACT §3.6）' AFTER pile_id,
  ADD COLUMN notify_attempts TINYINT NOT NULL DEFAULT 0
    COMMENT '已尝试发送次数（重启不清零）' AFTER notify_time,
  ADD COLUMN notify_error VARCHAR(120) NULL
    COMMENT '最近一次发送失败原因' AFTER notify_attempts,
  ADD KEY idx_occ_occupancy (occupancy_id);

-- =============================================================================
-- 回退（v1.9 → v1.8）
-- -----------------------------------------------------------------------------
-- ⚠️ Git 回滚 ≠ 数据库回滚：回滚代码不会自动 DROP COLUMN。
--    新增列全部「可空或有默认值」，旧代码在带新列的库上仍可运行（向前兼容），
--    所以可以先回滚代码、再择机执行本段回退。
-- =============================================================================

-- ALTER TABLE charging_pile
--   DROP KEY idx_pile_occupancy,
--   DROP COLUMN occupancy_id,
--   DROP COLUMN scenario;
--
-- ALTER TABLE occupation_record
--   DROP KEY idx_occ_occupancy,
--   DROP COLUMN occupancy_id,
--   DROP COLUMN notify_attempts,
--   DROP COLUMN notify_error;
