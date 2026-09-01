"""
QUY ĐỊNH BẤT BIẾN (HARD-CODED WHITELIST) VỀ TƯ CÁCH ĐỐI TƯỢNG LIÊN HỆ
Không thể cấu hình qua Policy File. Thay đổi file này bắt buộc phải qua Release Code và duyệt 4 mắt.
Căn cứ: NĐ 117/2018/NĐ-CP, TT 18/2019/TT-NHNN, Luật BVDLCN 91/2025/QH15.
"""

# Danh mục 4 quan hệ ĐƯỢC PHÉP liên hệ trực tiếp vì có nghĩa vụ pháp lý đối với khoản nợ
ELIGIBLE_OBLIGATION_EDGES = {
    "BORROWED": "Chính chủ khoản vay / Bên vay",
    "CO_BORROWER_WITH": "Đồng vay / Cùng chịu nghĩa vụ",
    "GUARANTEES": "Bên bảo lãnh / Cam kết trả nợ thay",
    "LEGAL_REP_OF": "Người đại diện theo pháp luật của Pháp nhân vay"
}

# Danh mục quan hệ CÓ ĐIỀU KIỆN (chỉ được phép khi có ủy quyền hợp lệ hoặc có sự đồng ý)
CONDITIONAL_EDGES = {
    "AUTHORIZED_BY": "Người được ủy quyền hợp pháp (Có văn bản)",
    "REFERENCE_CONTACT_OF": "Người tham chiếu (BẮT BUỘC có consent_obtained=True)"
}

# Danh mục quan hệ CẤM TUYỆT ĐỐI LIÊN HỆ ĐÒI NỢ (Hard-blocked by Schema)
PROHIBITED_EDGES = {
    "FAMILY_OF": "Người thân (Bố, mẹ, vợ, chồng, con, anh chị em không bảo lãnh)",
    "EMPLOYED_BY": "Nơi làm việc, đồng nghiệp, cấp trên",
    "SHARES_PHONE": "Người trùng số điện thoại (Chỉ dùng cho Entity Resolution)",
    "SHARES_ADDRESS": "Người cùng địa chỉ cư trú",
    "RELATED_PARTY_OF": "Người có liên quan theo Luật TCTD (Chỉ dùng cho Risk Limit)"
}
