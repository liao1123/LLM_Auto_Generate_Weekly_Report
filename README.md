# LLM Auto Generate Weekly Report

## 动机
毕设周报/周记往往需要重复填写大量格式化内容。可能有人会认真记录，但更多时候是临近 DDL 才集中补齐。  
本项目尝试用 LLM 根据不同课题主题与背景材料自动生成周记内容，并填充进既有 LaTeX 模板，批量导出 PDF。

> 说明：请确保生成内容真实、可核对；不要直接用于不符合学校/导师要求的场景。

---

## 目标
- 调用 LLM API，根据用户输入的题目与背景材料生成每周周记文本：
  - 本周进展（progress）
  - 存在的问题与思路（problems_and_solutions）
  - 下周计划（next_week_plan）
- 将生成内容自动填入 `周记模板.tex.template`
- 通过 `pdflatex` 编译生成每周对应的 PDF 文件

---

## 项目结构
- `generate_weekly_report.py`  
  主入口。解析命令行参数 → 调用 LLM 生成内容 → 填入 LaTeX 模板 → 编译生成 PDF。
- `prompt.py`  
  Prompt 配置与约束。可自行调整输出风格、长度、是否分点、是否编号等。
- `chat.py`  
  LLM API 调用封装（读取 `.env` 中的 Key/Base URL/Model 等）。
- `materials/`  
  存放导师电子签名、背景材料（开题报告、任务书等）。脚本可自动读取并作为上下文输入 LLM。
- `weekly_report/`  
  输出目录。保存最终生成的 `.tex/.pdf` 文件。
- `周记模板.tex.template`  
  LaTeX 模板文件，脚本会将生成内容注入模板并编译为 PDF。

---

## 环境要求
- Python 3.10+（建议 3.10/3.11）
- TeX Live（需包含 `pdflatex`、`CJKutf8` 等相关宏包）
- 已配置可用的 LLM API Key

---

## 安装
```bash
pip install -r requirements.txt
```

## 配合env文件
```bash
API_KEY=xxxx
BASE_URL=xxxx
MODEL_NAME=xxxx
```

## 材料放入materials中
将以下文件放入 materials/：

- 导师签名图片（如 sign.jpg / sign.png）
- 背景材料（任务书、开题报告等，txt/pdf/docx 均可，具体看你的读取逻辑）

脚本会自动读取并作为背景上下文传给 LLM（以项目实现为准）。

## 运行
修改下面参数即可
```bash
python generate_weekly_report.py \
    --college "网络与信息安全学院" \
    --major "网络空间安全" \
    --title "推箱子小程序设计" \
    --student_name "你的名字" \
    --student_id "你的学号" \
    --advisor "你的指导老师" \
    --weeks 16 \
    --user_prompt "根据所给的背景材料和论文标题来生成周记" \
    --opinion "同意"
```
最终完整pdf保存在weekly_report/final_pdf/week_x中

## 免责声明
本项目仅用于学习与效率提升。请遵守学校学术规范与导师要求，生成内容应基于真实进展进行核对与修改，使用者自行承担使用后果。

## 参考
周记批量生成：https://github.com/canxin121/xdu_weekly_journal
