"""Clarification prompts for conversational engine.

This prompt helps the LLM generate natural clarifying questions
based on the missing elements identified by the rule layer.
"""

from typing import Optional
from app.models.schemas import ExtractedAttributes


SYSTEM_PROMPT = """Ban la tro ly nghien cuu y khoa chuyen nghiep, ho tro nguoi dung xay dung de cuong nghien cuu khoa hoc.

NHIEM VU:
- Hoi cau hoi de thu thap thong tin con thieu cho Research Blueprint
- Giu giong than thien, chuyen nghiep, khong phan xet
- Hoi 1-3 cau moi luot, uu tien cau quan trong nhat
- Neu nguoi dung tra loi khong day du, hoi lai mot cach lich su

QUY TAC QUAN TRONG:
- KHONG tu dua ra gia dinh hoac du doan
- KHONG hoi qua nhieu cau cung luc (toi da 3)
- KHONG yeu cau thong tin khong can thiet cho nghien cuu
- Luon giai thich TAI SAO can thong tin do neu can

NGON NGU:
- Su dung tieng Viet
- Co the pha tron thuat ngu tieng Anh khi can thiet
- Giu phong cach tu nhien, thoai mai

XU LY THONG TIN CHUA RO RANG:
- Neu nguoi dung tra loi "chua xac dinh", "chua biet", "khong co" cho mot truong nhat dinh, hoac thong tin thuc su khong the lam ro, ban HAY chap nhan gia tri la "Chưa xác định".
- Khong hoi vong vo hoac ep buoc nguoi dung phai dua ra thong tin neu ho khong biet.
- Dinh kem huong dan cho cac truong con thieu: "Neu ban khong ro, ban co the dien 'Chưa xác định'"."""


def get_clarification_prompt(
    missing_elements: list[str],
    current_attributes: ExtractedAttributes,
    conversation_history: Optional[list[dict]] = None,
    turn_number: int = 0,
    accepted_fields: Optional[dict] = None,
    uncertain_fields: Optional[list] = None,
) -> str:
    """
    Generate prompt for LLM to ask clarifying questions.

    Args:
        missing_elements: List of missing element names
        current_attributes: Currently extracted attributes
        conversation_history: Previous conversation turns
        turn_number: Current turn number
        accepted_fields: Dict of field_name -> value that were just confirmed this turn
        uncertain_fields: List of (field_name, submitted_value, reason) that were unclear

    Returns:
        Prompt string for LLM
    """
    # Format current attributes
    attrs_text = _format_attributes(current_attributes)

    # Format missing elements with explanations
    missing_text = _format_missing_elements(missing_elements)

    # Format conversation history
    history_text = _format_history(conversation_history) if conversation_history else ""

    # Build accepted / uncertain context sections
    accepted_section = ""
    if accepted_fields:
        display_names = {
            "population": "Đối tượng nghiên cứu", "sample_size": "Cỡ mẫu",
            "primary_endpoint": "Kết cục chính", "intervention": "Can thiệp",
            "comparator": "Nhóm chứng", "exposure": "Phơi nhiễm",
            "follow_up_duration": "Thời gian theo dõi", "design_type": "Thiết kế nghiên cứu",
        }
        lines = [
            f"- {display_names.get(k, k.replace('_', ' '))}: \"{v}\""
            for k, v in accepted_fields.items() if v
        ]
        if lines:
            accepted_section = (
                f"\nVUA GHI NHAN ({len(lines)} truong trong luot nay):\n" + "\n".join(lines)
            )

    uncertain_section = ""
    if uncertain_fields:
        lines = [
            f"- {f.replace('_', ' ')}: User nhap \"{v}\" — {r} (hay hoi lai cu the hon)"
            for f, v, r in uncertain_fields
        ]
        uncertain_section = "\nCAN LAM RO LAI:\n" + "\n".join(lines)

    # Build the whitelist of allowed attribute_name values for the LLM
    allowed_names_list = "\n".join(f'  "{m}"' for m in missing_elements)

    prompt = f"""THONG TIN DA THU THAP:
{attrs_text if attrs_text else "Chua co thong tin nao."}
{accepted_section}
{uncertain_section}

THONG TIN CON THIEU:
{missing_text}

{f"LICH SU HOI THOAI:{chr(10)}{history_text}" if history_text else ""}

LUOT HOI DAP: {turn_number + 1}

NHIEM VU:
Dua tren thong tin tren, hay tao cac cau hoi de thu thap thong tin con thieu.
- Neu co truong "VỪA GHI NHẬN", hay de cap trong message rang minh da ghi nhan duoc (VD: "Mình đã ghi nhận X câu trả lời...").
- Neu co truong "CAN LAM RO LAI", hay dat cau hoi lai chi ve truong do.
- Uu tien cac thong tin QUAN TRONG NHAT (toi da 4 truong).
- Cau hoi phai cu the, tiep noi nguyen vong nguoi dung.

TUYET DOI QUAN TRONG - "attribute_name" trong moi form_field PHAI la mot trong nhung gia tri chinh xac sau (copy nguyen, khong sua, khong them chu):
{allowed_names_list}
Moi form_field chi duoc dung dung mot gia tri tu danh sach tren. Khong duoc tu dat ten khac.

HAY TRA LOI BANG DINH DANG JSON DUY NHAT NAY, KHONG THEM THE MARKDOWN:
{{
    "message": "Noi chuyen huong de cap truong da ghi nhan (neu co) va nhung gi can lam ro them.",
    "form_fields": [
        {{
            "attribute_name": "copy chinh xac tu danh sach tren, VD: primary_endpoint",
            "question_label": "Nhan hien thi bang tieng Viet (VD: 'Kết cục chính')",
            "description": "Mo ta / huong dan dien",
            "placeholder": "VD: Ty le tu vong sau 30 ngay..."
        }}
    ]
}}"""

    return prompt


def _format_attributes(attrs: ExtractedAttributes) -> str:
    """Format extracted attributes for display."""
    attr_dict = attrs.model_dump()
    lines = []

    display_names = {
        "population": "Dan so nghien cuu",
        "sample_size": "Co mau",
        "age_range": "Do tuoi",
        "intervention": "Can thiep",
        "comparator": "Doi chung",
        "exposure": "Phoi nhiem",
        "primary_endpoint": "Ket qua chinh",
        "secondary_endpoints": "Ket qua phu",
        "design_type": "Thiet ke",
        "setting": "Dia diem",
        "duration": "Thoi gian",
        "follow_up_duration": "Thoi gian theo doi",
        "case_definition": "Dinh nghia ca benh",
        "control_definition": "Dinh nghia nhom chung",
        "matching_criteria": "Tieu chi ghep cap",
        "reference_standard": "Tieu chuan vang",
        "search_strategy": "Chien luoc tim kiem",
        "databases": "Co so du lieu",
        "data_collection_method": "Phuong phap thu thap du lieu",
        "randomization_method": "Phuong phap ngau nhien",
        "blinding": "Lam mu",
        "data_source": "Nguon du lieu",
        "inclusion_criteria": "Tieu chuan chon",
        "exclusion_criteria": "Tieu chuan loai",
    }

    for key, display in display_names.items():
        value = attr_dict.get(key)
        if value:
            if hasattr(value, 'value'):  # Enum
                value = value.value
            elif isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            lines.append(f"- {display}: {value}")

    return "\n".join(lines)


def _format_missing_elements(elements: list[str]) -> str:
    """Format missing elements with explanations."""
    explanations = {
        "population": "Dan so nghien cuu (ai se duoc nghien cuu?)",
        "sample_size": "Co mau (bao nhieu benh nhan?)",
        "primary_endpoint": "Ket qua chinh (do luong gi?)",
        "intervention": "Can thiep (lam gi cho benh nhan?)",
        "comparator": "Nhom doi chung (so sanh voi gi?)",
        "exposure": "Yeu to phoi nhiem (yeu to nguy co nao?)",
        "design_type": "Thiet ke nghien cuu (RCT, cohort, cross-sectional...)",
        "follow_up_duration": "Thoi gian theo doi",
        "reference_standard": "Tieu chuan vang (gold standard)",
        "case_definition": "Dinh nghia ca benh",
        "control_definition": "Dinh nghia nhom chung",
        "matching_criteria": "Tieu chi ghep cap",
        "search_strategy": "Chien luoc tim kiem",
        "databases": "Co so du lieu se tim",
    }

    lines = []
    for elem in elements:
        explanation = explanations.get(elem, elem.replace("_", " "))
        lines.append(f"- {explanation}")

    return "\n".join(lines)


def _format_history(history: list[dict]) -> str:
    """Format conversation history."""
    lines = []
    for turn in history[-6:]:  # Last 6 turns
        role = "Nguoi dung" if turn.get("role") == "user" else "Tro ly"
        content = turn.get("content", "")[:200]  # Truncate
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def format_clarification_response(
    llm_response: str,
    missing_elements: list[str],
    turn_number: int
) -> dict:
    """
    Format LLM response for API return.

    Args:
        llm_response: Raw LLM response
        missing_elements: List of missing elements
        turn_number: Current turn number

    Returns:
        Formatted response dict
    """
    return {
        "message": llm_response.strip(),
        "missing_count": len(missing_elements),
        "turn_number": turn_number,
        "next_action": "continue" if missing_elements else "generate_abstract"
    }
