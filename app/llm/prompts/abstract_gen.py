"""Abstract generation prompts.

This prompt generates an estimated abstract from a Research Blueprint.
Implements R-04 (No fake data) and R-05 (Results = [PLACEHOLDER]).
"""

from app.models.schemas import ResearchBlueprint
from app.rules.design_rules import get_design_display_name


SYSTEM_PROMPT = """Ban la chuyen gia viet abstract nghien cuu y khoa.

NHIEM VU:
Viet abstract nghien cuu dua tren Research Blueprint duoc cung cap.
Abstract se duoc su dung de CHUA THUC HIEN nghien cuu (estimated abstract).

QUY TAC BAT BUOC:
1. KHONG BAO GIO tao so lieu gia (R-04)
2. Phan KET QUA phai ghi: "[PLACEHOLDER - Ket qua se duoc dien sau khi co du lieu]" (R-05)
3. Phan KET LUAN ghi ket luan DU KIEN dua tren gia thuyet, khong khang dinh

CAU TRUC ABSTRACT:
1. Muc tieu (Objective): 2-3 cau, neu ro muc dich nghien cuu
2. Phuong phap (Methods): 3-5 cau, mo ta thiet ke, dan so, can thiep, ket qua chinh
3. Ket qua (Results): "[PLACEHOLDER - Ket qua se duoc dien sau khi co du lieu]"
4. Ket luan (Conclusion): 2-3 cau, ket luan DU KIEN

NGON NGU:
- Viet bang tieng Viet
- Co the dung thuat ngu tieng Anh trong ngoac
- Giu van phong khoa hoc, chinh xac"""


def get_abstract_generation_prompt(blueprint: ResearchBlueprint) -> str:
    """
    Generate prompt for abstract generation.

    Args:
        blueprint: Research Blueprint

    Returns:
        Prompt string for LLM
    """
    design_name = get_design_display_name(blueprint.design_type)

    # Format secondary outcomes
    secondary = ""
    if blueprint.secondary_outcomes:
        secondary = "\n".join(f"  - {o}" for o in blueprint.secondary_outcomes)

    # Format design details
    details = ""
    if blueprint.design_details:
        details = "\n".join(f"  - {k}: {v}" for k, v in blueprint.design_details.items())

    prompt = f"""RESEARCH BLUEPRINT:

=== PICO(T) ===
- Population (P): {blueprint.population}
- Intervention/Exposure (I): {blueprint.intervention_or_exposure}
- Comparator (C): {blueprint.comparator or "Khong co (single-arm)"}
- Primary Outcome (O): {blueprint.primary_outcome}
- Timeframe (T): {blueprint.timeframe or "Khong xac dinh"}

=== THIET KE ===
- Loai: {design_name}
{f"- Chi tiet:{chr(10)}{details}" if details else ""}

=== CO MAU ===
- So luong: n = {blueprint.sample_size}
- Ly do: {blueprint.sample_justification or "Chua xac dinh"}

=== KET QUA PHU ===
{secondary if secondary else "- Khong co"}

=== PHUONG PHAP THONG KE ===
{blueprint.statistical_approach or "Chua xac dinh cu the"}

=== METADATA ===
- Chuyen khoa: {blueprint.specialty or "Khong xac dinh"}
- Dia diem: {blueprint.setting or "Khong xac dinh"}

---

NHIEM VU:
Dua tren Blueprint tren, hay viet mot ESTIMATED ABSTRACT hoan chinh.

LUU Y QUAN TRONG:
- Phan "Ket qua" PHAI ghi: "[PLACEHOLDER - Ket qua se duoc dien sau khi co du lieu]"
- Phan "Ket luan" chi ghi ket luan DU KIEN, KHONG khang dinh ket qua
- Do dai: 250-300 tu
- Cau truc: Muc tieu > Phuong phap > Ket qua > Ket luan

HAY VIET ABSTRACT:"""

    return prompt


def validate_generated_abstract(abstract: str) -> tuple[bool, list[str]]:
    """
    Validate that generated abstract follows rules.

    Args:
        abstract: Generated abstract text

    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []
    abstract_lower = abstract.lower()

    # R-04: Check for fake data patterns
    fake_data_patterns = [
        r"p\s*[<>=]\s*0\.\d{2,}",  # Specific p-values
        r"(or|hr|rr)\s*=\s*\d+\.\d+",  # Specific ratios
        r"\d+\.\d+%\s*(vs|so voi)",  # Specific percentages comparison
        r"giam\s*\d+%",  # Specific percentage decrease
        r"tang\s*\d+%",  # Specific percentage increase
    ]

    import re
    for pattern in fake_data_patterns:
        if re.search(pattern, abstract_lower):
            issues.append(f"Phat hien so lieu co the la gia: pattern '{pattern}'")

    # R-05: Check for results placeholder
    if "[placeholder" not in abstract_lower:
        issues.append("Thieu [PLACEHOLDER] trong phan Ket qua")

    # Check for conclusion tone
    definitive_patterns = [
        "chung minh rang",
        "ket qua cho thay",
        "da chung minh",
        "co hieu qua",
        "khong co hieu qua",
    ]

    for pattern in definitive_patterns:
        if pattern in abstract_lower:
            issues.append(f"Ket luan qua khang dinh: '{pattern}'")

    return len(issues) == 0, issues


def format_abstract_with_sections(abstract: str) -> dict:
    """
    Parse abstract into sections.

    Args:
        abstract: Full abstract text

    Returns:
        Dict with section names as keys
    """
    sections = {
        "objective": "",
        "methods": "",
        "results": "",
        "conclusion": "",
        "full_text": abstract
    }

    # Try to identify sections
    lines = abstract.split("\n")
    current_section = None

    for line in lines:
        line_lower = line.lower().strip()

        if "muc tieu" in line_lower or "objective" in line_lower:
            current_section = "objective"
        elif "phuong phap" in line_lower or "method" in line_lower:
            current_section = "methods"
        elif "ket qua" in line_lower or "result" in line_lower:
            current_section = "results"
        elif "ket luan" in line_lower or "conclusion" in line_lower:
            current_section = "conclusion"
        elif current_section:
            sections[current_section] += line + "\n"

    # Clean up
    for key in sections:
        if key != "full_text":
            sections[key] = sections[key].strip()

    return sections
