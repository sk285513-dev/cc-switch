import os

file_path = r"c:\Users\temp\antigravity\LexMind-Omni-法律實務-AI-工作站\src\App.tsx"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

start_anchor = "                    {/* Succeeded Result Preview Widget and Injection Action */}"
start_idx = content.find(start_anchor)
if start_idx == -1:
    print("Error: Start anchor not found")
    exit(1)

# Find the onClick={handleBatchIngest} element
button_idx = content.find("onClick={handleBatchIngest}", start_idx)
if button_idx == -1:
    print("Error: Ingest button not found")
    exit(1)

# Find the closing tags after the button
# We need to find </div> followed by some spaces and another </div>
search_from = button_idx
close_div_1 = content.find("</div>", search_from)
if close_div_1 == -1:
    print("Error: First closing div not found")
    exit(1)

close_div_2 = content.find("</div>", close_div_1 + 6)
if close_div_2 == -1:
    print("Error: Second closing div not found")
    exit(1)

end_pos = close_div_2 + 6

# Let's inspect what we are replacing
print(f"Replacing content from index {start_idx} to {end_pos}")
print("--- TARGET PREVIEW ---")
print(content[start_idx:start_idx+200])
print("...")
print(content[end_pos-200:end_pos])
print("----------------------")

replacement = """                    {/* Succeeded Result Preview Widget and Injection Action */}
                    {lastScrapedResult && (
                      <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="p-3 border border-slate-800 bg-slate-950/60 rounded-xl mt-1 flex flex-col gap-2 relative"
                      >
                        <div className="flex justify-between items-start gap-3">
                          <div className="flex-1">
                            <span className="text-[9px] font-bold text-slate-500 font-mono tracking-wider uppercase bg-slate-900 border border-slate-800 px-1.5 py-0.5 rounded">
                              ✨ 成功抓取預覽 | {lastScrapedResult.category}
                            </span>
                            <h4 className="text-[12px] font-bold text-white mt-1.5 font-display leading-tight">{lastScrapedResult.title}</h4>
                          </div>
                          <span className="text-[10px] text-slate-500 font-mono shrink-0">
                            {Math.round(lastScrapedResult.content.length)} 字
                          </span>
                        </div>
                        
                        <div className="text-[10px] text-slate-400 font-sans border-t border-slate-850/60 pt-2 line-clamp-3 leading-relaxed whitespace-pre-wrap">
                          {lastScrapedResult.content}
                        </div>

                        <div className="flex gap-2 mt-1">
                          <button
                            type="button"
                            onClick={handleEnqueueScrapedResult}
                            className="flex-1 py-1.5 bg-cyan-500/15 border border-cyan-500/35 hover:bg-cyan-500/25 active:bg-cyan-500/35 text-cyan-400 font-bold text-[11px] rounded-lg transition-all flex items-center justify-center gap-1 cursor-pointer"
                          >
                            <span>📥 自動匯入下方批次教材隊列</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => setLastScrapedResult(null)}
                            className="px-3 py-1.5 bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-355 text-[11px] rounded-lg transition-all cursor-pointer"
                          >
                            捨棄
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </div>

                  <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-xl flex flex-col gap-3">
                    <div className="flex justify-between items-center border-b border-slate-850 pb-2 mb-1">
                      <div className="flex gap-3">
                        <button
                          type="button"
                          onClick={() => setQueueTab("pending")}
                          className={`text-xs font-bold pb-1.5 transition-all cursor-pointer border-b-2 px-1 ${
                            queueTab === "pending"
                              ? "text-amber-500 border-amber-500"
                              : "text-slate-400 border-transparent hover:text-slate-200"
                          }`}
                        >
                          ⏳ 待校對隊列 ({batchTexts.length})
                        </button>
                        <button
                          type="button"
                          onClick={() => setQueueTab("vault")}
                          className={`text-xs font-bold pb-1.5 transition-all cursor-pointer border-b-2 px-1 ${
                            queueTab === "vault"
                              ? "text-amber-500 border-amber-500"
                              : "text-slate-400 border-transparent hover:text-slate-200"
                          }`}
                        >
                          📚 已入庫智商庫 ({vaultItems.length})
                        </button>
                      </div>
                      
                      {queueTab === "pending" ? (
                        batchTexts.length > 0 && (
                          <button 
                            type="button"
                            onClick={() => {
                              if (confirm("確定要清空材料隊列嗎？")) {
                                setBatchTexts([]);
                              }
                            }}
                            className="text-[10px] text-rose-450 hover:text-rose-350 flex items-center gap-1 cursor-pointer font-normal border-0 bg-transparent"
                          >
                            <Trash2 className="w-3.5 h-3.5" /> 清空隊列
                          </button>
                        )
                      ) : (
                        <button
                          type="button"
                          onClick={fetchVaultItems}
                          disabled={isVaultLoading}
                          className="text-[10px] text-slate-400 hover:text-slate-200 flex items-center gap-1 cursor-pointer font-normal border-0 bg-transparent"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${isVaultLoading ? "animate-spin" : ""}`} /> 重新整理
                        </button>
                      )}
                    </div>

                    {/* Global auto-correct rule engine action */}
                    {queueTab === "pending" && batchTexts.length > 0 && (
                      <div className="bg-amber-500/10 border border-amber-500/15 p-3 rounded-lg flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
                        <div className="flex items-center gap-2">
                          <span className="p-1 px-1.5 bg-amber-500/20 text-amber-400 font-bold rounded text-[9px] border border-amber-500/10 shrink-0 font-mono">
                            OFFLINE ENGINE
                          </span>
                          <p className="text-[11px] text-slate-300 font-sans leading-relaxed">
                            <b>LanguageTool 離線法律校對核心：</b>已自動在背景套用繁體法律術語和語音 (ASR) 混淆音判定規則。
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => {
                            const updated = batchTexts.map(f => ({
                              ...f,
                              content: autoCorrectText(f.content)
                            }));
                            setBatchTexts(updated);
                          }}
                          className="w-full sm:w-auto px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-lg font-bold text-[11px] transition-all flex items-center justify-center gap-1 shrink-0 border-none cursor-pointer"
                        >
                          <CheckCircle className="w-3.5 h-3.5 text-slate-950" />
                          一鍵校對修正全體隊列
                        </button>
                      </div>
                    )}

                    {/* Category Filter selector */}
                    <div className="bg-slate-950 border border-slate-855 rounded-lg p-2.5 flex flex-col gap-1.5">
                      <div className="text-[11px] text-slate-400 font-semibold tracking-wider flex items-center justify-between font-sans">
                        <span className="flex items-center gap-1 text-slate-300">🔍 教材標籤篩選器</span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          ⚖️ 判例(
                          {
                            queueTab === "pending"
                              ? batchTexts.filter(b => (b.category || classifyFileCategory(b.name)) === '判例').length
                              : vaultItems.filter(b => b.category === '判例').length
                          }
                          ) | 📁 證物(
                          {
                            queueTab === "pending"
                              ? batchTexts.filter(b => (b.category || classifyFileCategory(b.name)) === '證物').length
                              : vaultItems.filter(b => b.category === '證物').length
                          }
                          ) | 🎥 影音(
                          {
                            queueTab === "pending"
                              ? batchTexts.filter(b => ['學術錄影', '學術錄音'].includes(b.category || classifyFileCategory(b.name) || '')).length
                              : vaultItems.filter(b => ['學術錄影', '學術錄音'].includes(b.category || '')).length
                          }
                          )
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {[
                          { id: "all", label: "全部顯示", emoji: "🗂️" },
                          { id: "判例", label: "⚖️ 判例", emoji: "" },
                          { id: "證物", label: "📁 證物", emoji: "" },
                          { id: "學術錄影", label: "🎥 學術錄影", emoji: "" },
                          { id: "學術錄音", label: "📻 學術錄音", emoji: "" },
                          { id: "學術教材", label: "📖 學術教材", emoji: "" }
                        ].map((btn) => {
                          const count = btn.id === "all"
                            ? (queueTab === "pending" ? batchTexts.length : vaultItems.length)
                            : (queueTab === "pending"
                                ? batchTexts.filter(b => (b.category || classifyFileCategory(b.name)) === btn.id).length
                                : vaultItems.filter(b => b.category === btn.id).length);
                          const isActive = ingestFilter === btn.id;
                          return (
                            <button
                              key={btn.id}
                              type="button"
                              onClick={() => setIngestFilter(btn.id)}
                              className={`px-2.5 py-1 text-[11px] font-semibold rounded-md border transition-all cursor-pointer flex items-center gap-1 ${
                                isActive 
                                  ? "bg-amber-600/20 text-amber-455 border-amber-500/50 shadow-sm"
                                  : "bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200 hover:border-slate-700"
                              }`}
                            >
                              <span>{btn.emoji} {btn.label}</span>
                              <span className={`text-[10px] font-mono px-1 rounded-sm ${isActive ? "bg-amber-400/20 text-amber-300" : "bg-slate-950 text-slate-500"}`}>{count}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Integrated Search Input for Vault */}
                    {queueTab === "vault" && (
                      <div className="relative">
                        <input
                          type="text"
                          value={vaultSearchQuery}
                          onChange={(e) => setVaultSearchQuery(e.target.value)}
                          placeholder="🔍 搜尋已存入之教材名稱或逐字稿關鍵字（如：民法、上課錄影、判例）..."
                          className="w-full bg-slate-950 border border-slate-850 focus:border-amber-500/80 rounded-lg py-2 pl-3 pr-8 text-xs text-slate-350 focus:outline-none transition-all font-sans"
                        />
                        {vaultSearchQuery && (
                          <button
                            type="button"
                            onClick={() => setVaultSearchQuery("")}
                            className="absolute right-2.5 top-2.5 text-slate-500 hover:text-slate-300 bg-transparent border-0 cursor-pointer"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    )}

                    <div className="space-y-3.5 max-h-[480px] overflow-y-auto pr-1">
                      {queueTab === "pending" ? (
                        batchTexts.filter(file => {
                          if (ingestFilter === "all") return true;
                          const fileCat = file.category || classifyFileCategory(file.name);
                          return fileCat === ingestFilter;
                        }).length === 0 ? (
                          <div className="text-center py-8 bg-slate-950/40 border border-slate-850 rounded-lg">
                            <p className="text-xs text-slate-500 italic font-sans">此分類篩選下無任何檔案項目。</p>
                          </div>
                        ) : (
                          batchTexts.filter(file => {
                            if (ingestFilter === "all") return true;
                            const fileCat = file.category || classifyFileCategory(file.name);
                            return fileCat === ingestFilter;
                          }).map((file, idx) => {
                            const origIdx = batchTexts.findIndex(b => b.name === file.name);
                            const activeCat = file.category || classifyFileCategory(file.name);
                            
                            if (file.status === "error") {
                              return (
                                <div key={file.name + '-' + idx} className="p-3 bg-slate-950 border border-rose-950/40 rounded-lg flex flex-col gap-2.5 text-xs animate-[fadeIn_0.2s_ease-out]">
                                  <div className="flex justify-between items-center border-b border-slate-850 pb-1.5 mb-0.5 text-[11px] font-mono">
                                    <span className="text-rose-400 font-semibold truncate max-w-[280px]" title={file.name}>{file.name}</span>
                                    <span className="text-slate-500 shrink-0">
                                      {file.size ? `${(file.size / (1024 * 1024)).toFixed(2)} MB` : "失敗"} | UTF-8
                                    </span>
                                  </div>
                                  <div className="flex flex-wrap justify-between items-center gap-2 text-[10px] px-2 py-1.5 bg-slate-900/40 rounded border border-slate-855/30">
                                    <span className="text-slate-400 font-medium flex items-center gap-1.5">
                                      <span>🏫 預定分類:</span>
                                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold border ${
                                        activeCat === '判例' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' :
                                        activeCat === '證物' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                        activeCat === '學術錄影' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                                        activeCat === '學術錄音' ? 'bg-purple-500/10 text-purple-450 border-purple-500/20' :
                                        'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                                      }`}>
                                        {activeCat}
                                      </span>
                                    </span>
                                  </div>
                                  <div className="p-2 border border-rose-500/20 bg-rose-550/5 rounded-lg text-rose-400 text-[11px] font-sans flex items-start gap-2">
                                    <AlertTriangle className="w-4 h-4 text-rose-455 shrink-0 mt-0.5" />
                                    <div className="flex-1 flex flex-col gap-1">
                                      <span className="font-bold">❌ 解析失敗：</span>
                                      <span className="font-mono text-[10px] text-rose-300 leading-normal break-all">{file.error || "未知錯誤"}</span>
                                    </div>
                                  </div>
                                </div>
                              );
                            }

                            return (
                              <div key={file.name + '-' + idx} className="p-3 bg-slate-950 border border-slate-800 rounded-lg flex flex-col gap-2.5 text-xs animate-[fadeIn_0.2s_ease-out]">
                                <div className="flex justify-between items-center border-b border-slate-850 pb-1.5 mb-0.5 text-[11px] font-mono">
                                  <span className="text-amber-500 font-semibold truncate max-w-[280px]" title={file.name}>{file.name}</span>
                                  <span className="text-slate-500 shrink-0">{(file.content.length * 2 / 1024).toFixed(1)} KB | UTF-8</span>
                                </div>

                                {/* Classification Field */}
                                <div className="flex flex-wrap justify-between items-center gap-2 text-[10px] px-2 py-1.5 bg-slate-900/60 rounded border border-slate-800/40">
                                  <span className="text-slate-400 font-medium flex items-center gap-1.5">
                                    <span>🏫 自動學術分類:</span>
                                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold border ${
                                      activeCat === '判例' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' :
                                      activeCat === '證物' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                      activeCat === '學術錄影' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                                      activeCat === '學術錄音' ? 'bg-purple-500/10 text-purple-455 border-purple-500/20' :
                                      'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                                    }`}>
                                      {activeCat}
                                    </span>
                                  </span>
                                  <div className="flex items-center gap-1.5">
                                    <span className="text-slate-500 font-sans">分類變更:</span>
                                    <select
                                      value={activeCat}
                                      onChange={(e) => {
                                        if (origIdx !== -1) {
                                          const newArr = [...batchTexts];
                                          newArr[origIdx] = { ...newArr[origIdx], category: e.target.value as any };
                                          setBatchTexts(newArr);
                                        }
                                      }}
                                      className="bg-slate-950 border border-slate-800 text-slate-300 rounded px-1.5 py-0.5 text-[10px] focus:outline-none focus:border-amber-500/80 cursor-pointer"
                                    >
                                      <option value="判例">⚖️ 判例</option>
                                      <option value="證物">📁 證物</option>
                                      <option value="學術錄影">🎥 學術錄影</option>
                                      <option value="學術錄音">📻 學術錄音</option>
                                      <option value="學術教材">📖 學術教材</option>
                                    </select>
                                  </div>
                                </div>

                                {/* Real-time spelling & Taiwanese legal terminology proofreading */}
                                {(() => {
                                  const detected = proofreadText(file.content);
                                  if (detected.length === 0) return null;
                                  return (
                                    <div className="bg-amber-500/5 border border-amber-500/20 p-2.5 rounded-lg flex flex-col gap-1.5 animate-[fadeIn_0.2s_ease-out]">
                                      <div className="flex items-center justify-between text-amber-400 font-bold text-[10px] font-sans">
                                        <span className="flex items-center gap-1">
                                          <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                                          ⚠️ 偵測到 {detected.length} 處疑似語音或法律術語標記錯誤
                                        </span>
                                        <button
                                          type="button"
                                          onClick={() => {
                                            if (origIdx !== -1) {
                                              const newArr = [...batchTexts];
                                              newArr[origIdx].content = autoCorrectText(file.content);
                                              setBatchTexts(newArr);
                                            }
                                          }}
                                          className="px-2 py-0.5 bg-amber-500/20 hover:bg-amber-500 text-amber-300 hover:text-slate-950 rounded font-bold text-[10px] transition-all flex items-center gap-1 border border-amber-500/30 cursor-pointer active:scale-95"
                                        >
                                          <span>⚡ 一鍵本卡校正</span>
                                        </button>
                                      </div>
                                      <div className="flex flex-wrap gap-1 max-h-[85px] overflow-y-auto pr-1 pad-y-0.5 font-sans">
                                        {detected.map((match, mIdx) => (
                                          <span 
                                            key={match.id + '-' + mIdx} 
                                            className="inline-flex items-center bg-slate-950 border border-slate-850 rounded px-1.5 py-0.5 text-[10px] text-slate-300 font-mono select-none"
                                            title={`${match.reason} (建議修正為：${match.correct})`}
                                          >
                                            <span className="text-rose-455 line-through mr-1">{match.suspect}</span>
                                            <span className="text-slate-600">➔</span>
                                            <span className="text-emerald-450 font-bold ml-1">{match.correct}</span>
                                          </span>
                                        ))}
                                      </div>
                                      <p className="text-[9px] text-slate-500 italic leading-none font-sans mt-0.5">
                                        提示：將滑鼠游標停留在出錯點上方，即可參閱 LanguageTool 智慧法學解析依據。
                                      </p>
                                    </div>
                                  );
                                })()}

                                <textarea 
                                  value={file.content}
                                  onChange={(e) => {
                                    if (origIdx !== -1) {
                                      const newArr = [...batchTexts];
                                      newArr[origIdx].content = e.target.value;
                                      setBatchTexts(newArr);
                                    }
                                  }}
                                  rows={3}
                                  className="w-full bg-slate-900 border border-slate-850 text-slate-400 focus:outline-none focus:text-slate-100 rounded p-1.5 leading-normal mt-0.5 font-sans"
                                />
                              </div>
                            );
                          })
                        )
                      ) : (
                        (() => {
                          const filteredVaultItems = vaultItems.filter(item => {
                            // Category filter
                            if (ingestFilter !== "all") {
                              const fileCat = item.category || "學術教材";
                              if (fileCat !== ingestFilter) return false;
                            }
                            // Search filter
                            const q = vaultSearchQuery.toLowerCase().trim();
                            if (q) {
                              const matchesSource = item.source && item.source.toLowerCase().includes(q);
                              const matchesText = item.text && item.text.toLowerCase().includes(q);
                              const matchesCat = item.category && item.category.toLowerCase().includes(q);
                              if (!matchesSource && !matchesText && !matchesCat) return false;
                            }
                            return true;
                          });

                          if (filteredVaultItems.length === 0) {
                            return (
                              <div className="text-center py-8 bg-slate-950/40 border border-slate-855 border-dashed rounded-lg">
                                <p className="text-xs text-slate-500 italic font-sans">此篩選條件下智商庫無任何教材項目。</p>
                              </div>
                            );
                          }

                          return filteredVaultItems.map((item, idx) => {
                            const activeCat = item.category || "學術教材";
                            const fileExt = item.source.split('.').pop()?.toUpperCase() || "TXT";
                            
                            return (
                              <div key={item.id || idx} className="p-3 bg-slate-955 border border-slate-800 rounded-lg flex flex-col gap-2.5 text-xs animate-[fadeIn_0.2s_ease-out]">
                                <div className="flex justify-between items-center border-b border-slate-850 pb-1.5 mb-0.5 text-[11px] font-mono">
                                  <span className="text-amber-500 font-semibold truncate max-w-[250px]" title={item.source}>📄 {item.source}</span>
                                  <span className="text-slate-500 shrink-0">{(item.text ? item.text.length : 0)} 字 | {fileExt}</span>
                                </div>

                                {/* Classification Field */}
                                <div className="flex flex-wrap justify-between items-center gap-2 text-[10px] px-2 py-1.5 bg-slate-900/60 rounded border border-slate-800/40">
                                  <span className="text-slate-400 font-medium flex items-center gap-1.5">
                                    <span>🏫 目前智商分類:</span>
                                    <span className={`px-2 py-0.5 rounded text-[9px] font-bold border ${
                                      activeCat === '判例' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' :
                                      activeCat === '證物' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                      activeCat === '學術錄影' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' :
                                      activeCat === '學術錄音' ? 'bg-purple-500/10 text-purple-450 border-purple-500/20' :
                                      'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                                    }`}>
                                      {activeCat}
                                    </span>
                                  </span>
                                  <div className="flex items-center gap-1.5">
                                    <span className="text-slate-500 font-sans">分類變更:</span>
                                    <select
                                      value={activeCat}
                                      onChange={(e) => {
                                        const updated = vaultItems.map(vi => vi.id === item.id ? { ...vi, category: e.target.value } : vi);
                                        setVaultItems(updated);
                                      }}
                                      className="bg-slate-950 border border-slate-800 text-slate-300 rounded px-1.5 py-0.5 text-[10px] focus:outline-none focus:border-amber-500/80 cursor-pointer"
                                    >
                                      <option value="判例">⚖️ 判例</option>
                                      <option value="證物">📁 證物</option>
                                      <option value="學術錄影">🎥 學術錄影</option>
                                      <option value="學術錄音">📻 學術錄音</option>
                                      <option value="學術教材">📖 學術教材</option>
                                    </select>
                                  </div>
                                </div>

                                {/* Real-time spelling & Taiwanese legal terminology proofreading */}
                                {(() => {
                                  const detected = proofreadText(item.text || "");
                                  if (detected.length === 0) return null;
                                  return (
                                    <div className="bg-amber-500/5 border border-amber-500/20 p-2.5 rounded-lg flex flex-col gap-1.5 animate-[fadeIn_0.2s_ease-out]">
                                      <div className="flex items-center justify-between text-amber-400 font-bold text-[10px] font-sans">
                                        <span className="flex items-center gap-1">
                                          <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                                          ⚠️ 偵測到 {detected.length} 處疑似語音或法律術語標記錯誤
                                        </span>
                                        <button
                                          type="button"
                                          onClick={() => {
                                            const updated = vaultItems.map(vi => vi.id === item.id ? { ...vi, text: autoCorrectText(vi.text) } : vi);
                                            setVaultItems(updated);
                                          }}
                                          className="px-2 py-0.5 bg-amber-500/20 hover:bg-amber-500 text-amber-300 hover:text-slate-950 rounded font-bold text-[10px] transition-all flex items-center gap-1 border border-amber-500/30 cursor-pointer active:scale-95"
                                        >
                                          <span>⚡ 一鍵本卡校正</span>
                                        </button>
                                      </div>
                                      <div className="flex flex-wrap gap-1 max-h-[85px] overflow-y-auto pr-1 pad-y-0.5 font-sans">
                                        {detected.map((match, mIdx) => (
                                          <span 
                                            key={match.id + '-' + mIdx} 
                                            className="inline-flex items-center bg-slate-950 border border-slate-850 rounded px-1.5 py-0.5 text-[10px] text-slate-300 font-mono select-none"
                                            title={`${match.reason} (建議修正為：${match.correct})`}
                                          >
                                            <span className="text-rose-455 line-through mr-1">{match.suspect}</span>
                                            <span className="text-slate-600">➔</span>
                                            <span className="text-emerald-450 font-bold ml-1">{match.correct}</span>
                                          </span>
                                        ))}
                                      </div>
                                    </div>
                                  );
                                })()}

                                <textarea 
                                  value={item.text || ""}
                                  onChange={(e) => {
                                    const updated = vaultItems.map(vi => vi.id === item.id ? { ...vi, text: e.target.value } : vi);
                                    setVaultItems(updated);
                                  }}
                                  rows={4}
                                  className="w-full bg-slate-900 border border-slate-850 text-slate-400 focus:outline-none focus:text-slate-100 rounded p-1.5 leading-normal mt-0.5 font-sans"
                                />

                                {/* Save, Copy, Delete Inline Buttons */}
                                <div className="flex justify-between items-center gap-2 mt-1 pt-1.5 border-t border-slate-900/60">
                                  <button
                                    type="button"
                                    onClick={() => deleteVaultItem(item.id)}
                                    className="px-2 py-1 bg-rose-500/10 hover:bg-rose-500 hover:text-white border border-rose-500/20 text-rose-400 rounded text-[10px] transition-all cursor-pointer flex items-center gap-1 active:scale-95 border-none"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                    <span>🗑️ 永久刪除</span>
                                  </button>
                                  <div className="flex gap-2">
                                    <button
                                      type="button"
                                      onClick={() => {
                                        navigator.clipboard.writeText(item.text || "");
                                        showAlert("📋 全文已成功複製到剪貼簿！");
                                      }}
                                      className="px-2 py-1 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-355 rounded text-[10px] transition-all cursor-pointer flex items-center gap-1 active:scale-95"
                                    >
                                      <span>複製全文</span>
                                    </button>
                                    <button
                                      type="button"
                                      onClick={() => updateVaultItem(item.id, item.text, item.category)}
                                      className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-[10px] font-bold transition-all cursor-pointer flex items-center gap-1 active:scale-95 border-none"
                                    >
                                      <span>💾 儲存修改</span>
                                    </button>
                                  </div>
                                </div>
                              </div>
                            );
                          });
                        })()
                      )}
                    </div>

                    {queueTab === "pending" && (
                      <button 
                        onClick={handleBatchIngest}
                        disabled={isIngesting}
                        className="w-full py-3 bg-gradient-to-r from-amber-600 to-amber-700 text-white rounded-lg font-semibold hover:brightness-110 active:brightness-95 transition-all cursor-pointer text-xs flex items-center justify-center gap-2 mt-2 border-none"
                      >
                        {isIngesting ? <RefreshCw className="w-4 h-4 animate-spin text-white" /> : "🚀 確認校對無誤，開始智慧消化並寫入資料庫/智商庫"}
                      </button>
                    )}
                  </div>
                </div>"""

new_content = content[:start_idx] + replacement + content[end_pos:]

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Replacement successful!")
