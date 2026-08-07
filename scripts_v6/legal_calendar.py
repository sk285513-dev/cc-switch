import datetime
from dateutil.relativedelta import relativedelta

class LegalCalendarPlugin:
    def is_holiday(self, check_date: datetime.date) -> bool:
        # 判斷是否為週六或週日（民法 §122 例假日延展）
        return check_date.weekday() in [5, 6]

    def calculate_deadline(self, event_date_str: str, statute_type: str):
        try:
            event_date = datetime.datetime.strptime(event_date_str.strip(), "%Y-%m-%d").date()
        except ValueError:
            return {"error": "日期格式錯誤，請採用 YYYY-MM-DD 格式。"}

        # 基礎原則：始日不算入（民法 §120 第2項）
        start_compute_date = event_date + datetime.timedelta(days=1)

        if statute_type == "civil_tort":
            raw_end_date = event_date + relativedelta(years=2)
            duration_desc = "民事侵權行為請求權時效（2年）"
        elif statute_type == "civil_general":
            raw_end_date = event_date + relativedelta(years=15)
            duration_desc = "一般民事請求權時效（15年）"
        elif statute_type == "public_wage":
            raw_end_date = event_date + relativedelta(years=5)
            duration_desc = "公法上請求權 / 定期工資給付時效（5年）"
        elif statute_type == "labor_30d":
            # 以日定期間者，第 30 天為最終日
            raw_end_date = start_compute_date + datetime.timedelta(days=29)
            duration_desc = "勞動基準法第14條不經預告終止契約權（30日除斥期間）"
        else:
            return {"error": "未知的時效類型。"}

        # 適用民法 §122 末日逢例假日順延原則
        final_deadline = raw_end_date
        holiday_extended = False
        extended_days = 0

        while self.is_holiday(final_deadline):
            final_deadline += datetime.timedelta(days=1)
            holiday_extended = True
            extended_days += 1

        return {
            "status": "success",
            "statute_name": duration_desc,
            "event_date": str(event_date),
            "start_compute_date": str(start_compute_date),
            "raw_end_date": str(raw_end_date),
            "final_deadline": str(final_deadline),
            "holiday_extended": holiday_extended,
            "extended_days": extended_days,
            "legal_basis": "依據中華民國民法第120條第2項始日不算、第121條及第122條末日逢假日順延原則計算。",
            # 【修復 Issue 16】加入 Human-in-the-loop 的前端 UI 暫停確認機制防範 NLP 幻覺
            "requires_human_confirmation": True,
            "human_prompt": f"⚠️ 【時效警告】本案 {duration_desc} 計算之最後期限為 {final_deadline}，請律師/法務人員務必人工核對，確認是否提早遞狀以保全權利！"
        }
