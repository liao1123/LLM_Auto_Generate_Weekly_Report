import os
import json
from typing import List, Dict, Optional, Union

from dotenv import load_dotenv
from openai import OpenAI

from prompt import *


# 对文本稳定那个进行解析
def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

# 对pdf进行解析
def read_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return f"[无法读取PDF：未安装pypdf] 文件：{path}"

    try:
        reader = PdfReader(path)
        texts = []
        for page in reader.pages:
            t = page.extract_text() or ""
            if t.strip():
                texts.append(t)
        return "\n".join(texts).strip()
    except Exception as e:
        return f"[PDF读取失败] 文件：{path} 错误：{e}"


# 对docx进行解析
def read_docx(path: str) -> str:
    try:
        import docx  # python-docx
    except ImportError:
        return f"[无法读取Word：未安装python-docx] 文件：{path}"

    try:
        d = docx.Document(path)
        paras = [p.text for p in d.paragraphs if p.text.strip()]
        return "\n".join(paras).strip()
    except Exception as e:
        return f"[Word读取失败] 文件：{path} 错误：{e}"

# 导入文档
def load_background(background_files: Optional[List[str]] = None) -> str:
    chunks: List[str] = []

    if background_files:
        for fp in background_files:
            if not fp or not os.path.exists(fp):
                chunks.append(f"[背景文件不存在] {fp}")
                continue

            ext = os.path.splitext(fp)[1].lower()
            if ext in [".txt", ".md"]:
                chunks.append(read_text_file(fp))
            elif ext == ".pdf":
                chunks.append(read_pdf(fp))
            elif ext in [".docx"]:
                chunks.append(read_docx(fp))
            else:
                # 其他格式先按文本尝试读取
                chunks.append(f"[未知格式，按文本尝试读取] {fp}\n{read_text_file(fp)}")
    merged = "\n\n".join([c for c in chunks if c])
    return merged.strip()


# 导入环境变量
def get_env_var():
    load_dotenv()
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("BASE_URL")
    model_name = os.getenv("MODEL_NAME")
    if not api_key:
        raise ValueError("缺少环境变量 API_KEY")
    return OpenAI(api_key=api_key, base_url=base_url), model_name

def chat_json(client: OpenAI, model: str, system: str, user: str) -> Union[Dict, List]:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.4,
    )
    content = response.choices[0].message.content

    # 尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        cleaned = content
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)


def generate_weekly_reports(
    user_prompt: str,
    weeks: int,
    background_files: Optional[List[str]] = None,
) -> List[Dict]:
    """
    输入：
      - user_prompt: 前端用户输入的主题/要求
      - weeks: 周数（总共生成多少周）
      - background_files: 背景文件路径列表（pdf/docx/txt/md）

    输出：
      - List[Dict] 每周一个 dict：
        {week, progress, problems_and_solutions, next_week_plan}
    """
    if not user_prompt or not user_prompt.strip():
        raise ValueError("user_prompt 不能为空")
    if weeks <= 0 or weeks > 52:
        raise ValueError("weeks 需在 1-52 之间")

    # 导入api client、model name
    client, model_name = get_env_var()

    # 导入前端传的文件进行解析成文本
    background_text = load_background(background_files=background_files)
    
    # 先按照周数来生成每周的框架
    system_pt = system_prompt()
    plan_pt = plan_prompt(weeks, user_prompt, background_text)
    week_plan_list = chat_json(client, model_name, system_pt, plan_pt)
    if not isinstance(week_plan_list, list) or len(week_plan_list) != weeks:
        raise ValueError(f"总体计划输出不符合要求：需要长度为{weeks}的JSON数组")

    reports = []

    for idx, wp in enumerate(week_plan_list):
        wk_user = weekly_prompt(
            user_prompt=user_prompt,
            week_plan=wp,
            background_text=background_text,
            prev_week_summary=week_plan_list[idx-1] if idx > 0 else None,
            next_week_summary=week_plan_list[idx+1] if idx < weeks-1 else None
        )
        wk_report = chat_json(client, model_name, system_pt, wk_user)

        # 校验
        for k in ["week", "title", "progress", "problems_and_solutions", "next_week_plan"]:
            if k not in wk_report:
                raise ValueError(f"第{wp.get('week')}周周报缺少字段：{k}")

        reports.append(wk_report)

    return reports

def llm_output(user_prompt, weeks, background_file):
    # 保存 JSON 到文件
    output_path = "weekly_report/weekly_report.json"
    if not os.path.exists(output_path):
        generate_result = generate_weekly_reports(
            user_prompt=user_prompt,
            weeks=weeks,
            background_files=background_file,  # 文件保存到本地的地址
        )
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(generate_result, f, ensure_ascii=False, indent=2)
    else:
        with open(output_path, "r", encoding="utf-8") as f:
            generate_result = json.load(f)
    print("llm generate scussfully!")
    return generate_result