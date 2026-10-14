# 腾讯会议测试数据源：AI+X碰个头·第二十四期

2026-10-13 晚的会议录制，通过 `tmeet` CLI（@tencentcloud/tmeet v1.0.18，OAuth 已授权）
拉取，作为 videodevour 接入腾讯会议数据源的测试数据。

## 会议信息

| 项 | 值 |
|---|---|
| 会议主题 | AI+X碰个头（周期性会议，每 3 天一期） |
| 本期 | 第二十四期 |
| meeting_id | `3010812525270541781` |
| meeting_code | `60669290755` |
| 用户分享链接 | https://meeting.tencent.com/crm/2MYYqPy94b |
| 转写主文件 record_file_id | `2109971748627333121` |
| 会议录制 ID（云录制） | `2109971748627333120`（can_view，5 个子文件） |
| 主转写时长覆盖 | 00:00 – 02:15:03，236 段，11 位说话人 |

## 文件清单

| 文件 | 内容 | 来源命令 |
|---|---|---|
| `transcript_2109971748627333121.json` | 原始转写 JSON：段落→句子→词 三级时间戳 + 说话人分离 + 关键词 | `tmeet record transcript-get` |
| `transcript.md` | 从上速读导出的纯文本逐字稿，每段一行 `[时间] 说话人: 内容`（236 行），对齐 videodevour 的 transcript.md 形态 | 本地脚本转换 |
| `smart_minutes_main.json` | 智能纪要（录制的 AI 纪要） | `tmeet record smart-minutes` |
| `yuanbao_minutes.json` | 元宝纪要（overview / summary_points / todos，含 22、23、24 三期） | `tmeet minutes get` |
| `meeting_meta.json` | 会议元数据：周期规则、全部 23 条录制记录及权限状态、参会设置 | `tmeet meeting get` |

## 关键 JSON 路径速查

```text
transcript_*.json
├─ data.minutes.lang / keywords[]          # 语言、自动关键词
└─ data.minutes.paragraphs[]               # 转写段落
   ├─ start_time / end_time                # 段级时间戳（"MM:SS" / "HH:MM:SS"）
   ├─ speaker.user_name                    # 说话人（已按声纹分离）
   └─ sentences[].words[]                  # 句/词级时间戳，text 在 word 上

yuanbao_minutes.json
└─ data.minutes[]                          # 每期一条
   ├─ overview                             # 一句话总览（发言人+主题+摘要开头）
   ├─ summary_points                       # 分点详细纪要（纯文本）
   └─ todos[]                              # 待办（本期为空）

smart_minutes_main.json
└─ data.meeting_minute                     # 智能纪要主体
```

## 取数路径（复现命令）

```bash
# 1. 定位会议（周期会议按 meeting_id 查）
tmeet meeting get --meeting-id 3010812525270541781 --compact

# 2. 拿云录制各子文件 record_file_id（permission_status=can_view 才可用）
tmeet record address --meeting-record-id 2109971748627333120

# 3. 拉转写 / 智能纪要 / 元宝纪要
tmeet record transcript-get --record-file-id 2109971748627333121 --meeting-id 3010812525270541781
tmeet record smart-minutes --record-file-id 2109971748627333121
tmeet minutes get --meeting-id 3010812525270541781
```

## 踩坑记录

- **分享短链接不可直接当 record_file_id 用**（`crm/2MYYqPy94b` → 190004 Invalid
  RecordFileId）。正确链路：用户给主题/会议号 → `meeting get` → `records[]` 拿
  `meeting_record_id` + `permission_status` → `record address` 下钻子文件 ID。
- **`record list` / `record search` 只返回自己有权限的录制**，本例返回空；必须走
  `meeting` 命令族（会议级查询）才能看到无权限录制和 `permission_status`。
- 云录制 5 个子文件中仅主转写文件有转写内容；其余 3 个报 70001「获取纪要详情失败」、
  1 个报 30003「内容生成中」（分会场转写生成较慢，隔天可重试）。
- 时间参数必须带时区：`2026-10-13T00:00:00+08:00`。
