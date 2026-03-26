"""Prompt for generating highly optimized PubMed search queries."""

from app.models.schemas import ResearchBlueprint

SYSTEM_PROMPT = (
    "You are an expert medical librarian and literature search specialist. "
    "Your objective is to generate highly optimized, perfectly formatted PubMed search queries."
)

def get_pubmed_query_prompt(blueprint: ResearchBlueprint) -> str:
    """Generate prompt to convert blueprint into PubMed search query."""
    return f"""Nhiệm vụ: Chuyển đổi ý tưởng nghiên cứu sau (hiện đang bằng tiếng Việt) thành MỘT chuỗi (string) tìm kiếm PubMed tối ưu nhất bằng tiếng Anh.

YÊU CẦU BẮT BUỘC ĐỐI VỚI CHUỖI TÌM KIẾM (PUBMED QUERY):
1. **Dịch sang tiếng Anh**: Tất cả các khái niệm y khoa phải được dịch sang thuật ngữ chuẩn tiếng Anh (MeSH/tiếng Anh thông dụng).
2. **Sử dụng từ đồng nghĩa (Synonyms)**: Nhóm các từ đồng nghĩa hoặc các cách viết khác nhau bằng toán tử `OR` và gom trong ngoặc đơn. Ví dụ: `(children[tiab] OR pediatric*[tiab] OR infant*[tiab])`.
3. **Sử dụng trường [tiab]**: TẤT CẢ các khái niệm tìm kiếm đều phải gắn thẻ `[tiab]` (Title/Abstract) ngay phía sau từ khóa để tránh tìm kiếm rác. Không bao giờ bỏ sót đuôi `[tiab]`.
4. **Kết nối các cụm khái niệm**: Dùng toán tử `AND` giữa các nhóm khái niệm chính yếu (Ví dụ: Đối tượng AND Can thiệp AND Kết cục).
5. **Đơn giản hóa ý tưởng**: Không được cố dịch từng từ một. Chỉ nhặt ra 2-4 KHÁI NIỆM MỐT CHỐT CỐT LÕI (core aspects). Nếu có quá nhiều điều kiện nhỏ nhặt (ví dụ "tại bệnh viện", "tuổi từ 18-60", "trong vòng 6 tháng"), hãy *Loại bỏ* chúng để tránh việc PubMed trả về 0 kết quả (over-restricting).
6. FORMAT ĐẦU RA: BẠN CHỈ TRẢ VỀ ĐÚNG 1 CHUỖI STRING QUERY DUY NHẤT. KHÔNG KÈM THEO BẤT KỲ CÂU CHÀO HAY LỜI GIẢI THÍCH NÀO (Không có markdown).
Ví dụ Output tuyệt đối chuẩn xác:
((myocardial infarction*[tiab] OR heart attack*[tiab]) AND (aspirin*[tiab] OR salicylic acid[tiab]) AND (mortality[tiab] OR survival*[tiab]))

---
THÔNG TIN NGHIÊN CỨU HIỆN TẠI TỪ NGƯỜI DÙNG:
- Điểm đánh giá dự kiến (Outcome/Endpoint): {blueprint.primary_outcome or 'Không rõ'}
- Đối tượng (Population): {blueprint.population or 'Không rõ'}
- Can thiệp/Phơi nhiễm (Intervention/Exposure): {blueprint.intervention_or_exposure or 'Không rõ'}
- Nhóm chứng (Comparator): {blueprint.comparator or 'Không rõ'}
- Thiết kế (Design Type): {blueprint.design_type or 'Không rõ'}

TRẢ VỀ CHUỖI PUBMED QUERY NGAY DƯỚI ĐÂY:"""
