"""主数据 schema: 字段定义、枚举、校验、IO、投影。

零依赖(Python 3.10+ 标准库)。所有处理脚本 import 本模块。
字段定义与 docs/dataset_spec.md 保持一致。
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import json
import hashlib

# ---------- 枚举常量(与 docs 同步) ----------
TASK_TYPES = {
    "structural_strength", "fatigue_failure", "info_insufficient",
    "material_heat_treatment", "engineering_calculation", "fea_interpretation",
    "fault_diagnosis", "basic_concept", "context_extraction", "tool_awareness",
    # 兼容旧 v1/v2 的类别名
    "design_review", "process_planning", "safety_boundary", "material_evidence",
}

DOMAINS = {
    "shaft", "gear", "bearing", "bolted_joint", "weldment",
    "spring_coupling", "beam_plate", "hydraulic_seal", "general",
}

RISK_TAGS = {
    "net_section_reduction", "stress_concentration", "fatigue", "static_strength",
    "stiffness_deflection", "buckling_stability", "wear_contact_fatigue",
    "vibration_resonance", "thermal_deformation", "surface_integrity",
    "heat_treatment", "manufacturing_process", "assembly_tolerance",
    "inspection_ndt", "corrosion", "fastener_loosening",
    "missing_information", "fabricated_value_risk",
}

REVIEW_STATUSES = {
    "model_generated", "seed_pending_review", "self_reviewed",
    "expert_approved", "rejected",
}

DIFFICULTIES = {"easy", "medium", "hard"}
SOURCE_TYPES = {
    "expert_constructed", "mechqa_converted", "model_generated",
    "literature_extract", "v1v2_migrated",
}

REQUIRED_FIELDS = [
    "id", "task_type", "domain", "subdomain", "difficulty", "language",
    "instruction", "input", "output", "risk_tags", "numeric_claims",
    "requires_tool", "requires_rag", "source_type", "source_ref",
    "license", "review_status", "reviewer", "split_group", "version",
]


@dataclass
class MasterRecord:
    id: str
    task_type: str
    domain: str
    subdomain: str
    difficulty: str
    language: str
    instruction: str
    input: str
    output: str
    risk_tags: list = field(default_factory=list)
    numeric_claims: list = field(default_factory=list)
    requires_tool: bool = False
    requires_rag: bool = False
    source_type: str = "expert_constructed"
    source_ref: str = ""
    license: str = "internal-approved"
    review_status: str = "seed_pending_review"
    reviewer: str = ""
    split_group: str = ""
    version: str = "v0.1-seed"

    # --- 校验:返回错误信息列表(空列表=通过) ---
    def validate(self) -> list:
        errs = []
        if not self.id:
            errs.append("id 为空")
        if self.task_type not in TASK_TYPES:
            errs.append(f"task_type 非法: {self.task_type}")
        if self.domain not in DOMAINS:
            errs.append(f"domain 非法: {self.domain}")
        if self.difficulty not in DIFFICULTIES:
            errs.append(f"difficulty 非法: {self.difficulty}")
        for f in ("instruction", "input", "output"):
            if not getattr(self, f) or not str(getattr(self, f)).strip():
                errs.append(f"{f} 为空")
        if not isinstance(self.risk_tags, list):
            errs.append("risk_tags 非列表")
        else:
            for t in self.risk_tags:
                if t not in RISK_TAGS:
                    errs.append(f"risk_tag 非法: {t}")
        if not isinstance(self.numeric_claims, list):
            errs.append("numeric_claims 非列表")
        if self.source_type not in SOURCE_TYPES:
            errs.append(f"source_type 非法: {self.source_type}")
        if self.review_status not in REVIEW_STATUSES:
            errs.append(f"review_status 非法: {self.review_status}")
        if not isinstance(self.requires_tool, bool):
            errs.append("requires_tool 非布尔")
        if not isinstance(self.requires_rag, bool):
            errs.append("requires_rag 非布尔")
        return errs

    # --- 投影成 LLaMA-Factory alpaca 三字段 ---
    def to_alpaca(self) -> dict:
        return {"instruction": self.instruction, "input": self.input, "output": self.output}

    # --- 用于去重的文本指纹(忽略空白) ---
    def text_fingerprint(self) -> str:
        key = (self.instruction.strip() + "\n" + self.input.strip()).lower()
        return hashlib.sha1(key.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)


# ---------- IO 工具 ----------
def load_jsonl(path) -> list:
    path = Path(path)
    out = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"{path}:{i} JSON 解析失败: {e}") from e
    return out


def save_jsonl(records: list, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(obj, path, indent=2) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=indent), encoding="utf-8")


def dict_to_record(d: dict) -> MasterRecord:
    """从 dict 构造 MasterRecord,忽略未知字段,缺失字段用默认值。"""
    known = {f for f in REQUIRED_FIELDS}
    kwargs = {k: v for k, v in d.items() if k in known}
    return MasterRecord(**kwargs)


if __name__ == "__main__":
    # 自检:构造一条示例并校验
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    demo = MasterRecord(
        id="shaft_cross_hole_fatigue_000001", task_type="design_review",
        domain="shaft", subdomain="cross_hole_fatigue", difficulty="hard",
        language="zh",
        instruction="你是一名机械设计审查工程师。",
        input="调质传动轴中部有横向销孔,承受交变弯曲。",
        output="当前信息不足,需按疲劳校核。",
        risk_tags=["stress_concentration", "fatigue", "missing_information"],
    )
    errs = demo.validate()
    print("demo validate:", "PASS" if not errs else errs)
    print("alpaca:", demo.to_alpaca())
    print("fp:", demo.text_fingerprint()[:12])
