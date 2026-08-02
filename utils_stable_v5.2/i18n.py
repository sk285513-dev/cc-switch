import os

# 簡單的記憶體內建翻譯字典 (支援 zh_TW 與 en_US)
TRANSLATIONS = {
    "en_US": {
        "💬 實務辯護諮詢": "💬 Defense Consult",
        "📥 知識餵養 (影音 & 書狀)": "📥 Knowledge Ingest",
        "📂 法律個案管理": "📂 Case Management",
        "🔍 教材檢索與定位": "🔍 Material Search",
        "🎓 司法官自我養成": "🎓 Judicial Training",
        "📝 訴訟書狀起草": "📝 Pleading Draft",
        "⚙️ 系統與時效工具": "⚙️ System & Tools",
        "🤖 Antigravity 控制台": "🤖 Antigravity Console",
        "🌐 系統介面語言 (Language)": "🌐 System UI Language",
        "繁體中文 (zh_TW)": "Traditional Chinese (zh_TW)",
        "英文 (en_US)": "English (en_US)",
        "儲存並套用設定": "Save & Apply Settings",
        "設定已成功儲存！重新載入中...": "Settings saved! Reloading...",
        "重新整理 (Refresh)": "Refresh",
        "LexMind-Omni 臺灣法律 AI 工作站": "LexMind-Omni Legal AI Workstation",
        "臺灣法律實務專業級 AI Agent 特助整合工作站": "Taiwan Legal Practice Professional AI Agent Workstation",
        "系統管理員面板": "System Administrator Panel"
    }
}

class I18nManager:
    def __init__(self):
        self.current_lang = "zh_TW"  # Default

    def set_language(self, lang):
        if lang in ["zh_TW", "en_US"]:
            self.current_lang = lang

    def gettext(self, text):
        if self.current_lang == "zh_TW":
            return text
        
        # 尋找對應的英文翻譯，若找不到則回傳原文
        lang_dict = TRANSLATIONS.get(self.current_lang, {})
        return lang_dict.get(text, text)

# 全域單例
_i18n_instance = I18nManager()

def set_language(lang):
    _i18n_instance.set_language(lang)

def _(text):
    return _i18n_instance.gettext(text)
