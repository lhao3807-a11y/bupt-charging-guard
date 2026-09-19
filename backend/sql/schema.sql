-- =============================================================================
-- 桩点北邮 · 充电桩车位防占系统 —— 四表建表 + 种子数据
-- -----------------------------------------------------------------------------
-- 唯一事实源：docs/CONTRACT.md v1.1 §3（数据模型）、§7（系统配置项）
-- 语法基线  ：MySQL 8.0（本文件为正式交付物）
-- 开发期验证：本机未装 MySQL 8，按 CONTRACT §2「方案 b」用 SQLite + SQLAlchemy
--             做等价验证（见 backend/app/models.py 与 backend/tests/test_models.py）；
--             MySQL 8 真机验证延至第 2 周接入真实库时执行。
-- 维护人    ：汤瑾睿
-- -----------------------------------------------------------------------------
-- 注意：
--  1. ENUM 在 MySQL 侧保留原生类型；业务代码（SQLAlchemy 模型 / Pydantic）一律
--     按 String + Enum 校验，禁止依赖 DB 原生 ENUM 行为（换库才不炸）。
--  2. system_config 的 `key` 是 MySQL 保留字，必须加反引号。
--  3. 种子数据与 algo/samples/labels/*.json 的 plate 必须对得上（契约 §10）：
--     识别桩返回的车牌要能在 charging_pile.bound_plate 中查到，judge 才能关联到桩。
-- =============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS occupation_record;
DROP TABLE IF EXISTS charging_pile;
DROP TABLE IF EXISTS system_config;
DROP TABLE IF EXISTS vehicle;

SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------------------------------
-- 1. vehicle　车辆信息（CONTRACT §3.1）
-- -----------------------------------------------------------------------------
CREATE TABLE vehicle (
  plate      VARCHAR(15)  NOT NULL                   COMMENT '车牌号',
  vtype      ENUM('新能源','燃油') NOT NULL           COMMENT '车型（由绿牌/蓝牌判定）',
  owner      VARCHAR(50)      DEFAULT NULL           COMMENT '车主',
  phone      VARCHAR(20)      DEFAULT NULL           COMMENT '绑定手机号',
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '录入时间',
  PRIMARY KEY (plate)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='车辆信息';

-- -----------------------------------------------------------------------------
-- 2. charging_pile　充电桩状态（模拟）（CONTRACT §3.2）
-- -----------------------------------------------------------------------------
-- 约定（与 CONTRACT §3.2 一致，规则引擎判定口径）：
--  · bound_plate 记录「当前占用该桩的车牌」——含充电车与占位车（燃油车占位时也写入），
--    规则引擎即以 bound_plate 反查车辆所在桩。
--  · start_time 复用为「车辆绑定 / 到达该桩的时间」：新能源车停着不充电（status=空闲）
--    时，规则②以 now - start_time > abnormal_park_min 判定「异常占位 · 久停」。
--  · end_time 为「充满时间」，规则③以 now - end_time > full_timeout_min 判定「充满未移车」。
CREATE TABLE charging_pile (
  pile_id     VARCHAR(20) NOT NULL                        COMMENT '桩 ID',
  status      ENUM('空闲','充电中','已充满') NOT NULL DEFAULT '空闲' COMMENT '运行状态',
  bound_plate VARCHAR(15)     DEFAULT NULL                COMMENT '绑定/占用车牌（FK vehicle.plate）',
  start_time  DATETIME        DEFAULT NULL                COMMENT '绑定/开始充电时间（规则②久停基准）',
  end_time    DATETIME        DEFAULT NULL                COMMENT '充满时间（规则③超时基准）',
  PRIMARY KEY (pile_id),
  KEY idx_pile_bound_plate (bound_plate),
  CONSTRAINT fk_pile_vehicle FOREIGN KEY (bound_plate) REFERENCES vehicle (plate)
    ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='充电桩状态（模拟数据）';

-- -----------------------------------------------------------------------------
-- 3. occupation_record　违规记录（CONTRACT §3.3）
-- -----------------------------------------------------------------------------
-- rule_hit：0 正常 / 1 燃油占位 / 2 异常占位 / 3 充满未移车
CREATE TABLE occupation_record (
  id            BIGINT      NOT NULL AUTO_INCREMENT       COMMENT '记录 ID',
  plate         VARCHAR(15) NOT NULL                      COMMENT '车牌',
  vtype         ENUM('新能源','燃油') NOT NULL             COMMENT '车型',
  pile_id       VARCHAR(20)     DEFAULT NULL              COMMENT '桩 ID（v0.1 新增）',
  rule_hit      TINYINT     NOT NULL DEFAULT 0            COMMENT '1 燃油占位 / 2 异常占位 / 3 充满未移车 / 0 正常',
  occur_time    DATETIME    NOT NULL                      COMMENT '命中时间',
  notify_status ENUM('未提醒','已提醒','失败') NOT NULL DEFAULT '未提醒' COMMENT '提醒状态',
  notify_time   DATETIME        DEFAULT NULL              COMMENT '提醒时间',
  PRIMARY KEY (id),
  KEY idx_occ_occur_time (occur_time),
  KEY idx_occ_rule_hit (rule_hit),
  KEY idx_occ_plate (plate)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='违规记录';

-- -----------------------------------------------------------------------------
-- 4. system_config　系统参数（CONTRACT §3.4 / §7）
-- -----------------------------------------------------------------------------
CREATE TABLE system_config (
  `key`   VARCHAR(30)  NOT NULL COMMENT '参数键',
  `value` VARCHAR(50)  NOT NULL COMMENT '参数值',
  note    VARCHAR(100)     DEFAULT NULL COMMENT '说明',
  PRIMARY KEY (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统参数（阈值等，严禁硬编码）';

-- =============================================================================
-- 种子数据
-- =============================================================================

-- 车辆：6 辆（4 新能源 + 2 燃油），覆盖四条规则所需场景
--  · 前 4 辆与充电桩种子一一对应，服务四条规则的判定
--  · 后 2 辆（v1.3 任务 C）为「车辆信息管理」页准备，保证两类车型标签都能取到色
INSERT INTO vehicle (plate, vtype, owner, phone, created_at) VALUES
  ('京AD12345', '新能源', '汤瑾睿', '13800000001', '2026-09-01 09:00:00'),
  ('京AD67890', '新能源', '吕浩',   '13800000002', '2026-09-01 09:05:00'),
  ('京AD24680', '新能源', '吴和庆', '13800000003', '2026-09-01 09:10:00'),
  ('京A88888',  '燃油',   '张伟',   '13800000004', '2026-09-01 09:15:00'),
  ('京AD33333', '新能源', '王芳',   '13800000005', '2026-09-01 09:20:00'),
  ('京N66666',  '燃油',   '李明',   '13800000006', '2026-09-01 09:25:00');

-- 充电桩：4 个，覆盖 空闲 / 充电中 / 已充满 三种状态
--  · PILE-001 充电中  → 规则④ 正常充电，judge 返回 null
--  · PILE-002 已充满  → 若 now - end_time > full_timeout_min，命中规则③
--  · PILE-003 空闲    → 新能源占位，若 now - start_time > abnormal_park_min，命中规则②
--  · PILE-004 空闲    → 燃油车占位，命中规则①
INSERT INTO charging_pile (pile_id, status, bound_plate, start_time, end_time) VALUES
  ('PILE-001', '充电中', '京AD12345', '2026-09-08 09:50:00', NULL),
  ('PILE-002', '已充满', '京AD67890', '2026-09-08 08:00:00', '2026-09-08 09:20:00'),
  ('PILE-003', '空闲',   '京AD24680', '2026-09-08 08:30:00', NULL),
  ('PILE-004', '空闲',   '京A88888',  '2026-09-08 09:00:00', NULL);

-- 系统参数：契约 §7 两项默认阈值（严禁硬编码，业务一律查本表）
-- 注：识别桩的 stub/real 开关不走本表，而是环境变量 RECOGNITION_MODE（非业务阈值，属部署期开关）
INSERT INTO system_config (`key`, `value`, note) VALUES
  ('full_timeout_min',  '30', '充满超时阈值（分钟）：已充满后超过该时长未移车即命中规则③'),
  ('abnormal_park_min', '30', '异常占位久停阈值（分钟）：未充电停放超过该时长即命中规则②');
