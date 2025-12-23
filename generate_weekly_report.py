import argparse
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict

from chat import llm_output
import os

# Fields and whether the value should be wrapped in braces in the TEX template.
FIELD_STYLE = {
    "college": "plain",
    "week": "plain",
    "major": "plain",
    "title": "braced",
    "student": "plain",
    "id": "plain",
    "advisor": "plain",
    "work": "braced",
    "issue": "braced",
    "plan": "braced",
    "opinion": "braced",
}

BACKGROUND_EXTS = {".txt", ".md", ".json", ".tex", ".pdf", ".docx"}
SIGNATURE_EXTS  = {".png", ".jpg", ".jpeg", ".bmp", ".pdf"}

TEMPLATE_PATH = Path("周记模板.tex.template")

def tex_paragraphs(s: str) -> str:
    if s is None:
        return ""
    # 统一各种换行
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # 再把真实换行转成 LaTeX 分段
    s = s.replace("\n", r"\par ")
    return s
def tex_escape(s: str) -> str:
    """最基本的 TeX 转义，避免 LLM/用户文本里出现特殊字符导致编译失败。"""
    if s is None:
        return ""
    rep = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out = []
    for ch in str(s):
        out.append(rep.get(ch, ch))
    return "".join(out)


def _wrap(field: str, value: str) -> str:
    """Wrap value in braces if the template expects it."""
    if FIELD_STYLE[field] == "braced":
        return "{" + value + "}"
    return value


def build_week_block(entry: Dict[str, str], sign_name: str | None) -> str:
    for field in FIELD_STYLE:
        if field not in entry:
            raise KeyError(f"missing field '{field}' in data entry (week {entry.get('week')})")
    
    if sign_name:
        sign_snippet = (
            r"\par\vspace{0.6cm}"
            r"\makebox[\linewidth][r]{指导教师（签名）：\hspace{0.8em}"
            r"\raisebox{-0.4cm}{\includegraphics[width=2.8cm]{" + sign_name + r"}}}"
        )
    else:
        sign_snippet = (
            r"\par\vspace{0.6cm}"
            r"\makebox[\linewidth][r]{指导教师（签名）：\hspace{0.8em}\makebox[3cm][c]{}}"
        )
    lines = ["\\WeeklyLogEntry{%"]
    for field in FIELD_STYLE:
        val = _wrap(field, entry[field])
        if field == "opinion":
            val = "{" + entry[field] + sign_snippet + "}"
        lines.append(f"{field} = {val},")
    lines[-1] = lines[-1].rstrip(",")  # no trailing comma on the last line
    lines.append("}")
    return "\n".join(lines) + "\n"


def inject_week_block(template: str, week_block: str) -> str:
    """
    Replace the original \\WeeklyLogEntry{...} block (the sample data right
    before \\begin{document}) with the rendered block.
    """
    start = template.find("\\WeeklyLogEntry{")
    if start == -1:
        raise ValueError("Could not find \\WeeklyLogEntry in template")
    begin_doc = template.find("\\begin{document}", start)
    if begin_doc == -1:
        raise ValueError("Could not find \\begin{document} in template")
    prefix = template[:start]
    suffix = template[begin_doc:]
    return prefix + week_block + suffix


def fill_template(template: str, entry: Dict[str, str], sign_name: str | None) -> str:
    block = build_week_block(entry, sign_name)
    return inject_week_block(template, block)


def compile_pdf(tex_file: Path) -> None:
    cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex_file.name]
    subprocess.run(cmd, cwd=tex_file.parent, check=True)


def _week_report_to_tex_fields(llm_week: Dict[str, str]) -> Dict[str, str]:
    """把 LLM 每周输出转换为模板需要的 work/issue/plan 字段文本。"""
    # 你的 weekly_prompt 目前是字符串分点（“- ”开头换行），这里直接用
    work = llm_week.get("progress", "")
    issue = llm_week.get("problems_and_solutions", "")
    plan = llm_week.get("next_week_plan", "")
    title = llm_week.get("title", f"第{llm_week.get('week','')}周")

    return {
        "title": title,
        "work": work,
        "issue": issue,
        "plan": plan,
    }

# 解析参数
def parse_args():
    p = argparse.ArgumentParser(
        description="LLM 自动生成周报（命令行版）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # 基本信息
    p.add_argument("--college", default="网络与信息安全学院", help="学院")
    p.add_argument("--major", default="网络空间安全", help="专业")
    p.add_argument("--title", default="基于深度学习的垃圾分类识别系统", help="毕设题目")
    p.add_argument("--student_name", default="张三", help="学生姓名")
    p.add_argument("--student_id", default="2020123456", help="学号")
    p.add_argument("--advisor", default="李老师", help="导师姓名")

    p.add_argument("--weeks", type=int, default=8, help="生成周数", required=True)

    p.add_argument("--user_prompt", type=str, default="按照所给背景完成毕设周记内容", help="用户需求/主题描述（建议尽量具体）")
    p.add_argument("--opinion", type=str, default="同意", help="导师的意见")
    return p.parse_args()

def load_local_materials(material_path):
    p = Path(material_path).expanduser()

    if not p.exists():
        raise FileNotFoundError(f"material_path not found: {p}")

    # 收集候选文件
    if p.is_file():
        files = [p]
    else:
        files = [f for f in p.rglob("*") if f.is_file()]

    # 分类
    bg_candidates = [f for f in files if f.suffix.lower() in BACKGROUND_EXTS]
    sign_candidates = [f for f in files if f.suffix.lower() in SIGNATURE_EXTS]

    # 你也可以加一个规则：文件名包含 sign/signature/签名 的优先级更高
    def pick_latest(cands):
        if not cands:
            return None
        return max(cands, key=lambda x: x.stat().st_mtime)

    background_file = pick_latest(bg_candidates)
    signature_path = pick_latest(sign_candidates)

    return background_file, signature_path

def generate_weekly_report():
    if not TEMPLATE_PATH.exists():
        raise SystemExit("周记模板.tex.template not found in current directory")
    
    # 命令行导入参数
    args = parse_args()
    college, major, title, student_name, student_id, advisor, weeks, user_prompt, opinion = args.college, args.major, args.title, args.student_name, args.student_id, args.advisor, args.weeks, args.user_prompt, args.opinion

    # 从本地文件夹读取background_file 和 signature_path
    material_path = "materials"
    os.makedirs(material_path, exist_ok=True)
    background_file, signature_path = load_local_materials(material_path)

    # 保存地址
    save_path = "weekly_report"
    os.makedirs(save_path, exist_ok=True)
    # 调用 LLM 生成周报结构
    generate_result = llm_output(user_prompt, weeks, background_file)
    if not isinstance(generate_result, list) or len(generate_result) == 0:
        raise SystemExit("No week entries returned by llm_output")

    # 在输出文件夹里保存签名文件，方便之后latex引用
    signature_path = Path(signature_path) if signature_path else None
    sign_dest_name: str | None = None
    if signature_path:
        sign_dest_name = signature_path.name
        sign_source = signature_path 
        if sign_source.exists():
            shutil.copy2(sign_source, Path(save_path) / sign_dest_name)
        else:
            print(f"Warning: signature image '{sign_source}' not found; opinion will omit signature.")


    # 读取latex模板
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    # 按周生成 tex+pdf
    for idx in range(1, weeks + 1):
        # 找到对应周的数据
        llm_week = next((x for x in generate_result if int(x.get("week", -1)) == idx), None)
        if llm_week is None:
            raise ValueError(f"LLM output missing week {idx}")

        week_fields = _week_report_to_tex_fields(llm_week)

        entry = {
            "college": tex_escape(college),
            "week": tex_escape(str(idx)),
            "major": tex_escape(major),
            "title": tex_escape(title if title else week_fields["title"]),  # 题目放模板title字段更常见
            "student": tex_escape(student_name),
            "id": tex_escape(student_id),
            "advisor": tex_escape(advisor),

            # 周报三段
            "work": tex_paragraphs(tex_escape(week_fields["work"])),
            "issue": tex_paragraphs(tex_escape(week_fields["issue"])),
            "plan": tex_paragraphs(tex_escape(week_fields["plan"])),

            "opinion": tex_escape(opinion),
        }

        tex_name = f"week_{idx}.tex"
        tex_path = os.path.join(save_path, tex_name)

        tex_content = fill_template(template, entry, sign_dest_name)
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)

        compile_pdf(Path(tex_path)) 

    # 读取savepath下面的pdf文件然后重新提取到一个新的文件夹下面
    pdf_save_path = os.path.join(save_path, "final_pdf")
    os.makedirs(pdf_save_path, exist_ok=True)
    pdfs = sorted(Path(save_path).glob("*.pdf"))
    for pdf in pdfs:
        shutil.copy2(pdf, os.path.join(pdf_save_path, pdf.name))
    print(f"Generated {weeks} TEX/PDF files in {save_path}")


if __name__ == "__main__":
    generate_weekly_report()