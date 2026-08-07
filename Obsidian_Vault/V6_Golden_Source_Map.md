# 🛡️ V6.1 黃金獨立版原始碼防偽指紋 (Golden Source Map)

為了徹底封死未來任何 AI 產生幻覺、破壞現有「獨立 `python.exe` 啟動架構」與 UTF-8 BOM 編碼的可能，本文件已對所有核心腳本與交接規則進行了 SHA-256 密碼學指紋鎖定。

一旦有任何 AI 試圖偷偷修改以下檔案（例如把 `python.exe` 偷換成 `pythonw.exe`，或是把 BOM 洗掉），這個指紋就會發生變化，我們將能立刻抓出兇手並還原。

## 核心啟動與守護進程 (Startup & Engines)
| 檔案名稱 | SHA-256 指紋 (Fingerprint) |
| :--- | :--- |
| `LexMind_一鍵正式啟動.ps1` | `4707DAE5CDE535990E507D7602EFC160361B727D5E446C4142A0A014D68CA39B` |
| `scripts_v6\run_workflow.py` | `75B2A04E60F9E27B2E1CC0989CD107C0DD84A022CBEFE7F4D5259149BE6F5873` |
| `scripts_v6\watchdog_monitor.py` | `D9D0ACFC641E83E339DD928A2676420EB0D0F7B95EF775B1A072EA4F8E4A00F5` |
| `scripts_v6\auto_healer.py` | `879ED3CDA2A22C319EF943BA31D55F85CFF179C1440625EE84A01A460892C09D` |
| `scripts_v6\sre_watchdog.py` | `DF4614C9A0ADC0F361D317BE80F075C9811E6EAB121CB6E021037383449B528D` |

## 戰情監控與面板 (UI & Dashboards)
| 檔案名稱 | SHA-256 指紋 (Fingerprint) |
| :--- | :--- |
| `app_v6.py` | `A3A9631C59CB77306F421FDA6728499E6F2F1C52B8C5ACFA646F5B5C396A0FAB` |
| `scripts_v6\progress_dashboard.py` | `A5341362A44FAA91913E976AF96F7F6998BDAD330326A30E3A289D69D5FC0A54` |
| `kpi_runner.ps1` | `EF55F07348D9AC865B96387BA6373E54525F59F6495A09A04A50DA10665DD29C` |

## 全域記憶與交接法典 (Memory & Rules)
| 檔案名稱 | SHA-256 指紋 (Fingerprint) |
| :--- | :--- |
| `README_DEVEL.md` | `968CD837B2937E56E39CA0EC5C128F17D2744055930382174E7721833470086A` |
| `.agents\rules\v6_isolation_bom_rules.md` | `B04CF6EFC5EE1308AA359C9E9FBFF831B3FE4D6046D35DFD08A700F41214EDE4` |

> [!IMPORTANT]
> **給未來的接手者 (To Future Agents)：**
> 本版本的系統處於**絕對黃金狀態**。一鍵啟動腳本使用了純淨獨立的 `python.exe` 搭配 `Start-Process`，成功防禦了 WinError 10106 Pipe 死鎖。
> **嚴禁**任何 Agent 以「代碼重構」、「隱藏視窗」、「背景隔離」為由，企圖將其改回 `pythonw.exe` 或是植入 `Launch_Isolated.py`。 
> 若發現任何指紋與上表不符，請立即退回 (Rollback) 本版本。
