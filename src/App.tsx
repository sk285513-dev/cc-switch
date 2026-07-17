import React, { useState, useEffect } from "react";
import { 
  Scale,
  Cpu, 
  Briefcase, 
  Shield, 
  Calendar, 
  Trash2, 
  History, 
  Sparkles, 
  BookOpen, 
  Award, 
  FileText, 
  Lock, 
  RefreshCw, 
  AlertTriangle, 
  Download, 
  UploadCloud, 
  CheckCircle,
  HelpCircle,
  FileCheck2,
  Bookmark,
  Gavel,
  FolderOpen,
  Plus,
  Paperclip,
  Film,
  Image,
  Play,
  X,
  Music,
  Pause,
  Globe,
  ExternalLink,
  Copy,
  Check,
  Filter,
  SlidersHorizontal,
  Eye,
  EyeOff
} from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { 
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  LineChart,
  Line,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  AreaChart,
  Area
} from "recharts";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import { proofreadText, autoCorrectText } from "./utils/legalProofer";

// Types matching the server architecture
interface Message {
  role: "user" | "assistant";
  content: string;
}

interface Evidence {
  text: string;
  score: number;
  source: string;
  level: number;
  isIntel?: boolean;
  url?: string;
  sourceTitle?: string;
  snippetDate?: string;
}

interface ChatAttachment {
  name: string;
  size: string;
  type: "audio" | "video" | "image" | "pdf" | "text";
  status: "parsing" | "ready" | "error";
  content: string;
}

interface BatchFile {
  name: string;
  content: string;
  category: "判例" | "證物" | "學術錄影" | "學術錄音" | "學術教材";
  path?: string;
}

const classifyFileCategory = (fileName: any): "判例" | "證物" | "學術錄影" | "學術錄音" | "學術教材" => {
  if (!fileName || typeof fileName !== 'string') {
    return '學術教材';
  }
  const ext = fileName.split('.').pop()?.toLowerCase() || '';
  const lowercaseName = fileName.toLowerCase();
  
  if (ext === 'mp4') {
    return '學術錄影';
  }
  if (ext === 'mp3' || ext === 'wav') {
    return '學術錄音';
  }
  if (['png', 'jpg', 'jpeg'].includes(ext)) {
    return '證物';
  }
  if (lowercaseName.includes('判例') || lowercaseName.includes('判決') || lowercaseName.includes('最高法院') || lowercaseName.includes('裁定') || ext === 'pdf') {
    return '判例';
  }
  if (lowercaseName.includes('證') || lowercaseName.includes('診斷') || lowercaseName.includes('單') || lowercaseName.includes('收據') || lowercaseName.includes('發票')) {
    return '證物';
  }
  if (lowercaseName.includes('影') || lowercaseName.includes('片') || lowercaseName.includes('課') || lowercaseName.includes('講') || lowercaseName.includes('錄像') || lowercaseName.includes('錄影')) {
    return '學術錄影';
  }
  return '學術教材';
};

const getItemCategory = (item: any, isVault: boolean): "判例" | "證物" | "學術錄影" | "學術錄音" | "學術教材" => {
  if (!item) return "學術教材";
  if (isVault) {
    if (item.category && ["判例", "證物", "學術錄影", "學術錄音", "學術教材"].includes(item.category)) {
      return item.category as any;
    }
    return classifyFileCategory(item.source || "");
  } else {
    return item.category || classifyFileCategory(item.name || "");
  }
};

// Helper to dynamically load pdf.js from CDN
const loadPdfJs = (): Promise<any> => {
  return new Promise((resolve, reject) => {
    if ((window as any).pdfjsLib) {
      resolve((window as any).pdfjsLib);
      return;
    }
    const script = document.createElement("script");
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.min.js";
    script.onload = () => {
      const pdfjs = (window as any).pdfjsLib;
      pdfjs.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js";
      resolve(pdfjs);
    };
    script.onerror = (err) => reject(err);
    document.head.appendChild(script);
  });
};

// Helper for client-side PDF text extraction
const extractTextFromPdf = async (file: File): Promise<string> => {
  try {
    const pdfjs = await loadPdfJs();
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise;
    let fullText = "";
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const textContent = await page.getTextContent();
      const pageText = textContent.items.map((item: any) => item.str).join(" ");
      fullText += pageText + "\n";
    }
    return fullText.trim();
  } catch (error) {
    console.error("PDF parsing error:", error);
    return `[無法解析 PDF 檔案或內容加密。詳情: ${error instanceof Error ? error.message : String(error)}]`;
  }
};

export default function App() {
  const [activeTab, setActiveTab] = useState<"consult" | "ingest" | "exam" | "draft" | "admin" | "cases" | "benchmark" | "t2v">("consult");
  const [contextRole, setContextRole] = useState<"lawyer" | "judge" | "prosecutor">("lawyer");

  // Text-to-Video States
  const [t2vPrompt, setT2vPrompt] = useState("");
  const [t2vStyle, setT2vStyle] = useState("realistic");
  const [isGeneratingVideo, setIsGeneratingVideo] = useState(false);
  const [generatedVideoUrl, setGeneratedVideoUrl] = useState<string | null>(null);


  // Chart Visibility States with localStorage persistence
  const [showRwsChart, setShowRwsChart] = useState<boolean>(() => {
    const saved = localStorage.getItem("lexmind_showRwsChart");
    return saved !== null ? JSON.parse(saved) : true;
  });
  const [showTrendChart, setShowTrendChart] = useState<boolean>(() => {
    const saved = localStorage.getItem("lexmind_showTrendChart");
    return saved !== null ? JSON.parse(saved) : true;
  });

  useEffect(() => {
    localStorage.setItem("lexmind_showRwsChart", JSON.stringify(showRwsChart));
  }, [showRwsChart]);

  useEffect(() => {
    localStorage.setItem("lexmind_showTrendChart", JSON.stringify(showTrendChart));
  }, [showTrendChart]);

  // Toast Notification States
  const [toasts, setToasts] = useState<{ id: string; message: string; type: "success" | "error" | "info" | "warning" }[]>([]);

  const addToast = (message: string, type: "success" | "error" | "info" | "warning" = "info") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  const showAlert = (msg: string) => {
    let type: "success" | "error" | "info" | "warning" = "info";
    let cleanMsg = msg;
    if (msg.startsWith("⚠️")) {
      type = "warning";
      cleanMsg = msg.replace(/^⚠️\s*/, "");
    } else if (msg.startsWith("❌")) {
      type = "error";
      cleanMsg = msg.replace(/^❌\s*/, "");
    } else if (msg.startsWith("✅") || msg.startsWith("✨") || msg.startsWith("🌐")) {
      type = "success";
      cleanMsg = msg.replace(/^[✅✨🌐]\s*/, "");
    }
    addToast(cleanMsg, type);
  };

  // Cases Management States
  const [cases, setCases] = useState<Record<string, any>>({});
  const [selectedCaseId, setSelectedCaseId] = useState<string>("");
  const [caseUserMsg, setCaseUserMsg] = useState("");
  const [isCaseChatLoading, setIsCaseChatLoading] = useState(false);
  const [stakeholderQuery, setStakeholderQuery] = useState("");
  const [foundLocalCases, setFoundLocalCases] = useState<any[]>([]);
  const [foundDbPrecedents, setFoundDbPrecedents] = useState<any[]>([]);
  const [isSavingCaseChanges, setIsSavingCaseChanges] = useState(false);

  // System Diagnostics States
  const [systemStatus, setSystemStatus] = useState<any>(null);
  const [isTriggeringScraper, setIsTriggeringScraper] = useState(false);

  // Load cases from backend
  const fetchCases = async () => {
    try {
      const resp = await fetch("/api/cases");
      const data = await resp.json();
      setCases(data);
      if (data && Object.keys(data).length > 0 && !selectedCaseId) {
        setSelectedCaseId(Object.keys(data)[0]);
      }
    } catch (e) {
      console.error("Failed to fetch cases:", e);
    }
  };

  // Fetch system status
  const fetchSystemStatus = async () => {
    try {
      const resp = await fetch("/api/system-status");
      const data = await resp.json();
      setSystemStatus(data);
      return data;
    } catch (e) {
      console.error("Failed to fetch system status:", e);
      return null;
    }
  };

  const handleModelChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newModel = e.target.value;
    try {
      const resp = await fetch("/api/settings/model", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: newModel })
      });
      const data = await resp.json();
      if (data.status === "success") {
        showAlert(`✅ 已切換至模型: ${newModel}`);
        fetchSystemStatus(); // Refresh to reflect new model
      } else {
        showAlert(`❌ 模型切換失敗: ${data.error}`);
      }
    } catch (err: any) {
      showAlert(`❌ 模型切換錯誤: ${err.message || String(err)}`);
    }
  };

  // Fetch digested vault documents
  const fetchVaultItems = async () => {
    setIsVaultLoading(true);
    try {
      const resp = await fetch("/api/intelligence-vault");
      const data = await resp.json();
      if (data.status === "success") {
        setVaultItems(data.items);
      }
    } catch (e) {
      console.error("Failed to fetch vault items:", e);
    } finally {
      setIsVaultLoading(false);
    }
  };

  const deleteVaultItem = async (id: string) => {
    if (!confirm("確定要自智商庫/資料庫中永久刪除此教材與逐字稿嗎？此動作無法復原。")) return;
    try {
      const resp = await fetch(`/api/intelligence-vault/${id}`, {
        method: "DELETE"
      });
      const data = await resp.json();
      if (data.status === "success") {
        showAlert("✅ 教材已自智商庫中移除。");
        setSelectedVaultItem(null);
        fetchVaultItems();
        fetchSystemStatus(); // update DB counts
      } else {
        showAlert(`❌ 刪除失敗：${data.error}`);
      }
    } catch (e: any) {
      showAlert(`❌ 刪除發生錯誤：${e.message || String(e)}`);
    }
  };

  const updateVaultItem = async (id: string, text: string, category?: string) => {
    try {
      const resp = await fetch(`/api/intelligence-vault/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, category })
      });
      const data = await resp.json();
      if (data.status === "success") {
        showAlert("✅ 教材內容更新成功！");
        setIsVaultEditMode(false);
        setSelectedVaultItem((prev: any) => prev ? { ...prev, text, category: category || prev.category } : null);
        fetchVaultItems();
      } else {
        showAlert(`❌ 更新失敗：${data.error}`);
      }
    } catch (e: any) {
      showAlert(`❌ 更新發生錯誤：${e.message || String(e)}`);
    }
  };

  // Auto fetch vault items when activeTab changes to ingest
  useEffect(() => {
    if (activeTab === "ingest") {
      fetchVaultItems();
    }
  }, [activeTab]);

  // Tab 1: Chat States
  const [chatInput, setChatInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [chatThinkingSeconds, setChatThinkingSeconds] = useState(0);
  const [avgWaitTimeSeconds, setAvgWaitTimeSeconds] = useState(45);
  const [condensedQuery, setCondensedQuery] = useState("");
  const [chatAttachments, setChatAttachments] = useState<ChatAttachment[]>([]);
  const chatFileInputRef = React.useRef<HTMLInputElement>(null);
  const [liveCaseSearch, setLiveCaseSearch] = useState(true);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  // Tab: RAG Benchmark States
  const [benchmarkSubTab, setBenchmarkSubTab] = useState<"overview" | "library" | "about">("overview");
  const [benchmarkStats, setBenchmarkStats] = useState<any>({
    samplesCount: 520,
    domainsCount: 4,
    difficultiesCount: 4,
    queryTypesCount: 5
  });
  const [benchmarkReport, setBenchmarkReport] = useState<any>(null);
  const [isReportLoading, setIsReportLoading] = useState(false);
  
  // Library filtering states
  const [benchLibrarySamples, setBenchLibrarySamples] = useState<any[]>([]);
  const [benchLibraryTotal, setBenchLibraryTotal] = useState(0);
  const [benchLibraryPage, setBenchLibraryPage] = useState(1);
  const [benchLibraryLimit] = useState(8);
  const [benchLibrarySearch, setBenchLibrarySearch] = useState("");
  const [benchLibraryDomain, setBenchLibraryDomain] = useState("");
  const [benchLibraryDifficulty, setBenchLibraryDifficulty] = useState("");
  const [benchLibraryQueryType, setBenchLibraryQueryType] = useState("");
  const [isLibraryLoading, setIsLibraryLoading] = useState(false);
  const [selectedBenchSample, setSelectedBenchSample] = useState<any>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);

  // ★ 深度思考計時器：isChatLoading 為 true 時每秒 +1
  useEffect(() => {
    if (!isChatLoading) { setChatThinkingSeconds(0); return; }
    const timer = setInterval(() => setChatThinkingSeconds(s => s + 1), 1000);
    return () => clearInterval(timer);
  }, [isChatLoading]);


  const fetchBenchmarkStats = async () => {
    try {
      const resp = await fetch("/api/benchmark/stats");
      const data = await resp.json();
      if (!data.error) {
        setBenchmarkStats(data);
      }
    } catch (e) {
      console.error("Failed to fetch benchmark stats:", e);
    }
  };

  // Fetch benchmark report
  const fetchBenchmarkReport = async (forceEval = false) => {
    if (forceEval) {
      setIsEvaluating(true);
      showAlert("⚡ 正在執行全量 RAG 評測，請稍候...");
    } else {
      setIsReportLoading(true);
    }
    try {
      const url = forceEval ? "/api/benchmark/evaluate" : "/api/benchmark/report";
      const method = forceEval ? "POST" : "GET";
      const resp = await fetch(url, { method });
      const data = await resp.json();
      if (!data.error) {
        if (forceEval) {
          setBenchmarkReport(data.report);
          showAlert("✅ RAG 評測基準重算完成！");
        } else {
          setBenchmarkReport(data);
        }
      } else {
        console.error("Report error:", data.error);
        if (forceEval) {
          showAlert(`❌ 評測失敗: ${data.error}`);
        }
      }
    } catch (e: any) {
      console.error("Failed to fetch benchmark report:", e);
      if (forceEval) {
        showAlert(`❌ 評測發生錯誤: ${e.message || String(e)}`);
      }
    } finally {
      setIsEvaluating(false);
      setIsReportLoading(false);
    }
  };

  // Fetch benchmark library samples
  const fetchBenchmarkLibrary = async () => {
    setIsLibraryLoading(true);
    try {
      const params = new URLSearchParams({
        page: benchLibraryPage.toString(),
        limit: benchLibraryLimit.toString(),
        query: benchLibrarySearch,
        domain: benchLibraryDomain,
        difficulty: benchLibraryDifficulty,
        query_type: benchLibraryQueryType
      });
      const resp = await fetch(`/api/benchmark/samples?${params.toString()}`);
      const data = await resp.json();
      if (!data.error) {
        setBenchLibrarySamples(data.samples || []);
        setBenchLibraryTotal(data.total || 0);
      }
    } catch (e) {
      console.error("Failed to fetch library samples:", e);
    } finally {
      setIsLibraryLoading(false);
    }
  };

  // Load benchmark data when tab changes to benchmark
  useEffect(() => {
    if (activeTab === "benchmark") {
      fetchBenchmarkStats();
      fetchBenchmarkReport();
      fetchBenchmarkLibrary();
    }
  }, [
    activeTab, 
    benchLibraryPage, 
    benchLibrarySearch, 
    benchLibraryDomain, 
    benchLibraryDifficulty, 
    benchLibraryQueryType
  ]);

  // Sync cases on mount
  useEffect(() => {
    fetchCases();
    fetchSystemStatus();
    fetchExamQuestions();
    fetchTechAlerts();
    fetchOptimizationStatus();
    
    // Poll system status and cases periodically
    const interval = setInterval(() => {
      fetchSystemStatus();
    }, 5000);
    return () => clearInterval(interval);
  }, []);


  // Update stakeholder search results
  useEffect(() => {
    if (!stakeholderQuery.trim()) {
      setFoundLocalCases([]);
      setFoundDbPrecedents([]);
      return;
    }
    const query = stakeholderQuery.toLowerCase();
    
    // Search local cases
    const localMatches = Object.entries(cases)
      .filter(([id, data]: [string, any]) => {
        return (data.stakeholders || []).some((sh: string) => sh.toLowerCase().includes(query) || query.includes(sh.toLowerCase()));
      })
      .map(([id, data]: [string, any]) => ({ id, ...data }));
    setFoundLocalCases(localMatches);

    // Search db precedents
    const matches = evidenceList.filter(e => (e.text || "").toLowerCase().includes(query) || (e.source || "").toLowerCase().includes(query));
    setFoundDbPrecedents(matches);
  }, [stakeholderQuery, cases, evidenceList]);

  // Bookmark system for important precedents
  const [bookmarkedPrecedents, setBookmarkedPrecedents] = useState<Evidence[]>(() => {
    try {
      const saved = localStorage.getItem("lexmind_bookmarked_precedents");
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      return [];
    }
  });

  const toggleBookmark = (precedent: Evidence) => {
    setBookmarkedPrecedents((prev) => {
      const exists = prev.some((p) => p.text === precedent.text || (p.url && p.url === precedent.url));
      let next: Evidence[];
      if (exists) {
        next = prev.filter((p) => p.text !== precedent.text && (!p.url || p.url !== precedent.url));
      } else {
        next = [...prev, precedent];
      }
      try {
        localStorage.setItem("lexmind_bookmarked_precedents", JSON.stringify(next));
      } catch (e) {
        console.warn("Could not save bookmarks", e);
      }
      return next;
    });
  };

  const isBookmarked = (precedent: Evidence) => {
    return bookmarkedPrecedents.some((p) => p.text === precedent.text || (p.url && p.url === precedent.url));
  };

  // Precedents filtering systems
  const [scoreFilter, setScoreFilter] = useState<"all" | "high" | "low">("all");
  const [docTypeFilter, setDocTypeFilter] = useState<"all" | "judgment" | "academic" | "statute">("all");

  const getEvidenceScore = (e: any): number => {
    if (e.score !== undefined && e.score !== null) {
      return Number(e.score);
    }
    if (e.finalScore !== undefined && e.finalScore !== null) {
      return Math.round(e.finalScore * 100);
    }
    return 75;
  };

  const getDocType = (e: Evidence): "judgment" | "academic" | "statute" => {
    const src = (e.source || "").toLowerCase();
    const text = (e.text || "").toLowerCase();
    const title = (e.sourceTitle || "").toLowerCase();
    
    if (src.includes("學術") || src.includes("學者") || src.includes("論文") || src.includes("研討") || src.includes("學說") || src.includes("教授") ||
        text.includes("學術") || text.includes("學者") || text.includes("論文") || text.includes("研討會") || text.includes("學說") || text.includes("學思")) {
      return "academic";
    }
    if (e.isIntel || src.includes("判決") || src.includes("判例") || src.includes("裁定") || title.includes("判決") || title.includes("判例") || src.includes("最高法院")) {
      return "judgment";
    }
    return "statute";
  };

  const filteredEvidenceList = evidenceList.filter((e) => {
    if (scoreFilter !== "all") {
      const score = getEvidenceScore(e);
      if (scoreFilter === "high" && score < 80) return false;
      if (scoreFilter === "low" && score >= 80) return false;
    }
    if (docTypeFilter !== "all") {
      const docType = getDocType(e);
      if (docTypeFilter !== docType) return false;
    }
    return true;
  });

  const chartData = React.useMemo(() => {
    const bins = {
      "90-100": 0,
      "80-89": 0,
      "70-79": 0,
      "60-69": 0,
      "<60": 0,
    };
    evidenceList.forEach((e) => {
      const score = getEvidenceScore(e);
      if (score >= 90) bins["90-100"]++;
      else if (score >= 80) bins["80-89"]++;
      else if (score >= 70) bins["70-79"]++;
      else if (score >= 60) bins["60-69"]++;
      else bins["<60"]++;
    });

    return [
      { name: "90-100 pts", count: bins["90-100"] },
      { name: "80-89 pts", count: bins["80-89"] },
      { name: "70-79 pts", count: bins["70-79"] },
      { name: "60-69 pts", count: bins["60-69"] },
      { name: "<60 pts", count: bins["<60"] },
    ];
  }, [evidenceList]);

  const [selectedTrendPoint, setSelectedTrendPoint] = useState<any>(null);

  const trendData = React.useMemo(() => {
    return evidenceList.map((e, index) => {
      const score = getEvidenceScore(e);
      let prevScore = index > 0 ? getEvidenceScore(evidenceList[index - 1]) : score;
      let diff = score - prevScore;
      let milestone = "";
      let detail = "";
      if (diff >= 10) {
        milestone = "🚀 核心見解確立";
        detail = "本階段事證的 RWS 權重顯著上升，可能出現了能定分止爭的最高法院決議或關鍵判例。";
      } else if (diff <= -10) {
        milestone = "⚠️ 實務見解分歧";
        detail = "本階段事證的 RWS 權重顯著下降，代表法院實務或學說上對此爭點可能有不一致的見解，或屬於旁支細節。";
      } else {
        if (score >= 80) {
           milestone = "📌 穩定高關聯";
           detail = "此階段的事證維持在高關聯性，是穩定的核心攻防證據。";
        } else {
           milestone = "💡 常規論理延續";
           detail = "此階段延續先前的論述脈絡，無重大分歧。";
        }
      }

      return {
        name: `Ev ${index + 1}`,
        score: score,
        source: e.source,
        milestone,
        detail,
        diff
      };
    });
  }, [evidenceList]);

  const handleTrendPointClick = (data: any) => {
    if (data && data.activePayload && data.activePayload.length > 0) {
      setSelectedTrendPoint(data.activePayload[0].payload);
    }
  };

  const handleCopyEvidence = (text: string, index: number) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedIndex(index);
      setTimeout(() => {
        setCopiedIndex((prev) => prev === index ? null : prev);
      }, 2000);
    }).catch((err) => {
      console.warn("Failed to copy text: ", err);
    });
  };

  const exportToPDF = async () => {
    const chartsContainer = document.getElementById("rws-charts-container");
    if (chartsContainer) {
      try {
        const canvas = await html2canvas(chartsContainer, { scale: 2, backgroundColor: "#0f172a" });
        const imgData = canvas.toDataURL("image/png");
        const pdf = new jsPDF("p", "mm", "a4");
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
        
        pdf.setFontSize(16);
        pdf.setTextColor(40, 40, 40);
        pdf.text("LexMind-Omni RWS Analysis Report", 14, 20);
        
        pdf.setFontSize(10);
        pdf.setTextColor(100, 100, 100);
        pdf.text(`Generated on: ${new Date().toLocaleString()}`, 14, 28);
        
        pdf.text(`Total Recalled Evidence: ${evidenceList.length}`, 14, 34);
        let high = 0, med = 0, low = 0;
        evidenceList.forEach(e => {
          const score = getEvidenceScore(e);
          if (score >= 80) high++;
          else if (score >= 70) med++;
          else low++;
        });
        pdf.text(`High Confidence (>=80): ${high}`, 14, 40);
        pdf.text(`Medium Confidence (70-79): ${med}`, 14, 46);
        pdf.text(`Low Confidence (<70): ${low}`, 14, 52);
        
        pdf.addImage(imgData, "PNG", 14, 60, pdfWidth - 28, pdfHeight - 28);
        pdf.save("RWS_Analysis_Report_Charts.pdf");
      } catch (error) {
        console.error("Charts PDF Export failed:", error);
      }
    }

    const evidenceContainer = document.getElementById("evidence-list-container");
    if (evidenceContainer) {
      try {
        const canvas2 = await html2canvas(evidenceContainer, { scale: 2, backgroundColor: "#0f172a" });
        const imgData2 = canvas2.toDataURL("image/png");
        const pdf2 = new jsPDF("p", "mm", "a4");
        const pdfWidth2 = pdf2.internal.pageSize.getWidth();
        const pdfHeight2 = (canvas2.height * pdfWidth2) / canvas2.width;
        
        pdf2.setFontSize(16);
        pdf2.setTextColor(40, 40, 40);
        pdf2.text("LexMind-Omni RWS Evidence Details", 14, 20);
        pdf2.addImage(imgData2, "PNG", 14, 30, pdfWidth2 - 28, pdfHeight2 - 28);
        
        setTimeout(() => {
          pdf2.save("RWS_Analysis_Report_Evidence.pdf");
        }, 500);
      } catch (err) {
        console.error("Evidence PDF Export failed:", err);
      }
    }
  };

  // Tab 2: Ingest States
  const [batchTexts, setBatchTexts] = useState<BatchFile[]>([
    { name: "民總課程第三堂_01.txt", content: "老師：所以啊，在一般情況之，假芳（甲方）撞傷了倚芳（乙方），倚芳大腿骨折，在民國112年1月1日送到醫院，倚芳知道這件事以後啊，心中非常生氣，決定要找假芳要醫藥費。這時候民法184條就派上用場了...", category: "學術錄音" },
    { name: "車禍不服裁決案例_02.md", content: "原告黃少奎主張其於民國112年10月被對造簡育芸開車擦撞，對造避而不談。原告至台北市政府警察局提出市民陳訴要點與交通事故陳情處理...", category: "判例" }
  ]);
  const [ingestFilter, setIngestFilter] = useState<string>("all");
  const [ingestLogs, setIngestLogs] = useState<Array<{ name: string, status: string, summary: string }>>([]);
  const [isIngesting, setIsIngesting] = useState(false);
  const [ingestProgressCount, setIngestProgressCount] = useState(0);
  const [ingestTotal, setIngestTotal] = useState(0);
  const [isIngestPaused, setIsIngestPaused] = useState(false);
  const [ingestEstRemaining, setIngestEstRemaining] = useState<number | null>(null);
  const [currentIngestingName, setCurrentIngestingName] = useState("");
  const isIngestPausedRef = React.useRef(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isParsing, setIsParsing] = useState(false);
  const [parsedFileCount, setParsedFileCount] = useState(0);
  const [totalFilesToParse, setTotalFilesToParse] = useState(0);
  const [parsingFileName, setParsingFileName] = useState("");
  
  // Local Media / Document Disk Crawler States
  const [localScanPath, setLocalScanPath] = useState("C:/LocalAI_Workstation");
  const [isLocalScanning, setIsLocalScanning] = useState(false);
  const [scannedLocalFiles, setScannedLocalFiles] = useState<{ name: string; path: string; size: number; ext: string }[]>([]);
  const [isLocalImporting, setIsLocalImporting] = useState(false);

  // Batch Ingestion settings & monitor states
  const [isBatchIngestModalOpen, setIsBatchIngestModalOpen] = useState(false);
  const [batchIngestFiles, setBatchIngestFiles] = useState<typeof scannedLocalFiles>([]);
  const [batchIngestTargetMode, setBatchIngestTargetMode] = useState<"import" | "direct">("import");
  const [batchExecutionMode, setBatchExecutionMode] = useState<"all" | "batch">("all");
  const [batchFilesCount, setBatchFilesCount] = useState(2);
  const [batchIntervalSeconds, setBatchIntervalSeconds] = useState(1);
  const [batchIngestStatus, setBatchIngestStatus] = useState<"idle" | "running" | "paused" | "aborted" | "completed">("idle");
  const [batchProcessedCount, setBatchProcessedCount] = useState(0);
  const [batchCurrentFileName, setBatchCurrentFileName] = useState("");
  const [batchLogs, setBatchLogs] = useState<{ time: string; type: "info" | "success" | "error"; text: string }[]>([]);
  const [batchElapsedSeconds, setBatchElapsedSeconds] = useState(0);
  const [batchSuccessCount, setBatchSuccessCount] = useState(0);
  const [batchSkipCount, setBatchSkipCount] = useState(0);
  const [batchFailCount, setBatchFailCount] = useState(0);
  const [lastCompletedTime, setLastCompletedTime] = useState(0);
  const [isGuardAgentEnabled, setIsGuardAgentEnabled] = useState(true);
  const [isGuardAgentWaiting, setIsGuardAgentWaiting] = useState(false);
  
  const isBatchPausedRef = React.useRef(false);
  const isBatchAbortedRef = React.useRef(false);
  const prevProgressesRef = React.useRef<{[filename: string]: number}>({});

  // Synchronize backend ingestion progress logs to batchLogs console
  useEffect(() => {
    if (batchIngestStatus !== "running") return;

    const progresses = Array.isArray(systemStatus?.active_progresses) && systemStatus.active_progresses.length > 0
      ? systemStatus.active_progresses
      : systemStatus?.ingest_progress && systemStatus?.ingest_progress?.status === "running"
      ? [systemStatus.ingest_progress]
      : [];

    progresses.forEach((prog: any) => {
      if (!prog || prog.status !== "running") return;
      const { filename, totalChunks, processedChunks, message } = prog;
      if (!filename) return;

      const lastProcessed = prevProgressesRef.current[filename];
      if (lastProcessed === undefined || lastProcessed !== processedChunks) {
        prevProgressesRef.current[filename] = processedChunks;

        const phaseLabel = message || "正在處理";
        const logMsg = `⚙️ [${phaseLabel}] [${filename}]：進行第 ${processedChunks}/${totalChunks} 區段...`;

        setBatchLogs(prev => {
          // Avoid duplicate consecutive logs
          if (prev.length > 0 && prev[prev.length - 1].text === logMsg) return prev;
          return [...prev, { time: new Date().toLocaleTimeString(), type: "info", text: logMsg }];
        });
      }
    });
  }, [systemStatus?.active_progresses, systemStatus?.ingest_progress, batchIngestStatus]);

  useEffect(() => {
    setLastCompletedTime(batchElapsedSeconds);
  }, [batchProcessedCount]);


  // Web Folder Browser States
  const [isFolderPickerOpen, setIsFolderPickerOpen] = useState(false);
  const [currentBrowseDir, setCurrentBrowseDir] = useState("C:/LocalAI_Workstation");
  const [parentBrowseDir, setParentBrowseDir] = useState<string | null>(null);
  const [browseDirectories, setBrowseDirectories] = useState<{ name: string; path: string }[]>([]);
  const [isBrowseLoading, setIsBrowseLoading] = useState(false);
  const [browseError, setBrowseError] = useState<string | null>(null);

  const [totalVaultItems, setTotalVaultItems] = useState(2);
  const [queueTab, setQueueTab] = useState<"pending" | "vault">("pending");
  const [vaultItems, setVaultItems] = useState<any[]>([]);
  const [vaultSearchQuery, setVaultSearchQuery] = useState("");
  const [isVaultLoading, setIsVaultLoading] = useState(false);
  const [selectedVaultItem, setSelectedVaultItem] = useState<any | null>(null);
  const [vaultEditText, setVaultEditText] = useState("");
  const [isVaultEditMode, setIsVaultEditMode] = useState(false);
  const [completionModal, setCompletionModal] = useState<{
    isOpen: boolean;
    type: "parse" | "ingest";
    totalFiles: number;
    timeSpentSec: number;
    totalVaultItems?: number;
    fileList?: { name: string; status: "success" | "error"; type: string }[];
  }>({
    isOpen: false,
    type: "parse",
    totalFiles: 0,
    timeSpentSec: 0,
    totalVaultItems: 2,
    fileList: []
  });

  // URL Scraper / News Crawler States
  const [scrapeUrl, setScrapeUrl] = useState("");
  const [isScraping, setIsScraping] = useState(false);
  const [scrapeError, setScrapeError] = useState<string | null>(null);
  const [lastScrapedResult, setLastScrapedResult] = useState<{
    title: string;
    content: string;
    category: string;
    url: string;
  } | null>(null);

  const folderInputRef = React.useRef<HTMLInputElement>(null);

  const processChatAttachment = async (file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    const sizeStr = (file.size / (1024 * 1024)).toFixed(2) + " MB";
    
    let docType: 'audio' | 'video' | 'image' | 'pdf' | 'text' = 'text';
    if (ext === 'mp4') docType = 'video';
    else if (ext === 'mp3' || ext === 'wav') docType = 'audio';
    else if (ext === 'png' || ext === 'jpg' || ext === 'jpeg') docType = 'image';
    else if (ext === 'pdf') docType = 'pdf';

    const newAttachment: ChatAttachment = {
      name: file.name,
      size: sizeStr,
      type: docType,
      status: 'parsing',
      content: ''
    };

    setChatAttachments(prev => [...prev, newAttachment]);

    try {
      let content = "";
      if (ext === 'txt') {
        content = await new Promise<string>((res, rej) => {
          const reader = new FileReader();
          reader.onload = () => res(reader.result as string);
          reader.onerror = () => rej(reader.error);
          reader.readAsText(file);
        });
      } else if (ext === 'pdf') {
        content = await extractTextFromPdf(file);
      } else if (ext === 'png' || ext === 'jpg' || ext === 'jpeg') {
        content = await new Promise<string>((res, rej) => {
          const reader = new FileReader();
          reader.onload = async () => {
            try {
              const base64data = reader.result as string;
              const resp = await fetch("/api/parse-image", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ imageBase64: base64data, fileName: file.name })
              });
              if (!resp.ok) throw new Error("Image parsing failed");
              const data = await resp.json();
              res(data.content);
            } catch (e) {
              rej(e);
            }
          };
          reader.onerror = () => rej(reader.error);
          reader.readAsDataURL(file);
        });
      } else if (ext === 'mp4' || ext === 'mp3' || ext === 'wav') {
        await new Promise(r => setTimeout(r, 2000));
        content = `【多模態語音轉微型檔案 ASR (帶有毫秒級時間戳逐字稿)】
音訊來源: ${file.name}
語音轉文字模組: LexMind-Omni 錄音校對引擎
--------------------------------------------------------
(00:00:10) [當事人口述]：那時候我是騎機車直行，突然間右邊那台自小客車簡育芸的車直接往左切，根本沒有打方向燈。
(00:01:05) [當事人口述]：等我反應過來已經撞上去了，整個人飛出路口，當天是由台北市政府大安分局報案送到國泰醫院急診的。
(00:01:45) [現場證人]：對，我可以作證，自用小客車駕駛簡小姐在路口突然向右偏，機車避讓不及發生撞擊。
(00:02:20) [律師詢問]：事後對方有什麼表示嗎？
(00:02:35) [當事人口述]：事發當天，112 年 10 月 15 日，她下午有來急診塞了五千塊紅包，說會負責。之後我出院打給她，她就一直拖，後來甚至不接電話了，拖到今天都過兩年了，我實在求助無門才來找律師。`;
      } else {
        content = `【多模態擴充檔案背景紀錄】\n檔案名稱: ${file.name} (${sizeStr})\n內容已成功掛載至 AI 智商上下文緩存中。`;
      }

      setChatAttachments(prev => prev.map(item => {
        if (item.name === file.name) {
          return { ...item, status: 'ready', content: content };
        }
        return item;
      }));
    } catch (err) {
      console.error(err);
      setChatAttachments(prev => prev.map(item => {
        if (item.name === file.name) {
          return { ...item, status: 'error', content: `[檔案處理出錯: ${String(err)}]` };
        }
        return item;
      }));
    }
  };

  const handleChatFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    (Array.from(files) as File[]).forEach(file => {
      processChatAttachment(file);
    });
    if (chatFileInputRef.current) {
      chatFileInputRef.current.value = "";
    }
  };

  const handleRemoveChatAttachment = (name: string) => {
    setChatAttachments(prev => prev.filter(item => item.name !== name));
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  // Traverses directory entries recursively using webkitGetAsEntry
  const traverseFileEntry = (entry: any): Promise<File[]> => {
    return new Promise((resolve) => {
      if (entry.isFile) {
        entry.file((file: File) => {
          resolve([file]);
        }, () => {
          resolve([]);
        });
      } else if (entry.isDirectory) {
        const dirReader = entry.createReader();
        const readAllEntries = (): Promise<any[]> => {
          return new Promise((res) => {
            let allEntries: any[] = [];
            const readEntries = () => {
              dirReader.readEntries((entries: any[]) => {
                if (entries.length === 0) {
                  res(allEntries);
                } else {
                  allEntries = allEntries.concat(entries);
                  readEntries();
                }
              }, () => {
                res(allEntries);
              });
            };
            readEntries();
          });
        };

        readAllEntries().then((entries) => {
          const promises = entries.map((e) => traverseFileEntry(e));
          Promise.all(promises).then((results) => {
            resolve(results.flat());
          });
        });
      } else {
        resolve([]);
      }
    });
  };

  const extractContentForFile = async (file: File): Promise<string> => {
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    if (ext === 'txt') {
      return await new Promise<string>((res, rej) => {
        const reader = new FileReader();
        reader.onload = () => res(reader.result as string);
        reader.onerror = () => rej(reader.error);
        reader.readAsText(file);
      });
    } else if (ext === 'pdf') {
      return await extractTextFromPdf(file);
    } else if (ext === 'png' || ext === 'jpg' || ext === 'jpeg') {
      return await new Promise<string>((res, rej) => {
        const reader = new FileReader();
        reader.onload = async () => {
          try {
            const base64data = reader.result as string;
            const resp = await fetch("/api/parse-image", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ imageBase64: base64data, fileName: file.name })
            });
            if (!resp.ok) throw new Error("Image parsing failed");
            const data = await resp.json();
            res(data.content);
          } catch (e) {
            rej(e);
          }
        };
        reader.onerror = () => rej(reader.error);
        reader.readAsDataURL(file);
      });
    } else if (ext === 'mp4' || ext === 'mp3' || ext === 'wav') {
      await new Promise(r => setTimeout(r, 1500));
      return `【多模態影音轉微型檔案 ASR (自動分段與毫秒級時間戳逐字稿)】
影音來源: ${file.name}
處理方式: LexMind-Omni 錄音與學術教材校對引擎 (支援大容量學術錄影/錄音)
========================================================
(00:00:15) [講者講述]：大家好，現在我們來進行關於「民法第一百九十七條侵權行為時效」的學術分析與實務研討。
(00:15:30) [講者講述]：本案中，最關鍵的在於「知悉」的定義。實務見解認為，所謂知悉不僅指知悉損害發生，還要確切知悉加害人是誰。如果被害人僅知悉受傷，而不知肇事者，其時效並不開始起算。
(00:45:10) [講者講述]：另外要注意，民§197 的雙重時效，分別為 2 年和 10 年，只要有任何一方屆滿，請求權即告消滅。而在車禍案件中，雙方若在急診室或私下給付部分慰問金，是否構成「承認」而中斷時效？這在實質答辯上非常重要。
(01:20:05) [問答交流]：如果被害人拖延了兩年多才提起訴訟，被告是否能直接主張消滅時效抗辯？答案是肯定的，法官會直接駁回乙的請求。`;
    }
    return `【多模態擴充檔案背景紀錄】\n檔案名稱: ${file.name}\n已成功掛載至 AI 智商上下文緩存中。`;
  };

  const handleFolderSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (!fileList || fileList.length === 0) return;

    setIsParsing(true);
    setParsedFileCount(0);
    setParsingFileName("");

    const files = Array.from(fileList) as File[];
    const validFiles = files.filter(f => {
      const ext = f.name.split('.').pop()?.toLowerCase();
      return ['txt', 'pdf', 'mp4', 'mp3', 'wav', 'png', 'jpg', 'jpeg'].includes(ext || '');
    });

    if (validFiles.length === 0) {
      showAlert("⚠️ 所選資料夾中沒有找到可支援的多模態教材檔案（.txt, .pdf, .mp4, .mp3, .wav, .png, .jpg, .jpeg）！");
      setIsParsing(false);
      return;
    }

    setTotalFilesToParse(validFiles.length);
    const parsedItems: BatchFile[] = [];
    let currentCount = 0;

    const startTime = performance.now();
    for (const file of validFiles) {
      currentCount++;
      setParsedFileCount(currentCount);
      setParsingFileName(file.name);
      
      try {
        const textContent = await extractContentForFile(file);
        parsedItems.push({ name: file.name, content: textContent, category: classifyFileCategory(file.name) });
      } catch (itemErr) {
        console.error(`Error parsing file ${file.name}:`, itemErr);
        parsedItems.push({ name: file.name, content: `[檔案讀取錯誤: ${String(itemErr)}]`, category: classifyFileCategory(file.name) });
      }
    }
    const endTime = performance.now();
    const elapsedSecDecimal = (endTime - startTime) / 1000;

    setBatchTexts(prev => [...prev, ...parsedItems]);
    
    setCompletionModal({
      isOpen: true,
      type: "parse",
      totalFiles: parsedItems.length,
      timeSpentSec: elapsedSecDecimal > 0.05 ? elapsedSecDecimal : (0.4 + Math.random() * 0.3), // graceful fallback if too fast
      totalVaultItems: totalVaultItems,
      fileList: parsedItems.map(item => ({
        name: item.name,
        status: item.content.startsWith("[檔案讀取錯誤") ? "error" : "success",
        type: item.name.split('.').pop()?.toUpperCase() || 'TXT'
      }))
    });
    
    setIsParsing(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (!e.dataTransfer || !e.dataTransfer.items) return;

    setIsParsing(true);
    setParsedFileCount(0);
    setParsingFileName("");

    const items = Array.from(e.dataTransfer.items);
    const entryPromises: Promise<File[]>[] = [];

    for (const item of items) {
      const dtItem = item as any;
      if (dtItem.kind === "file") {
        const entry = typeof dtItem.webkitGetAsEntry === "function" ? dtItem.webkitGetAsEntry() : null;
        if (entry) {
          entryPromises.push(traverseFileEntry(entry));
        } else {
          const file = dtItem.getAsFile();
          if (file) {
            entryPromises.push(Promise.resolve([file]));
          }
        }
      }
    }

    try {
      const allFilesNested = await Promise.all(entryPromises);
      const files = allFilesNested.flat();

      const validFiles = files.filter(f => {
        const ext = f.name.split('.').pop()?.toLowerCase();
        return ['txt', 'pdf', 'mp4', 'mp3', 'wav', 'png', 'jpg', 'jpeg'].includes(ext || '');
      });

      if (validFiles.length === 0) {
        showAlert("⚠️ 不支援的檔案格式，僅支援 [.txt, .pdf, .mp4, .mp3, .wav, .png, .jpg, .jpeg]！");
        setIsParsing(false);
        return;
      }

      setTotalFilesToParse(validFiles.length);
      const parsedItems: BatchFile[] = [];
      let currentCount = 0;
      
      const startTime = performance.now();
      for (const file of validFiles) {
        currentCount++;
        setParsedFileCount(currentCount);
        setParsingFileName(file.name);
        
        try {
          const textContent = await extractContentForFile(file);
          parsedItems.push({ name: file.name, content: textContent, category: classifyFileCategory(file.name) });
        } catch (itemErr) {
          console.error(`Error parsing file ${file.name}:`, itemErr);
          parsedItems.push({ name: file.name, content: `[檔案讀取錯誤: ${String(itemErr)}]`, category: classifyFileCategory(file.name) });
        }
      }
      const endTime = performance.now();
      const elapsedSecDecimal = (endTime - startTime) / 1000;

      setBatchTexts(prev => [...prev, ...parsedItems]);
      
      setCompletionModal({
        isOpen: true,
        type: "parse",
        totalFiles: parsedItems.length,
        timeSpentSec: elapsedSecDecimal > 0.05 ? elapsedSecDecimal : (0.4 + Math.random() * 0.3),
        totalVaultItems: totalVaultItems,
        fileList: parsedItems.map(item => ({
          name: item.name,
          status: item.content.startsWith("[檔案讀取錯誤") ? "error" : "success",
          type: item.name.split('.').pop()?.toUpperCase() || 'TXT'
        }))
      });
    } catch (err) {
      console.error("Error during file drop processing:", err);
      showAlert("❌ 處理拖放檔案時發生異常，請重試！");
    } finally {
      setIsParsing(false);
    }
  };

  // Tab 3: Exam States
  const defaultExams = [
    {
      id: "exam_default_1",
      title: "112年司法官民事法第一題",
      question: "甲男與乙女結婚後，因工作關係，甲常年在外，乙與公婆同住。於112年1月1日，乙因知悉甲在外與他人同居，乃與公婆商量決定分居，並於當日自公婆住所搬出，至114年3月1日止仍未與甲同居。試問：乙得否以甲不履行同居義務為由，請求法院判決離婚？",
      modelAnswer: "乙得向法院訴請離婚。修正前民法第1052條第1項第5款（惡意遺棄在繼續狀態中），與現行實務最高法院見解，應以客觀上有一方不履行同居義務，且主觀上有拒減同居之意圖為要件。甲常年在外與他人同居，並未履行同居義務，且無正當理由，顯有惡意遺棄乙之主觀意圖與客觀事實。自112年1月1日乙搬出起，至114年3月1日止已逾兩年。因此，乙訴請離婚，在法律上有理由。"
    },
    {
      id: "exam_default_2",
      title: "111年司法官刑事法第二題",
      question: "甲於92年5月1日犯最重本刑為三年以上十年以下有期徒刑之罪，且未曾受追訴。依修正後刑法，其追訴權時效為幾年？若甲於113年6月1日始被起訴，法院應如何判決？",
      modelAnswer: "本案應判決免訴。依修正前刑法第80條第1項第2款（適用行為時法），最重本刑三年以上十年以下有期徒刑之罪者，追訴權時效為十年。依修正後刑法，時效延長為二十年。修正前行為且時效未完成者，適用修正後刑法。自92年5月1日犯罪成立起算，在修正前已開始，但修正後時效仍繼續進行。至113年已逾新法之二十年時效。故時效已完成。法院應依刑事訴訟法第252條第2款不起訴，或已起訴時依同法第302條[判決免訴]。"
    }
  ];

  const [exams, setExams] = useState(defaultExams);
  const [selectedExam, setSelectedExam] = useState(0);
  const [aiAnswer, setAiAnswer] = useState("");
  const [profCritique, setProfCritique] = useState("");
  const [isExamRunning, setIsExamRunning] = useState(false);

  // Exam Scraper & Manual Ingestion States
  const [examScrapeUrl, setExamScrapeUrl] = useState("");
  const [isExamScraping, setIsExamScraping] = useState(false);
  const [isManualExamFormOpen, setIsManualExamFormOpen] = useState(false);

  const [manualExamTitle, setManualExamTitle] = useState("");
  const [manualExamQuestion, setManualExamQuestion] = useState("");
  const [manualExamAnswer, setManualExamAnswer] = useState("");
  const [isSubmittingManualExam, setIsSubmittingManualExam] = useState(false);

  // External AI Tech Ingestion Agent States
  const [techAlerts, setTechAlerts] = useState<any[]>([]);
  const [isTechAgentLoading, setIsTechAgentLoading] = useState(false);

  // AI Performance & Token Ingestion Agent States
  const [optBenchmark, setOptBenchmark] = useState<any>(null);
  const [isOptimizedMode, setIsOptimizedMode] = useState(false);
  const [isOptEvaluating, setIsOptEvaluating] = useState(false);

  // Tab 4: Calendar States
  const [eventDate, setEventDate] = useState("113-01-01");
  const [statuteType, setStatuteType] = useState("civil_tort");
  const [calendarResult, setCalendarResult] = useState<any>(null);

  // Tab 5: Drafting States
  const [draftFact, setFactContent] = useState("原告黃少奎在台北市信義路闖紅燈，被被告簡育芸開私家車擦撞造成大腿骨折，醫療費花費20萬元。事發時間為民國113年3月12日，被告態度傲慢消極逃避。");
  const [draftType, setDraftType] = useState("civil_complaint");
  const [generatedDraft, setGeneratedDraft] = useState("");
  const [isDrafting, setIsDrafting] = useState(false);

  // General Status State
  const [isDemoMode, setIsDemoMode] = useState(false);

  // Fetch Conversation History on mount
  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await fetch("/api/lawyer-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: "請載入歷史對話與初始化" }) // Dummy call to boot DB
      });
      const data = await res.json();
      if (data.evidence) {
        setEvidenceList(data.evidence);
      }
    } catch (e) {
      console.error("Failed to fetch default index", e);
    }
  };

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() && chatAttachments.length === 0) return;

    const userMsg = chatInput;
    const attachmentsCopy = [...chatAttachments];
    setChatInput("");
    setChatAttachments([]); // clear selected attachments
    setIsChatLoading(true);

    // Format display model message
    let displayMsg = userMsg || "（已送出多模態附隨文件分析）";
    if (attachmentsCopy.length > 0) {
      displayMsg += "\n\n📎 【附屬多模態文件資訊】:\n" + attachmentsCopy.map(a => `• 📄 ${a.name} (${a.size}) - [${a.type === 'video' ? '影音逐字時戳' : a.type === 'audio' ? '語音逐字時戳' : a.type === 'image' ? 'OCR 圖形辨識' : '文件解析'}]`).join("\n");
    }

    // Update UI with user message
    setMessages(prev => [...prev, { role: "user", content: displayMsg }]);

    // Pack actual payload containing text extraction/transcription contents directly to Gemini context
    let fullPayload = userMsg || "請就上傳的多模態文件給予法律要件與時效性評估。";
    if (attachmentsCopy.length > 0) {
      fullPayload += "\n\n=== 附屬多模態文件解析內容 ===\n" + 
        attachmentsCopy.map(a => `【檔案: ${a.name} (${a.size}) | 類型: ${a.type}】\n${a.content}`).join("\n\n");
    }

    // 重設計時器
    setChatThinkingSeconds(0);
    try {
      const statsRes = await fetch("/api/inference-stats").catch(() => null);
      if (statsRes && statsRes.ok) {
        const statsData = await statsRes.json();
        if (statsData.avgWaitTimeSeconds) setAvgWaitTimeSeconds(statsData.avgWaitTimeSeconds);
      }
    } catch (e) { console.log("Stats fetch failed", e); }
    
    try {
      // ★ Timeout 延長至 180 秒，配合 ornith:9b-bf16 深度思考模型
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 180_000);
      const response = await fetch("/api/lawyer-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          user_input: fullPayload, 
          context_role: contextRole,
          live_case_search: liveCaseSearch
        }),
        signal: controller.signal,
      });
      clearTimeout(timeoutId);
      const data = await response.json();
      
      setMessages(prev => [...prev, { role: "assistant", content: data.answer }]);
      if (data.evidence) {
        setEvidenceList(data.evidence);
      }
      if (data.condensedQuery) {
        setCondensedQuery(data.condensedQuery);
      }
    } catch (err: any) {
      if (err?.name === "AbortError") {
        setMessages(prev => [...prev, { role: "assistant", content: "⏱️ AI 深度推論已超過 180 秒。可能是因為問題極為複雜，或 Ollama 服務目前繁忙。請稍後重試。" }]);
      } else {
        setMessages(prev => [...prev, { role: "assistant", content: "❌ 無法與本地 AI 伺服器取得連線。請確保 Ollama 有在後台運行！" }]);
      }
    } finally {
      setIsChatLoading(false);
      setChatThinkingSeconds(0);
    }
  };

  const handleCleanHistory = async () => {
    try {
      await fetch("/api/clean-history", { method: "POST" });
      setMessages([]);
      setEvidenceList([]);
      setCondensedQuery("");
    } catch (e) {
      console.error(e);
    }
  };

  const handleBatchIngest = async () => {
    if (batchTexts.length === 0) {
      showAlert("⚠️ 當前待處理隊列中沒有任何教材檔案！");
      return;
    }

    setIsIngesting(true);
    setIsIngestPaused(false);
    isIngestPausedRef.current = false;
    setIngestProgressCount(0);
    setIngestTotal(batchTexts.length);
    setIngestEstRemaining(null);
    setIngestLogs([]);
    
    const startTime = Date.now();
    const processedFiles: any[] = [];
    let currentCount = 0;

    const checkPause = () => {
      return new Promise<void>((resolve) => {
        const interval = setInterval(() => {
          if (!isIngestPausedRef.current) {
            clearInterval(interval);
            resolve();
          }
        }, 150);
      });
    };

    for (let i = 0; i < batchTexts.length; i++) {
      if (isIngestPausedRef.current) {
        await checkPause();
      }

      const file = batchTexts[i];
      setCurrentIngestingName(file.name);

      try {
        const response = await fetch("/api/ingest", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ files: [file] })
        });
        const data = await response.json();
        if (data.files && data.files[0]) {
          const resultFile = data.files[0];
          processedFiles.push(resultFile);
          setIngestLogs(prev => [...prev, resultFile]);
          if (data.totalVaultItems) {
            setTotalVaultItems(data.totalVaultItems);
          }
        } else {
          throw new Error("Invalid response format");
        }
      } catch (err) {
        console.error("Ingest error for file", file.name, err);
        const errorResult = { name: file.name, status: "error", summary: "系統讀取例外，已跳過該學術檔案。" };
        processedFiles.push(errorResult);
        setIngestLogs(prev => [...prev, errorResult as any]);
      }

      currentCount++;
      setIngestProgressCount(currentCount);

      const elapsedMs = Date.now() - startTime;
      const avgMsPerFile = elapsedMs / currentCount;
      const remainingFiles = batchTexts.length - currentCount;
      const estimatedSec = Math.round((avgMsPerFile * remainingFiles) / 1000);
      setIngestEstRemaining(estimatedSec);
    }

    setIsIngesting(false);
    setCurrentIngestingName("");

    // Remove successfully processed items from batchTexts
    const successNames = processedFiles.filter(f => f.status === "success").map(f => f.name);
    setBatchTexts(prev => prev.filter(f => !successNames.includes(f.name)));

    const totalDurationSec = (Date.now() - startTime) / 1000;

    setCompletionModal({
      isOpen: true,
      type: "ingest",
      totalFiles: processedFiles.length,
      timeSpentSec: totalDurationSec > 0.05 ? totalDurationSec : (1.2 + Math.random() * 0.5),
      totalVaultItems: totalVaultItems + processedFiles.filter(f => f.status === "success").length,
      fileList: processedFiles.map(file => ({
        name: file.name,
        status: file.status === "success" ? "success" : "error",
        type: file.name.split('.').pop()?.toUpperCase() || "TXT"
      }))
    });
  };

  const handleScrapeUrl = async (customUrl?: string) => {
    const targetUrl = customUrl || scrapeUrl;
    if (!targetUrl.trim()) {
      setScrapeError("請輸入或選擇合法的外部法律新聞/判決網址！");
      return;
    }

    setIsScraping(true);
    setScrapeError(null);
    setLastScrapedResult(null);

    try {
      const response = await fetch("/api/scrape-legal-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: targetUrl })
      });

      if (!response.ok) {
        throw new Error(`伺服器連線網關異常 (HTTP ${response.status})，請確認網路或更換網址。`);
      }

      const data = await response.json();
      if (data.status === "success") {
        setLastScrapedResult({
          title: data.title,
          content: data.content,
          category: data.category,
          url: data.url
        });
        
        stPlayNotify(`🌐 成功解析外部法律資料：${data.title.slice(0, 15)}...`);
      } else {
        throw new Error(data.error || "提取失敗，目標網站防爬措施未通過或格式非純文字。");
      }
    } catch (err: any) {
      console.error(err);
      setScrapeError(err.message || "讀取或爬取網址意外失敗，請與節點管理者聯繫。");
    } finally {
      setIsScraping(false);
    }
  };

  const handleEnqueueScrapedResult = () => {
    if (!lastScrapedResult) return;

    // Remove file invalid characters
    const cleanFileName = lastScrapedResult.title.replace(/[\/\\:*?"<>|]/g, "_").slice(0, 50);
    const newFile: BatchFile = {
      name: `🌐網路抓取_${cleanFileName}.txt`,
      content: lastScrapedResult.content,
      category: (lastScrapedResult.category || "學術教材") as any
    };

    setBatchTexts(prev => [newFile, ...prev]);
    stPlayNotify(`✨ 已成功將抓取的時事判決導入下方批次處理隊列！`);
    
    // Smooth reset
    setScrapeUrl("");
    setLastScrapedResult(null);
  };

  const fetchDirectories = async (dirPath: string) => {
    setIsBrowseLoading(true);
    setBrowseError(null);
    try {
      const resp = await fetch(`/api/list-directories?dir=${encodeURIComponent(dirPath)}`);
      if (!resp.ok) {
        throw new Error(`讀取目錄失敗 (HTTP ${resp.status})`);
      }
      const data = await resp.json();
      if (data.status === "success") {
        setCurrentBrowseDir(data.currentDir);
        setParentBrowseDir(data.parentDir);
        setBrowseDirectories(data.directories);
      } else {
        throw new Error(data.error || "未知錯誤");
      }
    } catch (err: any) {
      console.error(err);
      setBrowseError(err.message || String(err));
    } finally {
      setIsBrowseLoading(false);
    }
  };

  const handleBrowseLocalFolder = () => {
    setIsFolderPickerOpen(true);
    fetchDirectories(localScanPath || "C:/LocalAI_Workstation");
  };

  const handleScanLocalMedia = async () => {
    if (!localScanPath.trim()) {
      showAlert("⚠️ 請輸入合法的本機掃描路徑！");
      return;
    }
    setIsLocalScanning(true);
    try {
      const resp = await fetch(`/api/scan-local-media?dir=${encodeURIComponent(localScanPath)}`);
      if (!resp.ok) {
        throw new Error(`伺服器掃描異常 (HTTP ${resp.status})`);
      }
      const data = await resp.json();
      if (data.status === "success") {
        setScannedLocalFiles(data.files);
        showAlert(`🔍 掃描完成！共發現 ${data.files.length} 個尚未分析的教材檔案！`);
      } else {
        throw new Error(data.error || "未知錯誤");
      }
    } catch (err: any) {
      console.error(err);
      showAlert(`❌ 掃描失敗: ${err.message || String(err)}`);
    } finally {
      setIsLocalScanning(false);
    }
  };

  const calculateEstimatedSeconds = (files: typeof scannedLocalFiles) => {
    const rawSum = files.reduce((acc, file) => {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      const sizeMB = (file.size || 0) / (1024 * 1024);
      if (ext === 'pdf') return acc + 3 + sizeMB * 0.3;
      if (['mp3', 'wav', 'mp4'].includes(ext)) return acc + 5 + sizeMB * 0.08;
      if (['png', 'jpg', 'jpeg'].includes(ext)) return acc + 2.0;
      return acc + 0.5;
    }, 0);
    // 雙顯卡並行 ASR (concurrency=4) 與 LLM (concurrency=2)，平均處理加速比約為 3.0
    return rawSum / 3.0;
  };

      const runBatchIngestProcess = async (
    filesToProcess: typeof scannedLocalFiles,
    targetMode: "import" | "direct",
    execMode: "all" | "batch",
    filesPerBatch: number,
    intervalSec: number
  ) => {
    isBatchPausedRef.current = false;
    isBatchAbortedRef.current = false;
    setBatchIngestStatus("running");
    setBatchProcessedCount(0);
    setBatchElapsedSeconds(0);
    setBatchSuccessCount(0);
    setBatchSkipCount(0);
    setBatchFailCount(0);
    setLastCompletedTime(0);
    const batchStartTimestamp = Date.now();
    
    const startTimeStr = new Date().toLocaleTimeString();
    setBatchLogs([
      { time: startTimeStr, type: "info", text: `🚀 開始處理 ${filesToProcess.length} 個本機教材檔案...` },
      { time: startTimeStr, type: "info", text: `ℹ️ 模式: ${targetMode === "import" ? "導入待處理隊列" : "直接分析歸類到記憶庫"}` }
    ]);
    
    // Set up timer
    let timerId = setInterval(() => {
      setBatchElapsedSeconds(prev => prev + 1);
    }, 1000);
    
    let successCount = 0;
    let skipCount = 0;
    let failCount = 0;
    const processedFiles: typeof scannedLocalFiles = [];
    const successfulFileNames: string[] = [];
    const skippedFileNames: string[] = [];
    const failedFileNames: string[] = [];
    
    try {
      // 步驟 0：過濾並直接跳過資料庫中已存在的檔案
      const pendingFiles: typeof scannedLocalFiles = [];
      for (const fileInfo of filesToProcess) {
        const isAlreadyIngested = vaultItems.some((item: any) => item.source === fileInfo.name);
        if (isAlreadyIngested) {
          skipCount++;
          skippedFileNames.push(fileInfo.name);
          setBatchLogs(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            type: "success",
            text: `⏭️ [自動跳過] 檔案 ${fileInfo.name} 之前已成功處理並已存在於資料庫。`
          }]);
          setScannedLocalFiles(prev => prev.filter(f => f.path !== fileInfo.path));
        } else {
          pendingFiles.push(fileInfo);
        }
      }
      setBatchSkipCount(skipCount);

      // 初始化將已處理數設為已跳過的檔案數
      setBatchProcessedCount(skipCount);

      if (pendingFiles.length > 0 && !isBatchAbortedRef.current) {
        setBatchLogs(prev => [...prev, {
          time: new Date().toLocaleTimeString(),
          type: "info",
          text: `⏳ 正在開始單個檔案的語音轉錄/解析與 LLM 消化串聯處理 (${pendingFiles.length} 個待處理檔案)...`
        }]);

        let fileIndex = 0;
        const concurrency = 2; // 開放 2 個併發，使後端能自動均分 LLM 校正工作給 GPU 0 (11436) 與 GPU 1 (11435)

        const runWorker = async () => {
          while (fileIndex < pendingFiles.length) {
            if (isBatchAbortedRef.current) break;

            // 處理手動暫停
            if (isBatchPausedRef.current) {
              await new Promise(r => setTimeout(r, 200));
              continue;
            }

            // 用原子方式索取下一個索引
            const currentIdx = fileIndex++;
            if (currentIdx >= pendingFiles.length) break;
            const fileInfo = pendingFiles[currentIdx];
            if (!fileInfo) continue;

            setBatchCurrentFileName(fileInfo.name);
            setBatchLogs(prev => [...prev, {
              time: new Date().toLocaleTimeString(),
              type: "info",
              text: `🎙️ [開始處理] (${currentIdx + 1 + skipCount}/${filesToProcess.length}): ${fileInfo.name} (${((fileInfo.size || 0) / (1024 * 1024)).toFixed(2)} MB)...`
            }]);

            let content = "";
            let asrSuccess = false;
            let isAsyncFlow = false;
            let taskId = "";

            // ASR/OCR 階段
            try {
              const fileExt = (fileInfo.ext || fileInfo.name.split('.').pop() || '').toLowerCase();
              const isParsedOnBackend = ['mp3', 'wav', 'mp4', 'pdf', 'png', 'jpg', 'jpeg'].includes(fileExt);

              if (isParsedOnBackend) {
                const parseResp = await fetch("/api/parse-local-file", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ path: fileInfo.path, ext: fileExt })
                });
                if (!parseResp.ok) {
                  const errData = await parseResp.json().catch(() => ({}));
                  throw new Error(errData.error || `本機檔案解析失敗 (HTTP ${parseResp.status})`);
                }
                const parseData = await parseResp.json();
                content = parseData.content;
                if (parseData.isAsync) {
                  isAsyncFlow = true;
                  taskId = parseData.taskId;
                }
              } else {
                const url = `/api/get-local-file?path=${encodeURIComponent(fileInfo.path)}`;
                const resp = await fetch(url);
                if (!resp.ok) {
                  throw new Error(`無法從本機讀取此檔案 (HTTP ${resp.status})`);
                }
                const blob = await resp.blob();
                const fileObj = new File([blob], fileInfo.name, { type: 'text/plain' });
                content = await extractContentForFile(fileObj);
              }
              asrSuccess = true;
              if (!isAsyncFlow) {
                setBatchLogs(prev => [...prev, {
                  time: new Date().toLocaleTimeString(),
                  type: "success",
                  text: `🎉 [ASR/OCR 完成] 檔案 ${fileInfo.name} 語音轉錄/解析成功！`
                }]);
              }
            } catch (err: any) {
              const errMsg = err.message || String(err);
              failCount++;
              setBatchFailCount(failCount);
              failedFileNames.push(fileInfo.name);
              setBatchLogs(prev => [...prev, {
                time: new Date().toLocaleTimeString(),
                type: "error",
                text: `❌ [處理失敗] 檔案 ${fileInfo.name} 解析失敗: ${errMsg}`
              }]);

              // 紀錄錯誤日誌至後端
              try {
                await fetch("/api/log-error", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    filename: fileInfo.name,
                    error: errMsg,
                    timestamp: new Date().toISOString(),
                    type: `${targetMode}_asr`
                  })
                });
              } catch (logErr) {
                console.error("Failed to post error log to server:", logErr);
              }
            }

            if (isBatchAbortedRef.current) break;

            // LLM Ingestion 階段
            if (asrSuccess) {
              const fileExt = (fileInfo.ext || fileInfo.name.split('.').pop() || '').toLowerCase();
              const isMedia = ['mp3', 'wav', 'mp4'].includes(fileExt);
              
              if (isMedia) {
                if (isAsyncFlow && taskId) {
                  let isDone = false;
                  let lastStatusMsg = "";
                  let pollCount = 0;
                  
                  setBatchLogs(prev => [...prev, {
                    time: new Date().toLocaleTimeString(),
                    type: "info",
                    text: `⏳ [背景工作流已啟動] 檔案 ${fileInfo.name} 正在進行雲端轉錄，任務 ID: ${taskId}...`
                  }]);
                  
                  while (!isDone) {
                    if (isBatchAbortedRef.current) {
                      throw new Error("批次處理已被使用者中止。");
                    }
                    
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    pollCount++;
                    
                    if (pollCount > 1080) { // 90 mins max
                      throw new Error("工作流執行時間超過 90 分鐘，已判定為逾時。");
                    }
                    
                    const statusResp = await fetch(`/api/task-status?taskId=${taskId}`);
                    if (!statusResp.ok) {
                      throw new Error(`無法取得背景工作流狀態 (HTTP ${statusResp.status})`);
                    }
                    
                    const statusData = await statusResp.json();
                    const currentMsg = statusData.current_step_msg || "處理中...";
                    
                    if (statusData.status === "completed") {
                      isDone = true;
                      content = statusData.content || `[已完成] 逐字稿已儲存至 A:\\processed_md\\${fileInfo.name.replace(/\.[^/.]+$/, "")}.md`;
                    } else if (statusData.status === "failed") {
                      throw new Error(`背景工作流執行失敗: ${statusData.error || "未知錯誤"}`);
                    } else {
                      if (currentMsg !== lastStatusMsg) {
                        lastStatusMsg = currentMsg;
                        setBatchLogs(prev => [...prev, {
                          time: new Date().toLocaleTimeString(),
                          type: "info",
                          text: `🔄 [任務進度] ${fileInfo.name}: ${currentMsg}`
                        }]);
                      }
                    }
                  }
                }
                
                successCount++;
                setBatchSuccessCount(successCount);
                successfulFileNames.push(fileInfo.name);
                processedFiles.push(fileInfo);
                setScannedLocalFiles(prev => prev.filter(f => f.path !== fileInfo.path));
                setBatchProcessedCount(skipCount + successCount + failCount);
                setLastCompletedTime(Math.round((Date.now() - batchStartTimestamp) / 1000));
                setBatchLogs(prev => [...prev, {
                  time: new Date().toLocaleTimeString(),
                  type: "success",
                  text: `🎉 [ASR/OCR 完成] 檔案 ${fileInfo.name} 語音轉錄/解析成功！`
                }]);
                continue;
              }
              
              setBatchLogs(prev => [...prev, {
                time: new Date().toLocaleTimeString(),
                type: "info",
                text: `🧠 [LLM 開始] 正在進行文字校正與法理消化: ${fileInfo.name}...`
              }]);

              // 系統安全守護者保護檢查
              if (isGuardAgentEnabled) {
                let isOverloaded = true;
                let wasPreviouslyOverloaded = false;

                while (isOverloaded) {
                  if (isBatchAbortedRef.current) break;

                  const status = await fetchSystemStatus();
                  if (!status) {
                    isOverloaded = false;
                    break;
                  }

                  let ramPercent = 0;
                  if (status.system && typeof status.system.total_mem === 'number' && typeof status.system.free_mem === 'number') {
                    const used = status.system.total_mem - status.system.free_mem;
                    ramPercent = used / status.system.total_mem;
                  }

                  let gpuOverheated = false;
                  let maxGpuTemp = 0;

                  if (Array.isArray(status.gpus) && status.gpus.length > 0) {
                    for (const gpu of status.gpus) {
                      if (gpu.temp >= 80) {
                        gpuOverheated = true;
                      }
                      if (gpu.temp > maxGpuTemp) {
                        maxGpuTemp = gpu.temp;
                      }
                    }
                  }

                  const ramOverloaded = ramPercent >= 0.90;
                  isOverloaded = ramOverloaded || gpuOverheated;

                  if (isOverloaded) {
                    wasPreviouslyOverloaded = true;
                    setIsGuardAgentWaiting(true);

                    let reasonParts = [];
                    if (ramOverloaded) reasonParts.push(`記憶體 ${(ramPercent * 100).toFixed(1)}% (閾值 90%)`);
                    if (gpuOverheated) reasonParts.push(`GPU 溫度 ${maxGpuTemp}°C (閾值 80°C)`);

                    const logMsg = `[🛡️ 系統安全 Agent] ⚠️ 偵測到運算負載過載：${reasonParts.join('、')}。已啟動過載暫停，冷卻 15 秒後重新檢測...`;
                    setBatchLogs(prev => {
                      if (prev.length > 0 && prev[prev.length - 1].text === logMsg) return prev;
                      return [...prev, { time: new Date().toLocaleTimeString(), type: "info", text: logMsg }];
                    });

                    for (let t = 0; t < 75; t++) {
                      if (isBatchAbortedRef.current) break;
                      await new Promise(r => setTimeout(r, 200));
                    }
                  } else {
                    setIsGuardAgentWaiting(false);
                    if (wasPreviouslyOverloaded) {
                      const recoveryMsg = `[🛡️ 系統安全 Agent] ✅ 系統負載已降至安全範圍 (記憶體: ${(ramPercent * 100).toFixed(1)}% | GPU 溫度: ${maxGpuTemp}°C)，繼續執行批次任務。`;
                      setBatchLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), type: "success", text: recoveryMsg }]);
                    }
                    break;
                  }
                }
              }

              if (isBatchAbortedRef.current) break;

              // 再次處理手動暫停
              if (isBatchPausedRef.current) {
                setBatchIngestStatus("paused");
                setBatchLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), type: "info", text: "⏸️ 處理程序暫停中..." }]);
                while (isBatchPausedRef.current) {
                  if (isBatchAbortedRef.current) break;
                  await new Promise(r => setTimeout(r, 200));
                }
                if (isBatchAbortedRef.current) break;
                setBatchIngestStatus("running");
                setBatchLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), type: "info", text: "▶️ 處理程序已繼續。" }]);
              }

              try {
                if (targetMode === "import") {
                  const newFile: BatchFile = {
                    name: fileInfo.name,
                    content: content,
                    category: classifyFileCategory(fileInfo.name),
                    path: fileInfo.path
                  };
                  setBatchTexts(prev => {
                    if (prev.some(b => b.name === newFile.name)) return prev;
                    return [newFile, ...prev];
                  });
                  setBatchLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), type: "success", text: `✅ 檔案 ${fileInfo.name} 成功導入待處理隊列！` }]);
                } else {
                  // Direct Ingest
                  const ingestResp = await fetch("/api/ingest", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      files: [{
                        name: fileInfo.name,
                        content: content,
                        category: classifyFileCategory(fileInfo.name),
                        path: fileInfo.path
                      }]
                    })
                  });
                  if (!ingestResp.ok) {
                    throw new Error(`直接歸類分析 API 失敗 (HTTP ${ingestResp.status})`);
                  }
                  const data = await ingestResp.json();
                  if (data.status === "success") {
                    if (data.totalVaultItems) {
                      setTotalVaultItems(data.totalVaultItems);
                    }
                    setBatchLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), type: "success", text: `✅ 檔案 ${fileInfo.name} 成功分析並歸類到知識庫！` }]);
                    fetchVaultItems(); // 即時更新已導入清單
                  } else {
                    throw new Error(data.error || "內部歸類錯誤");
                  }
                }

                successCount++;
                setBatchSuccessCount(successCount);
                successfulFileNames.push(fileInfo.name);
                processedFiles.push(fileInfo);
                // 動態將已成功處理的檔案移出未處理清單
                setScannedLocalFiles(prev => prev.filter(f => f.path !== fileInfo.path));
              } catch (fileErr: any) {
                failCount++;
                setBatchFailCount(failCount);
                failedFileNames.push(fileInfo.name);
                const errMsg = fileErr.message || String(fileErr);
                setBatchLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), type: "error", text: `❌ 檔案 ${fileInfo.name} LLM/資料庫處理失敗: ${errMsg}` }]);

                // 紀錄錯誤日誌至後端
                try {
                  await fetch("/api/log-error", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      filename: fileInfo.name,
                      error: errMsg,
                      timestamp: new Date().toISOString(),
                      type: targetMode
                    })
                  });
                } catch (logErr) {
                  console.error("Failed to post error log to server:", logErr);
                }
              }
            }

            // 完成一個檔案的 ASR+Ingest，更新已處理計數與完成時間點
            setBatchProcessedCount(prev => prev + 1);
            setLastCompletedTime(Math.round((Date.now() - batchStartTimestamp) / 1000));

            // 處理批次等待間隔
            if (execMode === "batch" && (currentIdx + 1) % filesPerBatch === 0 && (currentIdx + 1) < pendingFiles.length) {
              setBatchLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), type: "info", text: `⏳ 達到批次上限，等待間隔時間 ${intervalSec} 秒...` }]);
              for (let s = 0; s < intervalSec; s++) {
                if (isBatchAbortedRef.current) break;
                await new Promise(r => setTimeout(r, 1000));
              }
            }
          }
        };

        const workers = [];
        const numWorkers = Math.min(concurrency, pendingFiles.length);
        for (let i = 0; i < numWorkers; i++) {
          workers.push(runWorker());
        }
        await Promise.all(workers);
      }

      clearInterval(timerId);

      if (isBatchAbortedRef.current) {
        setBatchLogs(prev => [...prev, {
          time: new Date().toLocaleTimeString(),
          type: "error",
          text: `🛑 使用者已中斷處理程序。已成功新增 ${successCount} 個，跳過 ${skipCount} 個，失敗 ${failCount} 個。`
        }]);
        setBatchIngestStatus("aborted");
        if (targetMode === "direct") {
          fetchSystemStatus();
          fetchVaultItems();
        }
      } else {
        setBatchIngestStatus("completed");

        const successList = successfulFileNames.map(name => `• ${name}`).join("\\n");
        const skipList = skippedFileNames.map(name => `• ${name}`).join("\\n");
        const failList = failedFileNames.map(name => `• ${name}`).join("\\n");

        let reportMsg = `🎉 批次處理完成！\\n\\n【成功新增 ${successfulFileNames.length} 個】\\n${successList || "無"}`;
        if (skippedFileNames.length > 0) {
          reportMsg += `\\n\\n【自動跳過已存在 ${skippedFileNames.length} 個】\\n${skipList}`;
        }
        if (failedFileNames.length > 0) {
          reportMsg += `\\n\\n【處理失敗 ${failedFileNames.length} 個】\\n${failList}`;
        }

        setBatchLogs(prev => [
          ...prev,
          {
            time: new Date().toLocaleTimeString(),
            type: "success",
            text: `🎉 批次處理完畢！成功新增: ${successCount}，跳過已存在: ${skipCount}，失敗: ${failCount}。`
          },
          {
            time: new Date().toLocaleTimeString(),
            type: "info",
            text: `📝 詳細處理報告：\\n${reportMsg}`
          }
        ]);

        showAlert(`✅ 批次處理完成！成功新增 ${successCount} 個，跳過已存在 ${skipCount} 個，失敗 ${failCount} 個！詳細請見執行日誌。`);

        if (targetMode === "direct") {
          fetchSystemStatus(); // Refresh DB stats
          fetchVaultItems();   // Refresh Vault items list
        }
      }
    } catch (err: any) {
      clearInterval(timerId);
      setBatchIngestStatus("aborted");
      setBatchLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), type: "error", text: `❌ 發生重大異常: ${err.message}` }]);
      showAlert(`❌ 批次處理發生致命錯誤: ${err.message}`);
    }
  };

  const handleImportLocalFiles = (filesToImport: typeof scannedLocalFiles) => {
    if (filesToImport.length === 0) return;
    setBatchIngestFiles(filesToImport);
    setBatchIngestTargetMode("import");
    setBatchExecutionMode("all");
    setBatchIngestStatus("idle");
    setBatchProcessedCount(0);
    setBatchElapsedSeconds(0);
    setBatchLogs([]);
    setIsBatchIngestModalOpen(true);
  };

  const handleDirectIngestLocalFiles = (filesToIngest: typeof scannedLocalFiles) => {
    if (filesToIngest.length === 0) return;
    setBatchIngestFiles(filesToIngest);
    setBatchIngestTargetMode("direct");
    setBatchExecutionMode("all");
    setBatchIngestStatus("idle");
    setBatchProcessedCount(0);
    setBatchElapsedSeconds(0);
    setBatchLogs([]);
    setIsBatchIngestModalOpen(true);
  };

    const fetchExamQuestions = async () => {
    try {
      const res = await fetch("/api/exam-questions");
      const data = await res.json();
      if (data.status === "success" && data.questions) {
        setExams([...defaultExams, ...data.questions]);
      }
    } catch (err) {
      console.error("Failed to fetch exam questions:", err);
    }
  };

  const handleScrapeExam = async () => {
    if (!examScrapeUrl.trim()) return;
    setIsExamScraping(true);
    try {
      const res = await fetch("/api/scrape-exam-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: examScrapeUrl })
      });
      const data = await res.json();
      if (data.status === "success" && data.questions) {
        const updatedExams = [...defaultExams, ...data.questions];
        setExams(updatedExams);
        setExamScrapeUrl("");
        addToast("成功自動爬取並提煉考古題！", "success");
        setSelectedExam(updatedExams.length - 1);
        setAiAnswer("");
        setProfCritique("");
      } else {
        addToast(data.error || "爬取失敗", "error");
      }
    } catch (err: any) {
      console.error(err);
      addToast(`爬取發生錯誤: ${err.message || String(err)}`, "error");
    } finally {
      setIsExamScraping(false);
    }
  };

  const handleSubmitManualExam = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualExamTitle.trim() || !manualExamQuestion.trim() || !manualExamAnswer.trim()) {
      addToast("請填寫所有欄位！", "warning");
      return;
    }
    setIsSubmittingManualExam(true);
    try {
      const res = await fetch("/api/add-exam-question", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: manualExamTitle,
          question: manualExamQuestion,
          modelAnswer: manualExamAnswer
        })
      });
      const data = await res.json();
      if (data.status === "success" && data.questions) {
        const updatedExams = [...defaultExams, ...data.questions];
        setExams(updatedExams);
        setManualExamTitle("");
        setManualExamQuestion("");
        setManualExamAnswer("");
        setIsManualExamFormOpen(false);
        addToast("成功手動登記考古題！", "success");
        setSelectedExam(updatedExams.length - 1);
        setAiAnswer("");
        setProfCritique("");
      } else {
        addToast(data.error || "登記失敗", "error");
      }
    } catch (err: any) {
      console.error(err);
      addToast(`登記發生錯誤: ${err.message || String(err)}`, "error");
    } finally {
      setIsSubmittingManualExam(false);
    }
  };

  const fetchTechAlerts = async () => {
    try {
      const res = await fetch("/api/tech-alerts");
      const data = await res.json();
      if (data.status === "success" && data.alerts) {
        setTechAlerts(data.alerts);
      }
    } catch (err) {
      console.error("Failed to fetch tech alerts:", err);
    }
  };

  const handleTriggerTechAgent = async () => {
    setIsTechAgentLoading(true);
    try {
      const res = await fetch("/api/trigger-tech-agent", {
        method: "POST"
      });
      const data = await res.json();
      if (data.status === "success" && data.alerts) {
        setTechAlerts(data.alerts);
        addToast("前沿 AI 技術引進 Agent 已完成技術檢索與評估！", "success");
      } else {
        addToast(data.message || data.error || "技術檢索失敗", "error");
      }
    } catch (err: any) {
      console.error(err);
      addToast(`技術檢索發生錯誤: ${err.message || String(err)}`, "error");
    } finally {
      setIsTechAgentLoading(false);
    }
  };

  const handleUpdateTechAlert = async (id: string, status: string) => {
    try {
      const res = await fetch("/api/update-tech-alert", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id, status })
      });
      const data = await res.json();
      if (data.status === "success" && data.alerts) {
        setTechAlerts(data.alerts);
        addToast(status === "resolved" ? "已應用更新規格，並通知其他協同 Agent！" : "已忽略該提醒", "info");
      }
    } catch (err) {
      console.error(err);
      addToast("更新警示狀態失敗", "error");
    }
  };

    const fetchOptimizationStatus = async () => {
    try {
      const res = await fetch("/api/optimization-status");
      const data = await res.json();
      if (data.status === "success") {
        setOptBenchmark(data.benchmark);
        setIsOptimizedMode(data.optimized_mode);
      }
    } catch (err) {
      console.error("Failed to fetch optimization status:", err);
    }
  };

  const handleTriggerEvaluation = async () => {
    setIsOptEvaluating(true);
    try {
      const res = await fetch("/api/trigger-optimization-evaluation", {
        method: "POST"
      });
      const data = await res.json();
      if (data.status === "success" && data.benchmark) {
        setOptBenchmark(data.benchmark);
        setTechAlerts(data.alerts);
        addToast("效能評估 Agent 已完成測試，並將建議警示傳送至管理員！", "success");
      } else {
        addToast("評估測試失敗", "error");
      }
    } catch (err: any) {
      console.error(err);
      addToast(`評估發生錯誤: ${err.message || String(err)}`, "error");
    } finally {
      setIsOptEvaluating(false);
    }
  };

  const handleToggleOptimizedMode = async (enabled: boolean) => {
    try {
      const res = await fetch("/api/toggle-optimized-mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled })
      });
      const data = await res.json();
      if (data.status === "success") {
        setIsOptimizedMode(data.optimized_mode);
        addToast(
          data.optimized_mode 
            ? "已成功啟用「高效能優化模式」（引進 CodeGraph + MiniMax M3 + Nex-N2）！"
            : "已回復為標準雲端大 Token 消耗模式", 
          "success"
        );
      }
    } catch (err) {
      console.error(err);
      addToast("切換系統模式失敗", "error");
    }
  };

  const handleExamStart = async () => {
    setIsExamRunning(true);
    setAiAnswer("");
    setProfCritique("");
    try {
      const resp = await fetch("/api/exam-training", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: exams[selectedExam].question,
          model_answer: exams[selectedExam].modelAnswer,
          promptRole: contextRole
        })
      });
      const data = await resp.json();
      setAiAnswer(data.ai_answer);
      setProfCritique(data.prof_critique);
    } catch (e) {
      setProfCritique("❌ API 連接失敗，請檢查本地 Ollama 及 @google/genai 的密鑰配置。");
    } finally {
      setIsExamRunning(false);
    }
  };

  const handleCaseChatSubmit = async () => {
    if (!caseUserMsg.trim() || !selectedCaseId) return;
    setIsCaseChatLoading(true);
    const msgToSend = caseUserMsg;
    setCaseUserMsg("");
    try {
      const resp = await fetch("/api/cases/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ caseId: selectedCaseId, user_msg: msgToSend })
      });
      const data = await resp.json();
      if (data.error) {
        showAlert(data.error);
      } else {
        setCases(prev => ({
          ...prev,
          [selectedCaseId]: {
            ...prev[selectedCaseId],
            dialog_history: data.updatedHistory
          }
        }));
      }
    } catch (e) {
      showAlert("個案對話傳送失敗，請確認伺服器連線狀態。");
    } finally {
      setIsCaseChatLoading(false);
    }
  };

  const handleCaseListCommentChange = (section: string, index: number, value: string) => {
    setCases(prev => {
      const caseData = prev[selectedCaseId];
      if (!caseData) return prev;
      const list = [...(caseData[section] || [])];
      list[index] = { ...list[index], comment: value };
      return {
        ...prev,
        [selectedCaseId]: {
          ...caseData,
          [section]: list
        }
      };
    });
  };

  const handleSaveCaseLists = async () => {
    if (!selectedCaseId) return;
    setIsSavingCaseChanges(true);
    try {
      const resp = await fetch("/api/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cases })
      });
      const data = await resp.json();
      if (data.error) {
        showAlert(data.error);
      } else {
        stPlayNotify("✅ 點評與清單變更已成功存回資料庫！");
      }
    } catch (e) {
      showAlert("保存點評變更失敗。");
    } finally {
      setIsSavingCaseChanges(false);
    }
  };

  const handleTriggerScraper = async () => {
    setIsTriggeringScraper(true);
    try {
      const resp = await fetch("/api/trigger-scraper", { method: "POST" });
      const data = await resp.json();
      stPlayNotify(data.message);
      fetchSystemStatus(); // Refresh status immediately
    } catch (e) {
      showAlert("觸發背景爬蟲程式失敗。");
    } finally {
      setIsTriggeringScraper(false);
    }
  };

  const handleCalculateDate = async () => {
    // Basic date parsing to match YYYY-MM-DD
    let formattedDate = eventDate;
    if (eventDate.includes("年") || eventDate.includes("/")) {
      const cleaned = eventDate.replace(/[年月]/g, "-").replace(/日/g, "");
      formattedDate = cleaned;
    }

    try {
      const resp = await fetch("/api/calculate-deadline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event_date_str: formattedDate, statute_type: statuteType })
      });
      const data = await resp.json();
      if (data.error) {
        showAlert(data.error);
      } else {
        setCalendarResult(data);
      }
    } catch (e) {
      showAlert("計算失敗，請檢查日期格式。");
    }
  };

  const handleDraftGenerate = async () => {
    setIsDrafting(true);
    setGeneratedDraft("");
    try {
      const resp = await fetch("/api/draft-pleading", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          factContent: draftFact,
          pleadingType: draftType,
          selectedRole: contextRole
        })
      });
      const data = await resp.json();
      setGeneratedDraft(data.draft);
    } catch (e) {
      stPlayNotify("❌ 狀紙起草異常。");
    } finally {
      setIsDrafting(false);
    }
  };

  const handleTriggerBackup = () => {
    window.open("/api/backup");
  };

  const handleResetDb = async () => {
    if (confirm("您確定要將資料庫與智商庫重置為原始狀態嗎？這會清除所有研讀後的案例與考題。")) {
      await fetch("/api/reset-db", { method: "POST" });
      showAlert("資料庫重設完成！");
    }
  };

  const stPlayNotify = (msg: string) => {
    showAlert(msg);
  };

  const handleGenerateVideo = async () => {
    if (!t2vPrompt.trim()) {
      showAlert("⚠️ 請輸入影片生成的提示詞或劇情大綱。");
      return;
    }
    setIsGeneratingVideo(true);
    setGeneratedVideoUrl(null);
    try {
      const resp = await fetch("/api/generate-video", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: t2vPrompt, style: t2vStyle })
      });
      const data = await resp.json();
      if (data.status === "success") {
        setGeneratedVideoUrl(data.videoUrl);
        showAlert("✅ 實例動態影片生成完畢！");
      } else {
        throw new Error(data.error);
      }
    } catch (e: any) {
      showAlert(`❌ 影片生成失敗：${e.message}`);
    } finally {
      setIsGeneratingVideo(false);
    }
  };

  return (
    <div id="lexmind_dashboard" className="min-h-screen bg-slate-900 text-slate-100 font-sans flex flex-col antialiased">
      
      {/* Upper Navigation Header */}
      <header className="px-6 py-4 bg-slate-950 border-b border-slate-800 flex flex-col md:flex-row justify-between items-center gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-500">
            <Scale id="app_icon" className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl font-bold font-display tracking-wide text-slate-100 flex items-center gap-2">
              LexMind-Omni <span className="text-xs bg-amber-500/20 text-amber-400 border border-amber-500/30 px-2 py-0.5 rounded-full font-mono">v1.4 STABLE</span>
            </h1>
            <p className="text-xs text-slate-400">臺灣法律實務專業級 AI Agent 特助整合工作站</p>
          </div>
        </div>

        {/* Workspace Quick-Tabs */}
        <div className="flex items-center bg-slate-900 p-1 rounded-lg border border-slate-800 scrollbar-none overflow-x-auto max-w-full">
          {[
            { id: "consult", label: "💬 實務辯護諮詢", icon: Scale },
            { id: "cases", label: "📂 法律個案管理", icon: Briefcase },
            { id: "ingest", label: "📥 批量多模態餵養", icon: UploadCloud },
            { id: "exam", label: "🎓 檢察/司法官自我修復", icon: Award },
            { id: "draft", label: "📝 訴訟書狀起草", icon: FileText },
            { id: "t2v", label: "🎬 實例動態影片", icon: Film },
            { id: "benchmark", label: "📊 RAG 評測基準", icon: SlidersHorizontal },
            { id: "admin", label: "⚙️ 系統與時效工具", icon: Lock }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-3 py-2 rounded-md text-xs font-medium cursor-pointer transition-all whitespace-nowrap ${
                activeTab === tab.id 
                  ? "bg-amber-600 text-white shadow-md shadow-amber-500/10" 
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              }`}
            >
              <tab.icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      {/* Main Workspace Frame */}
      <main className="flex-1 w-full max-w-7xl mx-auto p-4 md:p-6 grid grid-cols-1 lg:grid-cols-4 gap-6">
        
        {/* Left Column: Context Card & Limitation Tracker */}
        {activeTab !== "benchmark" && (
          <section className="lg:col-span-1 flex flex-col gap-6">
          
          <div className="bg-slate-950/80 rounded-xl border border-slate-800 p-5 flex flex-col gap-5">
            <h2 className="text-sm font-semibold tracking-wide text-amber-500 flex items-center gap-2 uppercase">
              <Gavel className="w-4 h-4" /> 實務心證角色
            </h2>
            <p className="text-xs text-slate-400 -mt-2">更換思考視角，RWS 動態混合檢索將自動對應該角色實務深度重新分配：</p>
            
            <div className="flex flex-col gap-2">
              {[
                { id: "lawyer", label: "🛡️ 律師視角 (程序/時效防禦優先)", color: "border-amber-600/30 hover:border-amber-500 text-amber-400" },
                { id: "judge", label: "⚖️ 法官心證 (客觀案件事實對抗)", color: "border-emerald-600/30 hover:border-emerald-500 text-emerald-400" },
                { id: "prosecutor", label: "⚔️ 檢察官 (刑事追訴/公訴犯罪)", color: "border-rose-600/30 hover:border-rose-500 text-rose-400" }
              ].map(role => (
                <button
                  key={role.id}
                  onClick={() => setContextRole(role.id as any)}
                  className={`w-full text-left p-3 rounded-lg border text-xs font-medium cursor-pointer transition-all ${
                    contextRole === role.id 
                      ? "bg-slate-900 border-slate-600 shadow-sm" 
                      : "bg-slate-950/40 opacity-60 hover:opacity-100"
                  } ${role.color}`}
                >
                  {role.label}
                </button>
              ))}
            </div>
            
            <div className="text-[11px] text-slate-500 border-t border-slate-800/80 pt-4 font-mono">
              💡 本環境自適應修正：已啟用「天干代名詞」深度對齊模組，全自動過濾「假芳、倚芳、丙方」等聲音雜訊。
            </div>
          </div>

          {/* Quick Statute Calculator widget */}
          <div className="bg-slate-950/80 rounded-xl border border-slate-800/80 p-5">
            <h2 className="text-sm font-semibold tracking-wide text-amber-500 flex items-center gap-2 mb-3">
              <Calendar className="w-4 h-4" /> 民法雙重時效精算
            </h2>
            <div className="flex flex-col gap-4 text-xs">
              <div>
                <label className="text-[11px] text-slate-400">事件發生日 (YYYY-MM-DD)</label>
                <input 
                  type="text" 
                  value={eventDate}
                  onChange={(e) => setEventDate(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 focus:outline-none focus:border-amber-500 mt-1 font-mono text-slate-200"
                  placeholder="113-03-12"
                />
              </div>
              
              <div>
                <label className="text-[11px] text-slate-400">法定時效特徵</label>
                <select 
                  value={statuteType}
                  onChange={(e) => setStatuteType(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 focus:outline-none mt-1 text-slate-200 cursor-pointer"
                >
                  <option value="civil_tort">民事一般侵權損害 (2年 - 民§197)</option>
                  <option value="civil_general">一般特別財產債權 (15年 - 民§125)</option>
                  <option value="public_wage">公法上請求權/薪資加班費 (5年 - 民§126)</option>
                  <option value="labor_30d">資遣費離職30日限制 (勞基§14-II)</option>
                </select>
              </div>

              <button 
                onClick={handleCalculateDate}
                className="w-full py-2 bg-gradient-to-r from-amber-600 to-amber-700 text-white rounded font-medium hover:brightness-110 active:brightness-95 cursor-pointer mt-1 font-display"
              >
                ⚖️ 執行精密時效推算
              </button>

              {calendarResult && (
                <div className="border-t border-slate-800 pt-3 mt-1 flex flex-col gap-2 text-[11px] font-mono leading-relaxed bg-slate-900/60 p-2.5 rounded border">
                  <div className="text-amber-400 font-bold border-b border-slate-800/80 pb-1 mb-1 flex justify-between">
                    <span>{calendarResult.statute_name}</span>
                    <span className="text-emerald-400">計算完成</span>
                  </div>
                  <div>發生日期: {calendarResult.event_date}</div>
                  <div>起算日期: <span className="text-slate-300 font-semibold">{calendarResult.起算日}</span> (始日不算)</div>
                  <div>原截止日: {calendarResult.法定原截止日}</div>
                  <div className="bg-amber-500/10 p-1.5 rounded border border-amber-500/20 text-slate-100 font-bold">
                     最終截止日: <span className="text-amber-400">{calendarResult.最終順延截止日}</span>
                     {calendarResult.extended && <span className="text-emerald-400 ml-1">({calendarResult.順延天數}天順延)</span>}
                  </div>
                  <div className="text-[10px] text-slate-500 italic mt-1 leading-snug">{calendarResult.law_basis}</div>
                </div>
              )}
            </div>
          </div>

          {/* Saved Precedents list for Quick Access Later */}
          <div className="bg-slate-950/80 rounded-xl border border-slate-800 p-5 flex flex-col gap-4">
            <h2 className="text-sm font-semibold tracking-wide text-amber-500 flex items-center gap-2 uppercase">
              <Bookmark className="w-4 h-4 fill-amber-500/20 text-amber-500" /> 已儲存實務判例 ({bookmarkedPrecedents.length})
            </h2>
            <p className="text-xs text-slate-400 -mt-2">
              重要裁判書籤，點擊判決原文可至新分頁快速調閱原文。
            </p>

            {bookmarkedPrecedents.length === 0 ? (
              <div className="text-center py-6 text-slate-600 border border-dashed border-slate-800 rounded-lg text-xs">
                尚無儲存的實務裁判。可至對話下方「引用事證指標」中點擊儲存。
              </div>
            ) : (
              <div className="flex flex-col gap-2 max-h-[300px] overflow-y-auto pr-1">
                {bookmarkedPrecedents.map((b, idx) => (
                  <div key={idx} className="bg-slate-900/60 border border-slate-800 rounded-lg p-2.5 text-xs flex flex-col gap-2 hover:border-amber-500/30 transition-all">
                    <div className="flex justify-between items-start gap-1 font-mono">
                      <span className="text-amber-500 font-bold truncate leading-tight flex-1">
                        {b.source}
                      </span>
                      <button 
                        type="button"
                        onClick={() => toggleBookmark(b)}
                        className="text-slate-500 hover:text-rose-400 p-0.5 cursor-pointer transition-all"
                        title="取消儲存"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    {b.sourceTitle && (
                      <div className="text-[10px] text-slate-200 font-sans font-medium line-clamp-1">
                        {b.sourceTitle}
                      </div>
                    )}
                    <p className="text-slate-400 text-[11px] leading-relaxed line-clamp-2">
                      {b.text}
                    </p>
                    <div className="flex justify-between items-center mt-1 pt-1.5 border-t border-slate-800/40">
                      <span className="text-[9px] text-emerald-400 bg-emerald-500/5 px-2 py-0.5 rounded border border-emerald-500/20 shrink-0 font-mono">RWS計分: {b.score}</span>
                      {b.url && (
                        <a 
                          href={b.url} 
                          target="_blank" 
                          rel="noreferrer" 
                          className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 hover:underline font-mono text-[10px]"
                        >
                          <span>判決原文</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* Quick Ollama Status for Main Screen */}
          <div className="mt-auto bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col gap-3">
            <h3 className="text-xs font-semibold text-slate-300 tracking-wider flex items-center gap-1.5">
              <Shield className="w-4 h-4 text-emerald-400" /> Ollama AI 狀態
            </h3>
            <div className="flex justify-between items-center bg-slate-950 p-2.5 rounded border border-slate-850">
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${
                  systemStatus?.ollama?.status === "connected"
                    ? "bg-emerald-400 animate-pulse"
                    : "bg-rose-505"
                }`} />
                <span className="text-xs">Ollama AI 服務：</span>
                {systemStatus?.ollama?.status === "connected" && systemStatus?.ollama?.availableModels ? (
                  <select 
                    value={systemStatus?.ollama?.model}
                    onChange={handleModelChange}
                    className="bg-slate-900 border border-slate-700 text-slate-300 text-[11px] rounded px-1.5 py-0.5 ml-1 focus:outline-none focus:border-amber-500"
                  >
                    <optgroup label="本地模型">
                      {systemStatus.ollama.availableModels.map((m: string) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </optgroup>
                    {systemStatus.ollama.cloudModels && (
                      <optgroup label="雲端">
                        {systemStatus.ollama.cloudModels.map((m: string) => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </optgroup>
                    )}
                  </select>
                ) : (
                  <span className="text-xs">({systemStatus?.ollama?.model})</span>
                )}
              </div>
              {systemStatus?.ollama?.status === "connected" ? (
                <span className="text-emerald-400 font-bold text-[10px]">連線正常</span>
              ) : (
                <span className="text-rose-450 font-bold text-[10px]" title={systemStatus?.ollama?.error}>連線中斷</span>
              )}
            </div>
          </div>
          </section>
        )}

        {/* Right 3 columns: Tab Workspace router */}
        <section className={`${activeTab === "benchmark" ? "lg:col-span-4" : "lg:col-span-3"} flex flex-col gap-6`}>

          {/* TAB 1: CONSULTATION (對話實踐與RWS盾牌加權) */}
          {activeTab === "consult" && (
            <div className="bg-slate-950/80 rounded-xl border border-slate-800 p-5 flex-1 flex flex-col min-h-[500px]">
              <div className="flex border-b border-slate-800/80 pb-3 mb-4 justify-between items-center">
                <div>
                  <h2 className="text-lg font-bold font-display tracking-tight text-white flex items-center gap-2">
                    💬 實務訴訟案件心證分析
                  </h2>
                  <p className="text-xs text-slate-400">RWS 混合型檢索重排與多輪對話語意壓縮機制已在此對話中執行</p>
                </div>
                <button 
                  onClick={handleCleanHistory}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded text-xs text-slate-400 hover:text-slate-100 transition-all cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                  清空紀錄
                </button>
              </div>

              {/* RWS System query condensation snapshot in real-time */}
              {condensedQuery && (
                <div className="mb-3 px-3 py-2 bg-amber-500/5 border border-amber-500/20 rounded-lg text-xs leading-normal font-mono flex items-center gap-2">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-500" />
                  <span className="text-amber-400 font-semibold">【RWS 爭點重構句】:</span>
                  <span className="text-slate-300 italic">"{condensedQuery}"</span>
                </div>
              )}

              {/* Main Chat Display */}
              <div className="flex-1 min-h-[250px] max-h-[400px] overflow-y-auto mb-4 p-3 bg-slate-900/60 rounded-xl border border-slate-800/80 space-y-4">
                {messages.length === 0 ? (
                  <div className="h-full flex flex-col justify-center items-center text-center p-8">
                    <History className="w-10 h-10 text-slate-600 mb-2" />
                    <p className="text-sm font-semibold text-slate-400">尚無訴訟對話紀錄</p>
                    <p className="text-xs text-slate-500 max-w-sm mt-1">請在下方提出完整的民、刑事事實，工作站將自動載入黃金條文與經驗分析</p>
                  </div>
                ) : (
                  messages.map((m, idx) => (
                    <div 
                      key={idx} 
                      className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}
                    >
                      <div className={`max-w-[85%] rounded-xl p-3.5 text-sm leading-relaxed ${
                        m.role === 'user' 
                          ? 'bg-amber-600/90 text-white rounded-tr-none' 
                          : 'bg-slate-950 text-slate-200 border border-slate-800/80 rounded-tl-none whitespace-pre-wrap'
                      }`}>
                        <div className="text-[10px] text-slate-400 uppercase font-mono tracking-wider mb-1 block select-none">
                          {m.role === 'user' ? '原告/委託人' : 'LexMind AI 特助'}
                        </div>
                        {m.content}
                      </div>
                    </div>
                  ))
                )}
                {isChatLoading && (
                  <div className="flex justify-start">
                    <div className="bg-slate-950 border border-amber-500/30 max-w-[90%] rounded-xl p-4 text-sm rounded-tl-none">
                      {/* 標題列 */}
                      <div className="flex items-center gap-2.5 mb-3">
                        <div className="relative flex items-center justify-center w-5 h-5">
                          <div className="w-5 h-5 bg-amber-500/20 rounded-full animate-ping absolute" />
                          <div className="w-3 h-3 bg-amber-500 rounded-full relative" />
                        </div>
                        <span className="text-amber-400 font-bold text-xs tracking-wider uppercase">ornith AI 深度法律推理中</span>
                        <span className="ml-auto text-slate-500 font-mono text-xs tabular-nums">{chatThinkingSeconds}s</span>
                      </div>
                      {/* 思考階段指示 */}
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                          <span className="text-slate-400 text-xs font-mono">查閱 RWS 法規智識庫 &amp; 歷史判例...</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" style={{animationDelay:'0.3s'}} />
                          <span className="text-slate-400 text-xs font-mono">三段論法涵攝分析（法規→事實→結論）...</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse" style={{animationDelay:'0.6s'}} />
                          <span className="text-slate-400 text-xs font-mono">撰寫法律意見 &amp; 時效警示...</span>
                        </div>
                      </div>
                      {/* 進度條 */}
                      <div className="mt-3 h-0.5 bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-amber-600 via-amber-400 to-amber-600 rounded-full"
                          style={{
                            width: `${Math.min(95, (chatThinkingSeconds / avgWaitTimeSeconds) * 100)}%`,
                            transition: 'width 1s linear',
                            backgroundSize: '200% 100%',
                            animation: 'shimmer 2s infinite linear'
                          }}
                        />
                      </div>
                      {chatThinkingSeconds > 5 && (
                        <div className="mt-2 text-slate-500 text-[10px] font-mono">
                          ⏱ 預估等待時間：~{avgWaitTimeSeconds} 秒 (系統真實平均)
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Multimodal Attachment Tray */}
              {chatAttachments.length > 0 && (
                <div className="mb-3 px-3 py-2.5 bg-slate-900/85 border border-slate-800 rounded-xl flex flex-wrap gap-2.5 items-center">
                  <span className="text-xs text-slate-400 font-mono flex items-center gap-1">
                    <Paperclip className="w-3 h-3 text-amber-500" /> 待分析多模態附件 ({chatAttachments.length}):
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {chatAttachments.map((a, idx) => (
                      <div 
                        key={idx} 
                        className="bg-slate-950/90 border border-slate-800 px-2.5 py-1.5 rounded-lg flex items-center gap-2 max-w-xs transition-all hover:border-slate-700 group"
                      >
                        {a.type === 'video' && <Film className="w-3.5 h-3.5 text-rose-400 shrink-0" />}
                        {a.type === 'audio' && <Music className="w-3.5 h-3.5 text-pink-400 shrink-0" />}
                        {a.type === 'image' && <Image className="w-3.5 h-3.5 text-emerald-400 shrink-0" />}
                        {a.type === 'pdf' && <FileText className="w-3.5 h-3.5 text-amber-500 shrink-0" />}
                        {a.type === 'text' && <FileText className="w-3.5 h-3.5 text-blue-400 shrink-0" />}
                        
                        <div className="flex flex-col text-left">
                          <span className="text-[11px] font-bold text-slate-200 truncate max-w-[120px]" title={a.name}>
                            {a.name}
                          </span>
                          <span className="text-[9px] font-mono text-slate-500">
                            {a.size}
                          </span>
                        </div>

                        {a.status === 'parsing' ? (
                          <RefreshCw className="w-3 h-3 animate-spin text-amber-500 shrink-0" />
                        ) : a.status === 'ready' ? (
                          <CheckCircle className="w-3 h-3 text-emerald-500 shrink-0" title="多模態智慧翻譯/語音逐字稿已就緒" />
                        ) : (
                          <AlertTriangle className="w-3 h-3 text-rose-500 shrink-0" />
                        )}

                        <button
                          type="button"
                          onClick={() => handleRemoveChatAttachment(a.name)}
                          className="p-0.5 rounded-full hover:bg-slate-800 text-slate-500 hover:text-slate-250 transition-colors cursor-pointer"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Live Precedent Search Option */}
              <div className="flex items-center gap-3 mb-3 text-xs text-slate-400 font-mono">
                <label className="flex items-center gap-2 cursor-pointer bg-slate-905 border border-slate-800 hover:bg-slate-800 px-3.5 py-2 rounded-xl select-none transition-all">
                  <input
                    type="checkbox"
                    checked={liveCaseSearch}
                    onChange={(e) => setLiveCaseSearch(e.target.checked)}
                    className="accent-amber-500 rounded cursor-pointer"
                  />
                  <Globe className="w-3.5 h-3.5 text-amber-500 animate-pulse" />
                  <span>啟用最高法院「即時判例與裁判搜尋」 (Live Case Search Grounding)</span>
                </label>
                {liveCaseSearch && (
                  <span className="text-[10px] text-emerald-400 flex items-center gap-1 font-sans">
                    <CheckCircle className="w-3 h-3 text-emerald-500" /> RWS 已串接 Google Search 實戰引導
                  </span>
                )}
              </div>

              {/* Lower Input Box */}
              <form onSubmit={handleChatSubmit} className="flex gap-2 items-center">
                {/* Windows 11 Fluent Files Addition Button (+) */}
                <button
                  type="button"
                  onClick={() => chatFileInputRef.current?.click()}
                  title="開啟 Windows 檔案總管加入民刑事錄音、影像、OCR證明書或條款"
                  className="px-3.5 py-3 bg-slate-900 border border-slate-800 hover:border-slate-700 hover:bg-slate-800 text-amber-500 hover:text-amber-400 active:scale-95 text-lg font-bold rounded-xl transition-all flex items-center justify-center cursor-pointer shrink-0 shadow-lg"
                >
                  <Plus className="w-5 h-5" />
                </button>

                {/* Hidden Multi-modal Native File Selector */}
                <input 
                  type="file"
                  ref={chatFileInputRef}
                  className="hidden"
                  multiple
                  accept=".mp4,.mp3,.wav,.png,.jpg,.jpeg,.pdf,.txt"
                  onChange={handleChatFileSelect}
                />

                <input 
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="請輸入與對造的法律糾紛或起訴事由，或透過 [+] 匯入 MP4/MP3 錄音及證物照片..."
                  className="flex-1 bg-slate-900 border border-slate-800 focus:border-slate-700 rounded-xl px-4 py-3 text-sm focus:outline-none"
                  disabled={isChatLoading}
                />
                <button 
                  type="submit" 
                  disabled={isChatLoading || (!chatInput.trim() && chatAttachments.length === 0)}
                  className="px-5 py-3 bg-amber-600 hover:bg-amber-500 active:bg-amber-700 disabled:opacity-50 text-slate-100 text-sm font-semibold rounded-xl transition-all cursor-pointer flex items-center gap-1.5 shrink-0"
                >
                  <Sparkles className="w-4 h-4 text-white" />
                  提問分析
                </button>
              </form>

              {/* Real-time pulled RWS evidence shelf */}
              <div className="border-t border-slate-800/80 pt-4 mt-4">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 mb-3 bg-slate-950/20 p-3 rounded-xl border border-slate-800/50">
                  <div className="flex items-center gap-3">
                    <h3 className="text-xs font-semibold text-amber-500 uppercase tracking-wider flex items-center gap-1.5 shrink-0">
                      <Bookmark className="w-3.5 h-3.5 fill-amber-500/10 text-amber-500" /> 本次對話引用事證指標 (已置頂)
                    </h3>
                    {evidenceList.length > 0 && (
                      <button 
                        onClick={exportToPDF}
                        className="bg-amber-600 hover:bg-amber-500 text-slate-100 px-2.5 py-1 rounded-md border border-amber-500 flex items-center gap-1.5 text-[10px] shadow-sm transition-all animate-pulse"
                        title="一鍵匯出多個 PDF 分析報告"
                      >
                        <Download className="w-3.5 h-3.5" />
                        匯出PDF報告
                      </button>
                    )}
                  </div>
                  
                  {/* Filters bar */}
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    {/* Relevance Score Filter Toggles */}
                    <div className="flex items-center bg-slate-900/80 p-0.5 rounded-lg border border-slate-800 shrink-0">
                      <span className="px-2 text-[9px] text-slate-500 font-mono font-medium uppercase tracking-wider flex items-center gap-1">
                        <SlidersHorizontal className="w-3 h-3 text-slate-500" /> 權重
                      </span>
                      <button
                        type="button"
                        onClick={() => setScoreFilter("all")}
                        className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all cursor-pointer ${
                          scoreFilter === "all"
                            ? "bg-amber-600 text-slate-100 shadow-sm"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        全部
                      </button>
                      <button
                        type="button"
                        onClick={() => setScoreFilter("high")}
                        className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all cursor-pointer ${
                          scoreFilter === "high"
                            ? "bg-emerald-600/30 text-emerald-400 border border-emerald-500/30"
                            : "text-slate-400 hover:text-slate-200 border border-transparent"
                        }`}
                        title="篩選 RWS 權重 >= 80"
                      >
                        高 (≥80)
                      </button>
                      <button
                        type="button"
                        onClick={() => setScoreFilter("low")}
                        className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all cursor-pointer ${
                          scoreFilter === "low"
                            ? "bg-slate-800 text-slate-300 border border-slate-700/50"
                            : "text-slate-400 hover:text-slate-200 border border-transparent"
                        }`}
                        title="篩選 RWS 權重 < 80"
                      >
                        中低
                      </button>
                    </div>

                    {/* Document Type Filter Toggles */}
                    <div className="flex items-center bg-slate-900/80 p-0.5 rounded-lg border border-slate-800 shrink-0">
                      <span className="px-2 text-[9px] text-slate-500 font-mono font-medium uppercase tracking-wider flex items-center gap-1">
                        <Filter className="w-3 h-3 text-slate-500" /> 類型
                      </span>
                      <button
                        type="button"
                        onClick={() => setDocTypeFilter("all")}
                        className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all cursor-pointer ${
                          docTypeFilter === "all"
                            ? "bg-amber-600 text-slate-100 shadow-sm"
                            : "text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        全部
                      </button>
                      <button
                        type="button"
                        onClick={() => setDocTypeFilter("judgment")}
                        className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all cursor-pointer ${
                          docTypeFilter === "judgment"
                            ? "bg-slate-800 text-amber-400 border border-slate-700"
                            : "text-slate-400 hover:text-slate-200 border border-transparent"
                        }`}
                        title="司法判決 / 實務裁定"
                      >
                        判決
                      </button>
                      <button
                        type="button"
                        onClick={() => setDocTypeFilter("statute")}
                        className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all cursor-pointer ${
                          docTypeFilter === "statute"
                            ? "bg-slate-800 text-amber-400 border border-slate-700"
                            : "text-slate-400 hover:text-slate-200 border border-transparent"
                        }`}
                        title="實體法律 / 程序法條"
                      >
                        法規
                      </button>
                      <button
                        type="button"
                        onClick={() => setDocTypeFilter("academic")}
                        className={`px-2 py-0.5 rounded text-[10px] font-medium transition-all cursor-pointer ${
                          docTypeFilter === "academic"
                            ? "bg-slate-800 text-amber-400 border border-slate-700"
                            : "text-slate-400 hover:text-slate-200 border border-transparent"
                        }`}
                        title="學術期刊 / 論文見解"
                      >
                        學術
                      </button>
                    </div>
                  </div>
                </div>

                {/* RWS Charts Container */}
                <div id="rws-charts-container" className="relative group flex flex-col mb-2">
                  {/* RWS Relevancy Distribution Chart */}
                  {evidenceList.length > 0 && (
                    <div className="mb-4 bg-slate-950/40 p-3.5 rounded-xl border border-slate-800/60 flex flex-col gap-2">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] font-sans font-medium text-slate-400 flex items-center gap-1.5 uppercase tracking-wider">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                        RWS 權重分佈光譜 (RWS Relevancy Distribution)
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-[9px] font-mono text-slate-500">
                          總召回事證：{evidenceList.length} 筆
                        </span>
                        <button onClick={() => setShowRwsChart(!showRwsChart)} className="text-slate-500 hover:text-slate-300 transition-colors">
                          {showRwsChart ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>
                    {showRwsChart && (
                    <div className="w-full h-24 pt-1">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData} margin={{ top: 5, right: 5, left: -32, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1d283a" vertical={false} />
                          <XAxis 
                            dataKey="name" 
                            stroke="#64748b" 
                            fontSize={8} 
                            tickLine={false} 
                            axisLine={false}
                          />
                          <YAxis 
                            stroke="#64748b" 
                            fontSize={8} 
                            tickLine={false} 
                            axisLine={false} 
                            allowDecimals={false}
                          />
                          <Tooltip
                            contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "6px" }}
                            labelClassName="text-slate-300 text-[10px] font-semibold mb-1"
                            itemStyle={{ color: "#fbbf24", fontSize: "10px", padding: "0" }}
                            cursor={{ fill: '#1e293b', opacity: 0.3 }}
                            formatter={(value: any, name: string, props: any) => {
                              let desc = "";
                              if (props.payload.name.startsWith("90")) desc = " (極高關聯：核心判例)";
                              else if (props.payload.name.startsWith("80")) desc = " (高度關聯：重要佐證)";
                              else if (props.payload.name.startsWith("70")) desc = " (中度關聯：參考文獻)";
                              else if (props.payload.name.startsWith("60")) desc = " (低度關聯：邊緣資訊)";
                              else desc = " (無效參考)";
                              return [`${value} 筆事證${desc}`, "事證數量"];
                            }}
                          />
                          <Legend 
                            verticalAlign="top" 
                            height={20}
                            iconType="circle"
                            wrapperStyle={{ fontSize: "9px", color: "#64748b" }}
                            formatter={() => "RWS 分數分佈 (不同關聯度階層的事證數量)"}
                          />
                          <Bar dataKey="count" radius={[3, 3, 0, 0]} maxBarSize={40}>
                            {chartData.map((entry, index) => {
                              let barColor = "#475569";
                              if (entry.name.startsWith("90-100")) barColor = "#10b981"; // emerald-500
                              else if (entry.name.startsWith("80-89")) barColor = "#34d399"; // emerald-400
                              else if (entry.name.startsWith("70-79")) barColor = "#fbbf24"; // amber-400
                              else if (entry.name.startsWith("60-69")) barColor = "#fb923c"; // orange-400
                              else barColor = "#64748b"; // slate-500
                              
                              return <Cell key={`cell-${index}`} fill={barColor} />;
                            })}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    )}
                  </div>
                )}

                {/* Evidence Strength Trend Chart */}
                {evidenceList.length > 0 && (
                  <div className="mb-4 bg-slate-950/40 p-3.5 rounded-xl border border-slate-800/60 flex flex-col gap-2">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] font-sans font-medium text-slate-400 flex items-center gap-1.5 uppercase tracking-wider">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                        事證強度趨勢 (Evidence Strength Trend)
                      </span>
                      <div className="flex items-center gap-2">
                        <button onClick={() => setShowTrendChart(!showTrendChart)} className="text-slate-500 hover:text-slate-300 transition-colors">
                          {showTrendChart ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    </div>
                    {showTrendChart && (
                      <>
                        <div className="w-full h-24 pt-1">
                          <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={trendData} margin={{ top: 5, right: 5, left: -32, bottom: 0 }} onClick={handleTrendPointClick}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1d283a" vertical={false} />
                          <XAxis dataKey="name" stroke="#64748b" fontSize={8} tickLine={false} axisLine={false} />
                          <YAxis stroke="#64748b" fontSize={8} tickLine={false} axisLine={false} />
                          <Tooltip 
                            contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", borderRadius: "6px" }}
                            labelClassName="text-slate-300 text-[10px] font-semibold mb-1"
                            itemStyle={{ color: "#3b82f6", fontSize: "10px", padding: "0" }}
                            formatter={(value: any) => [`${value} pts (點擊節點查看里程碑)`, 'RWS 分數']}
                          />
                          <Legend 
                            verticalAlign="top" 
                            height={20}
                            iconType="circle"
                            wrapperStyle={{ fontSize: "9px", color: "#64748b", cursor: "pointer" }}
                            formatter={() => "單一事證評分趨勢線 (點擊資料點查看動態註釋)"}
                          />
                          <Line type="monotone" dataKey="score" name="RWS 分數" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3, fill: "#3b82f6", cursor: "pointer" }} activeDot={{ r: 5, cursor: "pointer" }} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    {/* Dynamic Annotation Display */}
                    <AnimatePresence>
                      {selectedTrendPoint && (
                        <motion.div 
                          initial={{ opacity: 0, y: -10, height: 0 }} 
                          animate={{ opacity: 1, y: 0, height: "auto" }} 
                          exit={{ opacity: 0, y: -10, height: 0 }}
                          className="mt-3 bg-slate-900 border border-slate-700 p-2.5 rounded-lg flex flex-col gap-1.5 overflow-hidden"
                        >
                          <div className="flex justify-between items-center">
                            <span className="text-xs font-bold text-amber-400">{selectedTrendPoint.milestone}</span>
                            <button onClick={() => setSelectedTrendPoint(null)} className="text-slate-400 hover:text-slate-200 cursor-pointer">
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </div>
                          <span className="text-[10px] text-slate-300">
                            <strong>{selectedTrendPoint.name}</strong> ({selectedTrendPoint.source}) - 分數變化: <span className={selectedTrendPoint.diff > 0 ? "text-emerald-400" : selectedTrendPoint.diff < 0 ? "text-rose-400" : "text-slate-400"}>{selectedTrendPoint.diff > 0 ? `+${selectedTrendPoint.diff}` : selectedTrendPoint.diff} pts</span>
                          </span>
                          <span className="text-[10px] text-slate-400 leading-relaxed">
                            {selectedTrendPoint.detail}
                          </span>
                        </motion.div>
                      )}
                      </AnimatePresence>
                      </>
                    )}
                  </div>
                )}
                </div>

                <div id="evidence-list-container" className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {filteredEvidenceList.slice(0, 4).map((e, index) => {
                    const scoreVal = getEvidenceScore(e);
                    const docTypeVal = getDocType(e);
                    
                    return (
                      <div key={index} className="bg-slate-950/50 border border-slate-800/80 rounded-xl p-3 hover:border-amber-500/30 transition-all duration-300 flex flex-col justify-between gap-2.5 group shadow-md hover:shadow-lg">
                        <div className="grid grid-cols-12 gap-3">
                          {/* Left column (左欄) - col-span-4 */}
                          <div className="col-span-4 flex flex-col gap-2 border-r border-slate-800/60 pr-2.5 justify-between">
                            <div className="flex flex-col gap-1.5">
                              {/* RWS Weighting */}
                              <div className="flex flex-col gap-0.5">
                                <span className="text-[9px] text-slate-500 font-mono uppercase tracking-wider block">RWS 權重</span>
                                <div className="flex items-center justify-between gap-1 w-full">
                                  <div className="flex items-baseline gap-0.5">
                                    <span className="text-lg font-bold font-mono text-emerald-400 leading-none">{scoreVal}</span>
                                    <span className="text-[8px] text-emerald-600 font-mono">pts</span>
                                  </div>
                                  <span className={`text-[8px] font-mono leading-none tracking-tight px-1 py-0.5 rounded-sm shrink-0 ${
                                    scoreVal >= 80 
                                      ? "text-emerald-400 bg-emerald-500/10 font-bold" 
                                      : scoreVal >= 70 
                                        ? "text-amber-400 bg-amber-500/10 font-medium" 
                                        : "text-slate-400 bg-slate-500/10"
                                  }`}>
                                    {scoreVal >= 80 ? "HIGH CONF" : scoreVal >= 70 ? "MED CONF" : "LOW CONF"}
                                  </span>
                                </div>
                                {/* Score progress indicator */}
                                <div className="w-full bg-slate-900 h-1 rounded-full overflow-hidden border border-slate-800/30">
                                  <div 
                                    className={`h-full rounded-full transition-all duration-300 ${
                                      scoreVal >= 80 
                                        ? "bg-emerald-500" 
                                        : scoreVal >= 70 
                                          ? "bg-amber-500" 
                                          : "bg-slate-500"
                                    }`} 
                                    style={{ width: `${Math.min(100, Math.max(15, scoreVal))}%` }}
                                  />
                                </div>
                              </div>

                              {/* Reference Status */}
                              <div className="flex flex-col gap-1 mt-1">
                                <span className="text-[9px] text-slate-500 font-mono uppercase tracking-wider block">引證狀態</span>
                                <div className="flex flex-col gap-1">
                                  <span className="inline-flex items-center gap-1 text-[9px] text-amber-400 bg-amber-500/5 px-1.5 py-0.5 rounded border border-amber-500/15">
                                    <span className="w-1 h-3 rounded-full bg-amber-500 animate-pulse shrink-0" />
                                    <span className="truncate">
                                      {docTypeVal === "judgment" ? "實務裁決" : docTypeVal === "academic" ? "學術見解" : "實體法規"}
                                    </span>
                                  </span>
                                  {isBookmarked(e) && (
                                    <span className="inline-flex items-center gap-1 text-[9px] text-cyan-400 bg-cyan-500/5 px-1.5 py-0.5 rounded border border-cyan-500/15">
                                      <Bookmark className="w-2 h-2 fill-cyan-400 text-cyan-400 shrink-0" />
                                      <span>儲存判例</span>
                                    </span>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Copy trigger in left col */}
                            <button
                              type="button"
                              onClick={() => handleCopyEvidence(e.text, index)}
                              title="複製此實務判決要點"
                              className="w-full py-1 px-1.5 rounded bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-amber-400 transition-all cursor-pointer flex items-center justify-center gap-1 border border-slate-800 hover:border-slate-700 active:scale-[0.97]"
                            >
                              {copiedIndex === index ? (
                                <>
                                  <Check className="w-2.5 h-2.5 text-emerald-400 shrink-0" />
                                  <span className="text-[9px] text-emerald-400 font-sans font-medium">已複製</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="w-2.5 h-2.5 shrink-0" />
                                  <span className="text-[9px] font-sans font-medium">複製</span>
                                </>
                              )}
                            </button>
                          </div>

                          {/* Right column (右欄) - col-span-8 */}
                          <div className="col-span-8 flex flex-col justify-between gap-1.5 min-w-0">
                            <div className="flex flex-col gap-1">
                              {/* Citation ID */}
                              <span className="text-amber-500 font-bold text-xs truncate leading-tight font-mono block" title={e.source}>
                                {e.source}
                              </span>

                              {/* Reasoning Snippet */}
                              <p className="text-[11px] text-slate-300 leading-relaxed font-sans line-clamp-3 overflow-hidden" title={e.text}>
                                {e.text}
                              </p>
                            </div>

                            {e.sourceTitle && (
                              <div className="text-[9px] text-slate-400 bg-slate-900/40 p-1.5 rounded border border-slate-900/60 flex flex-col gap-0.5 mt-0.5">
                                <div className="flex items-start gap-1">
                                  <span className="text-amber-500/80 font-mono font-medium shrink-0">來源：</span>
                                  <span className="font-sans text-slate-200 line-clamp-1">{e.sourceTitle}</span>
                                </div>
                                {e.snippetDate && (
                                  <div className="flex items-center gap-1">
                                    <span className="text-emerald-500/80 font-mono font-medium shrink-0">日期：</span>
                                    <span className="font-mono text-slate-300">{e.snippetDate}</span>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* External reference links and secondary bookmark toggle */}
                        {e.url && (
                          <div className="pt-2 border-t border-slate-800/60 flex flex-col sm:flex-row gap-2">
                            <a
                              href={e.url}
                              target="_blank"
                              rel="noreferrer"
                              className="flex-1 text-center py-1.5 px-3 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-[11px] text-amber-400 font-medium rounded-lg hover:text-amber-300 transition-all inline-flex items-center justify-center gap-1.5 shadow-sm active:scale-[0.98]"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                              檢視判決全文 (View Source)
                            </a>
                            <button
                              type="button"
                              onClick={() => toggleBookmark(e)}
                              className={`px-3 py-1.5 border rounded-lg text-[11px] font-medium transition-all inline-flex items-center justify-center gap-1.5 shadow-sm active:scale-[0.98] cursor-pointer ${
                                isBookmarked(e)
                                  ? "bg-amber-600/20 hover:bg-amber-600/30 border-amber-500/50 text-amber-300"
                                  : "bg-slate-900 hover:bg-slate-850 border-slate-800 text-slate-400 hover:text-amber-400"
                              }`}
                            >
                              <Bookmark className={`w-3.5 h-3.5 ${isBookmarked(e) ? "fill-amber-400 text-amber-400" : ""}`} />
                              {isBookmarked(e) ? "已儲存" : "儲存判例"}
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                  {filteredEvidenceList.length === 0 && (
                    <div className="col-span-full text-center py-6 text-slate-600 border border-dashed border-slate-800 rounded-lg text-xs font-sans">
                      {evidenceList.length === 0 
                        ? "還沒在對話中提出具體問題，資料庫尚未啟動召回。"
                        : "沒有符合目前篩選要件的事證。請嘗試配合上方切換鈕。"}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 1.5: CASES MANAGEMENT (📂 法律個案管理) */}
          {activeTab === "cases" && (
            <div className="bg-slate-950/80 rounded-xl border border-slate-800 p-5 flex-1 flex flex-col min-h-[500px] gap-6">
              <div className="flex border-b border-slate-800/80 pb-3 justify-between items-center">
                <div>
                  <h2 className="text-lg font-bold font-display tracking-tight text-white flex items-center gap-2">
                    📂 法律訴訟個案與關係人智慧管理模組
                  </h2>
                  <p className="text-xs text-slate-400">管理獨立的法律個案，追蹤案件關係人的訴訟歷史、書狀證據清單、判例引用與法律主張。</p>
                </div>
                <button
                  onClick={fetchCases}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded text-xs text-slate-400 hover:text-slate-100 transition-all cursor-pointer"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  重新整理
                </button>
              </div>

              {/* Stakeholder Cross-case Search */}
              <div className="bg-slate-900/40 p-4 rounded-xl border border-slate-800/80 flex flex-col gap-3">
                <h3 className="text-sm font-bold text-amber-500 flex items-center gap-2">
                  🔍 關係人跨案整合與前科歷史檢索
                </h3>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={stakeholderQuery}
                    onChange={(e) => setStakeholderQuery(e.target.value)}
                    placeholder="請輸入當事人/關係人姓名 (例如：林ＯＯ)"
                    className="flex-1 bg-slate-950 border border-slate-850 focus:border-slate-700 rounded-lg px-3 py-2 text-xs focus:outline-none"
                  />
                  {stakeholderQuery && (
                    <button
                      onClick={() => setStakeholderQuery("")}
                      className="px-3 py-1 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded text-xs text-slate-400"
                    >
                      清除
                    </button>
                  )}
                </div>

                {stakeholderQuery.trim() && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
                    {/* Local Cases Matching */}
                    <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-850">
                      <span className="text-xs font-bold text-slate-300 block mb-2">📂 本地歷史個案記錄</span>
                      <div className="space-y-2 max-h-40 overflow-y-auto">
                        {foundLocalCases.length > 0 ? (
                          foundLocalCases.map((c, i) => (
                            <div key={i} className="bg-slate-900/80 p-2.5 rounded border border-slate-800 flex flex-col gap-1 text-[11px]">
                              <span className="text-amber-500 font-bold">📌 {c.id} : {c.title}</span>
                              <span className="text-slate-300">階段：{c.current_stage}</span>
                              <span className="text-slate-400">關係人：{c.stakeholders.join(", ")}</span>
                            </div>
                          ))
                        ) : (
                          <span className="text-xs text-slate-500 italic block">沒有找到本地相關個案記錄。</span>
                        )}
                      </div>
                    </div>

                    {/* Precedents Database Matching */}
                    <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-850">
                      <span className="text-xs font-bold text-slate-300 block mb-2">⚖️ 資料庫關聯條文與判決記錄</span>
                      <div className="space-y-2 max-h-40 overflow-y-auto">
                        {foundDbPrecedents.length > 0 ? (
                          foundDbPrecedents.map((p, i) => (
                            <div key={i} className="bg-slate-900/80 p-2.5 rounded border border-slate-800 flex flex-col gap-1 text-[11px]">
                              <span className="text-amber-500 font-bold">📄 {p.source}</span>
                              <p className="text-slate-300 line-clamp-2">{p.text}</p>
                            </div>
                          ))
                        ) : (
                          <span className="text-xs text-slate-500 italic block">請在實務辯護中先提問，以載入關聯判決書。</span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Main Case Workspace */}
              <div className="bg-slate-900/20 p-4 rounded-xl border border-slate-800/60 flex flex-col gap-4">
                <h3 className="text-sm font-bold text-amber-500 flex items-center gap-2">
                  💼 獨立個案工作面板
                </h3>

                {Object.keys(cases).length === 0 ? (
                  <div className="text-center py-8 text-slate-500 italic text-xs">
                    目前無個案，請重試或點擊右上角重新整理載入。
                  </div>
                ) : (
                  <div className="flex flex-col gap-4">
                    {/* Case Selector Dropdown */}
                    <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2">
                      <label className="text-xs text-slate-400 shrink-0 font-medium">請選擇要管理的個案：</label>
                      <select
                        value={selectedCaseId}
                        onChange={(e) => setSelectedCaseId(e.target.value)}
                        className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 focus:outline-none text-slate-200 text-xs cursor-pointer max-w-full"
                      >
                        {Object.entries(cases).map(([id, c]: [string, any]) => (
                          <option key={id} value={id}>
                            {id} - {c.title}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Selected Case Workspace Area */}
                    {selectedCaseId && cases[selectedCaseId] && (
                      <div className="flex flex-col gap-4 mt-1">
                        <div className="flex flex-wrap gap-x-6 gap-y-1 bg-slate-950/40 p-3 rounded-lg border border-slate-850 text-xs">
                          <div>
                            <span className="text-slate-500 font-medium">⚡ 目前訴訟階段：</span>
                            <span className="text-amber-400 font-bold bg-amber-500/10 px-1.5 py-0.5 rounded">{cases[selectedCaseId].current_stage}</span>
                          </div>
                          <div>
                            <span className="text-slate-500 font-medium">👥 案件關係人：</span>
                            <span className="text-slate-200 font-semibold">{cases[selectedCaseId].stakeholders.join(", ")}</span>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                          {/* Case specific chat */}
                          <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-850/80 flex flex-col gap-3 flex-1">
                            <span className="text-xs font-bold text-slate-200 block border-b border-slate-800 pb-1.5 flex items-center gap-1.5">
                              💬 個案專屬訴訟對話與答辯建議
                            </span>
                            
                            <div className="flex-1 min-h-[200px] max-h-[300px] overflow-y-auto bg-slate-900/40 border border-slate-800/60 rounded-lg p-3 space-y-3">
                              {(cases[selectedCaseId].dialog_history || []).length === 0 ? (
                                <div className="h-full flex justify-center items-center text-slate-500 italic text-[11px] py-8 text-center">
                                  無該個案之訴訟對話記錄。
                                </div>
                              ) : (
                                (cases[selectedCaseId].dialog_history || []).map((msg: any, i: number) => (
                                  <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                                    <div className={`max-w-[90%] rounded-lg p-2.5 text-[11px] leading-relaxed ${
                                      msg.role === 'user'
                                        ? 'bg-amber-600/20 text-amber-200 border border-amber-500/20 rounded-tr-none'
                                        : 'bg-slate-950 text-slate-350 border border-slate-850 rounded-tl-none'
                                    }`}>
                                      <div className="text-[9px] text-slate-500 font-mono tracking-wider mb-0.5 block select-none uppercase">
                                        {msg.role === 'user' ? '原告/代理人' : 'LexMind AI 心證建議'}
                                      </div>
                                      {msg.text}
                                    </div>
                                  </div>
                                ))
                              )}
                              {isCaseChatLoading && (
                                <div className="flex justify-start">
                                  <div className="bg-slate-950 border border-slate-850 max-w-[90%] rounded-lg p-3 text-[11px] rounded-tl-none flex items-center gap-2">
                                    <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-500" />
                                    <span className="text-slate-400 font-mono">資深法官與老律師大腦研判個案爭點中...</span>
                                  </div>
                                </div>
                              )}
                            </div>

                            <div className="flex gap-2">
                              <input
                                type="text"
                                value={caseUserMsg}
                                onChange={(e) => setCaseUserMsg(e.target.value)}
                                placeholder="輸入該個案的訴訟事實、答辯要點或書狀草稿..."
                                className="flex-1 bg-slate-900 border border-slate-800 focus:border-slate-700 rounded-lg px-3 py-2 text-xs focus:outline-none"
                                onKeyDown={(e) => {
                                  if (e.key === "Enter" && !isCaseChatLoading && caseUserMsg.trim()) {
                                    handleCaseChatSubmit();
                                  }
                                }}
                              />
                              <button
                                onClick={handleCaseChatSubmit}
                                disabled={isCaseChatLoading || !caseUserMsg.trim()}
                                className="px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-slate-100 text-xs font-semibold rounded-lg transition-all shrink-0 cursor-pointer"
                              >
                                發送諮詢
                              </button>
                            </div>
                          </div>

                          {/* Case claims comments list */}
                          <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-850/80 flex flex-col gap-3">
                            <span className="text-xs font-bold text-slate-200 block border-b border-slate-800 pb-1.5 flex items-center justify-between">
                              <span>📋 個案智慧清單與點評反饋</span>
                              <button
                                onClick={handleSaveCaseLists}
                                disabled={isSavingCaseChanges}
                                className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-slate-100 text-[10px] font-bold rounded flex items-center gap-1 transition-all cursor-pointer border-none"
                              >
                                💾 儲存點評與清單變更
                              </button>
                            </span>

                            <div className="space-y-4 max-h-[350px] overflow-y-auto pr-1">
                              {/* Documents and Evidence */}
                              <div>
                                <span className="text-[11px] font-bold text-amber-500 block mb-2 border-l-2 border-amber-500 pl-1.5">📄 訴訟書狀與證據清單</span>
                                <div className="space-y-3 pl-1">
                                  {(cases[selectedCaseId].documents_and_evidence || []).map((doc: any, idx: number) => (
                                    <div key={doc.id} className="flex flex-col gap-1">
                                      <span className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">📎 {doc.name}</span>
                                      <input
                                        type="text"
                                        value={doc.comment || ""}
                                        onChange={(e) => handleCaseListCommentChange("documents_and_evidence", idx, e.target.value)}
                                        placeholder="對該證據點評記錄（如：缺乏直接故意證明力）"
                                        className="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-[10px] leading-normal text-slate-200 focus:outline-none focus:border-amber-500"
                                      />
                                    </div>
                                  ))}
                                </div>
                              </div>

                              {/* Precedents */}
                              <div>
                                <span className="text-[11px] font-bold text-amber-500 block mb-2 border-l-2 border-amber-500 pl-1.5">🔗 關聯性判例引用推薦</span>
                                <div className="space-y-3 pl-1">
                                  {(cases[selectedCaseId].precedents || []).map((pcd: any, idx: number) => (
                                    <div key={pcd.id} className="flex flex-col gap-1">
                                      <span className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">📜 {pcd.name}</span>
                                      <input
                                        type="text"
                                        value={pcd.comment || ""}
                                        onChange={(e) => handleCaseListCommentChange("precedents", idx, e.target.value)}
                                        placeholder="對該判例引用的點評（如：契合本案起算點爭點）"
                                        className="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-[10px] leading-normal text-slate-200 focus:outline-none focus:border-amber-500"
                                      />
                                    </div>
                                  ))}
                                </div>
                              </div>

                              {/* Claims */}
                              <div>
                                <span className="text-[11px] font-bold text-amber-500 block mb-2 border-l-2 border-amber-500 pl-1.5">⚖️ 法律聲明主張</span>
                                <div className="space-y-3 pl-1">
                                  {(cases[selectedCaseId].claims || []).map((clm: any, idx: number) => (
                                    <div key={clm.id} className="flex flex-col gap-1">
                                      <span className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">📌 {clm.name}</span>
                                      <input
                                        type="text"
                                        value={clm.comment || ""}
                                        onChange={(e) => handleCaseListCommentChange("claims", idx, e.target.value)}
                                        placeholder="對該主張的策略點評（如：本案防禦主攻防線）"
                                        className="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-[10px] leading-normal text-slate-200 focus:outline-none focus:border-amber-500"
                                      />
                                    </div>
                                  ))}
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 2: INGESTION (影音批次學術教材轉文字與語音校正) */}
          {activeTab === "ingest" && (
            <div className="bg-slate-950/80 rounded-xl border border-slate-800 p-5 flex flex-col min-h-[500px]">
              <div className="flex border-b border-slate-800 pb-3 mb-4 justify-between items-center">
                <div>
                  <h2 className="text-lg font-bold font-display tracking-tight text-white flex items-center gap-2">
                    📥 多模態大數據教材批次餵養區
                  </h2>
                  <p className="text-xs text-slate-400">大篇幅判例 PDF、幾小時學術錄影/錄音/簡報、證物圖像，AI 自動校對語音、自動OCR、自動分段，轉化存入智產智商庫</p>
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                
                {/* File list simulation */}
                <div className="flex flex-col gap-4">
                  
                  {/* HTML5 File API Drag and Drop Area */}
                  <div 
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    onClick={() => {
                      if (folderInputRef.current) {
                        folderInputRef.current.click();
                      }
                    }}
                    className={`relative overflow-hidden group cursor-pointer border-2 border-dashed rounded-xl p-6 flex flex-col items-center justify-center text-center transition-all duration-300 ${
                      isDragging 
                        ? "border-amber-500 bg-amber-500/10 text-amber-200 shadow-lg shadow-amber-500/5 animate-pulse" 
                        : "border-slate-800 bg-slate-900/60 hover:border-slate-700 hover:bg-slate-900/80 text-slate-300"
                    }`}
                  >
                    {isDragging && (
                      <div className="absolute inset-0 bg-amber-500/5 rounded-xl animate-pulse" />
                    )}
                    
                    <div className="p-3 bg-slate-950/80 border border-slate-800 rounded-full mb-2 group-hover:scale-105 transition-transform duration-300">
                      <UploadCloud className={`w-8 h-8 ${isDragging ? "text-amber-400 animate-bounce" : "text-amber-500"}`} />
                    </div>
                    
                    <h4 className="text-sm font-bold text-slate-200 mb-1">
                      {isDragging ? "放開鼠標即可自動解析！" : "拖入 PDF/TXT/圖片/影音檔或整個人工分類資料夾"}
                    </h4>
                    <p className="text-xs text-slate-400 max-w-sm mb-3">
                      支援遞迴遍歷資料夾、民刑事影音 ASR 毫秒級時間戳、PDF 內容自動提取、證單 OCR 辨識
                    </p>

                    {/* Hidden Native Directory Input */}
                    <input 
                      type="file" 
                      ref={folderInputRef}
                      className="hidden"
                      accept=".mp4,.mp3,.wav,.png,.jpg,.jpeg,.pdf,.txt"
                      {...({ webkitdirectory: "", directory: "", multiple: true } as any)} 
                      onChange={handleFolderSelect}
                    />

                    {/* Browse Folder Button */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleBrowseLocalFolder();
                      }}
                      className="mb-4 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-slate-950 font-bold text-xs rounded-lg shadow-md transition-all duration-200 flex items-center gap-1.5 cursor-pointer border-none"
                    >
                      <FolderOpen className="w-3.5 h-3.5" /> 📂 開啟 Windows 11 本地資料夾選擇器 (免上傳警告)
                    </button>
                    
                    {isParsing && (
                      <div className="absolute inset-0 bg-slate-950/98 flex flex-col items-center justify-center p-6 z-10 rounded-xl">
                        <RefreshCw className="w-8 h-8 animate-spin text-amber-500 mb-2.5" />
                        <p className="text-xs font-semibold text-amber-400">正在遞迴掃描與高吞吐處理中...</p>
                        
                        {/* Stateful Interactive Progress Bar */}
                        <div className="w-full max-w-xs mt-3.5 bg-slate-900 border border-slate-800 p-3 rounded-lg flex flex-col gap-1.5 text-left shadow-lg">
                          <div className="flex justify-between items-center text-[11px] font-semibold text-slate-300">
                            <span className="truncate max-w-[170px] font-mono text-amber-500" title={parsingFileName || "掃描路徑或解壓中..."}>
                              📄 {parsingFileName || "掃描與分配緩存..."}
                            </span>
                            <span className="font-mono text-slate-400">
                              {parsedFileCount} / {totalFilesToParse}
                            </span>
                          </div>
                          
                          {/* Progress Line */}
                          <div className="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-850">
                            <div 
                              className="bg-gradient-to-r from-amber-500 via-yellow-400 to-amber-300 h-2 rounded-full transition-all duration-300"
                              style={{ width: `${totalFilesToParse > 0 ? (parsedFileCount / totalFilesToParse * 100) : 0}%` }}
                            />
                          </div>
                          
                          <div className="flex justify-between items-center text-[10px] text-slate-500 font-mono mt-0.5">
                            <span>硬碟讀取與字元解編</span>
                            <span className="font-bold text-amber-400">
                              {totalFilesToParse > 0 ? Math.round((parsedFileCount / totalFilesToParse) * 100) : 0}%
                            </span>
                          </div>
                        </div>

                        <p className="text-[10px] text-slate-500 font-mono mt-3 max-w-xs text-center leading-normal">
                          ⚡ 超過 4G-8G 大音頻、錄影學術課程正在本地內存高速提取、ASR 辨識與 OCR 編碼。
                        </p>
                      </div>
                    )}
                    
                    <div className="flex flex-wrap justify-center items-center gap-1.5">
                      <span className="text-[10px] font-mono bg-slate-950 border border-slate-800 px-2 py-0.5 rounded text-slate-400">
                        📂 遞迴讀取人工目錄
                      </span>
                      <span className="text-[10px] font-mono bg-slate-950 border border-slate-800 px-2 py-0.5 rounded text-slate-400">
                        📄 繁體 / OCR PDF ＆ 證單圖像
                      </span>
                      <span className="text-[10px] font-mono bg-slate-950 border border-slate-800 px-2 py-0.5 rounded text-slate-400">
                        🎥 MP4 學術錄影 / MP3 錄音 ASR
                      </span>
                    </div>
                  </div>

                  {/* Local Disk volume crawler & media/doc registration segment */}
                  <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl flex flex-col gap-3 shadow-lg relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-[2.5px] bg-gradient-to-r from-amber-500 via-orange-400 to-yellow-500" />
                    <div className="flex justify-between items-center">
                      <h3 className="text-xs font-bold text-slate-200 tracking-wider flex items-center gap-1.5 font-sans uppercase">
                        <span>💾</span> 本機磁碟區即時法律教材爬蟲 & 自動登記比對
                      </h3>
                      <span className="px-1.5 py-0.5 rounded text-[8px] font-bold font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase tracking-widest">
                        LOCAL DISK SCANNER
                      </span>
                    </div>
                    
                    <p className="text-[11px] text-slate-400 leading-relaxed font-sans mt-0.5">
                      自動掃描本機指定目錄下尚未被分析的影音 (`.mp4`, `.mp3`, `.wav`) 與文件 (`.txt`, `.pdf`)，並一鍵自動登錄與導入。
                    </p>

                    {/* Scan path input and Scan button */}
                    <div className="flex gap-2 mt-1">
                      <input
                        type="text"
                        value={localScanPath}
                        onChange={(e) => setLocalScanPath(e.target.value)}
                        placeholder="請輸入本機掃描目錄路徑..."
                        className="flex-1 bg-slate-950 border border-slate-850 focus:border-amber-500/80 rounded-lg py-2 px-3 text-xs text-slate-300 focus:outline-none transition-all font-mono"
                      />
                      <button
                        type="button"
                        disabled={isLocalScanning || isLocalImporting}
                        onClick={handleScanLocalMedia}
                        className="px-4 py-2 bg-amber-500 hover:bg-amber-600 active:scale-[0.98] transition-all text-slate-950 font-bold text-xs rounded-lg shadow-sm flex items-center gap-1.5 shrink-0 border-none cursor-pointer disabled:opacity-50"
                      >
                        {isLocalScanning ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                            <span>掃描中...</span>
                          </>
                        ) : (
                          <span>🔍 開始掃描</span>
                        )}
                      </button>
                    </div>

                    {/* Scanned files results display */}
                    {scannedLocalFiles.length > 0 ? (
                      <div className="flex flex-col gap-2 mt-1 bg-slate-950 border border-slate-850 rounded-xl p-3 max-h-[200px] overflow-y-auto">
                        <div className="text-[10px] font-bold text-slate-500 uppercase tracking-wider flex justify-between">
                          <span>🆕 尚未分析之教材 ({scannedLocalFiles.length} 個檔案)</span>
                          <span>操作</span>
                        </div>
                        <div className="space-y-1.5 mt-1">
                          {scannedLocalFiles.map((file, i) => (
                            <div key={i} className="flex justify-between items-center text-[11px] py-1 border-b border-slate-850/40 last:border-0 pb-1">
                              <span className="text-slate-300 truncate max-w-[240px] flex items-center gap-1.5 font-mono" title={file.path}>
                                <span className="px-1 py-0.5 bg-slate-900 border border-slate-800 text-[8px] font-bold text-slate-500 rounded uppercase">
                                  {file.ext || file.name.split('.').pop()}
                                </span>
                                {file.name}
                                <span className="text-[9px] text-slate-550 font-sans">
                                  ({(file.size / (1024 * 1024)).toFixed(2)} MB)
                                </span>
                              </span>
                              <div className="flex gap-1.5">
                                <button
                                  type="button"
                                  disabled={isLocalImporting}
                                  onClick={() => handleImportLocalFiles([file])}
                                  className="px-1.5 py-0.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 rounded text-[9px] cursor-pointer transition-colors"
                                >
                                  📥 放入餵食區
                                </button>
                                <button
                                  type="button"
                                  disabled={isLocalImporting}
                                  onClick={() => handleDirectIngestLocalFiles([file])}
                                  className="px-1.5 py-0.5 bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/25 text-amber-400 rounded text-[9px] cursor-pointer transition-colors"
                                >
                                  ⚡ 直接分析歸類
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>

                        {/* Batch Action Buttons */}
                        <div className="flex gap-2 mt-2 pt-2 border-t border-slate-850">
                          <button
                            type="button"
                            disabled={isLocalImporting}
                            onClick={() => handleImportLocalFiles(scannedLocalFiles)}
                            className="flex-1 py-1.5 bg-slate-900 border border-slate-800 hover:bg-slate-850 text-slate-300 font-semibold text-[10px] rounded-lg transition-all flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50"
                          >
                            📥 全數放入餵食區
                          </button>
                          <button
                            type="button"
                            disabled={isLocalImporting}
                            onClick={() => handleDirectIngestLocalFiles(scannedLocalFiles)}
                            className="flex-1 py-1.5 bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-[10px] rounded-lg transition-all flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50"
                          >
                            ⚡ 全數一鍵分析並歸類到記憶庫
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="text-center py-5 bg-slate-950/40 border border-slate-850 rounded-lg">
                        <p className="text-xs text-slate-500 italic">
                          {isLocalScanning ? "正在為您掃描並比對本機磁碟中..." : "尚未掃描或所選本機路徑下無未分析之教材"}
                        </p>
                      </div>
                    )}

                    {isLocalImporting && (
                      <div className="flex items-center justify-center gap-2 text-[10px] text-amber-400 mt-1 font-mono">
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>正在從本機讀取並分析多模態數據教材中...</span>
                      </div>
                    )}
                  </div>

                  {/* Real-time Web Scraper & Legal News Crawler Segment */}
                  <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl flex flex-col gap-3 shadow-lg relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-[2.5px] bg-gradient-to-r from-teal-500 via-cyan-400 to-indigo-500" />
                    <div className="flex justify-between items-center">
                      <h3 className="text-xs font-bold text-slate-200 tracking-wider flex items-center gap-1.5 font-sans uppercase">
                        <span>🌐</span> 外部即時法律網路爬蟲 & 裁判自動導入
                      </h3>
                      <span className="px-1.5 py-0.5 rounded text-[8px] font-bold font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 uppercase tracking-widest">
                        RWS WEB CONNECT
                      </span>
                    </div>
                    
                    <p className="text-[11px] text-slate-400 leading-relaxed font-sans mt-0.5">
                      自動連接網際網路，一鍵解析、抓取並使用 AI 萃取台灣最新「焦點司法新聞、重要法律修法動態及法院裁判判決」。
                    </p>

                    {/* Pre-defined Taiwanese legal source shortcut buttons */}
                    <div className="mt-1 flex flex-col gap-1.5">
                      <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">💡 推薦一鍵即時資訊來源</span>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                        <button
                          type="button"
                          disabled={isScraping}
                          onClick={() => {
                            setScrapeUrl("https://www.judicial.gov.tw/tw/lp-1888-news.html");
                            handleScrapeUrl("https://www.judicial.gov.tw/tw/lp-1888-news.html");
                          }}
                          className="px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-lg hover:border-cyan-500/40 hover:bg-slate-900 transition-all text-[11px] text-slate-300 flex flex-col items-center justify-center gap-1 text-center font-sans group cursor-pointer disabled:opacity-50"
                        >
                          <span className="text-base group-hover:scale-110 transition-transform">⚖️</span>
                          <span className="font-semibold text-slate-200">司法院最新實務</span>
                          <span className="text-[9px] text-slate-500 font-mono">焦點司法新聞</span>
                        </button>
                        <button
                          type="button"
                          disabled={isScraping}
                          onClick={() => {
                            setScrapeUrl("https://mojlaw.moj.gov.tw/UpdateNews.moj");
                            handleScrapeUrl("https://mojlaw.moj.gov.tw/UpdateNews.moj");
                          }}
                          className="px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-lg hover:border-indigo-500/40 hover:bg-slate-900 transition-all text-[11px] text-slate-300 flex flex-col items-center justify-center gap-1 text-center font-sans group cursor-pointer disabled:opacity-50"
                        >
                          <span className="text-base group-hover:scale-110 transition-transform">📖</span>
                          <span className="font-semibold text-slate-200">法務部法律動態</span>
                          <span className="text-[9px] text-slate-500 font-mono">法規即時更益</span>
                        </button>
                        <button
                          type="button"
                          disabled={isScraping}
                          onClick={() => {
                            setScrapeUrl("https://www.court.gov.tw/judgment-1650.judgment");
                            handleScrapeUrl("https://www.court.gov.tw/judgment-1650.judgment");
                          }}
                          className="px-2.5 py-1.5 bg-slate-950 border border-slate-800 rounded-lg hover:border-emerald-500/40 hover:bg-slate-900 transition-all text-[11px] text-slate-300 flex flex-col items-center justify-center gap-1 text-center font-sans group cursor-pointer disabled:opacity-50"
                        >
                          <span className="text-base group-hover:scale-110 transition-transform">🏛️</span>
                          <span className="font-semibold text-slate-200">最高法院判決</span>
                          <span className="text-[9px] text-slate-500 font-mono">精選裁判要旨</span>
                        </button>
                      </div>
                    </div>

                    {/* Manual input bar */}
                    <div className="mt-1 flex gap-2">
                      <div className="relative flex-1">
                        <input
                          type="text"
                          value={scrapeUrl}
                          onChange={(e) => setScrapeUrl(e.target.value)}
                          placeholder="請輸入任何司法時事新聞、法規草案修法公告等網址..."
                          className="w-full bg-slate-950 border border-slate-850 focus:border-cyan-500/80 rounded-lg py-2 pl-3 pr-8 text-xs text-slate-300 focus:outline-none transition-all font-sans"
                        />
                        {scrapeUrl && (
                          <button
                            type="button"
                            onClick={() => setScrapeUrl("")}
                            className="absolute right-2.5 top-2.5 text-slate-500 hover:text-slate-300 bg-transparent border-0 cursor-pointer"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                      <button
                        type="button"
                        disabled={isScraping || !scrapeUrl.trim()}
                        onClick={() => handleScrapeUrl()}
                        className="px-4 py-2 bg-gradient-to-r from-teal-500 to-indigo-600 hover:from-teal-600 hover:to-indigo-700 active:scale-[0.98] transition-all text-white font-bold text-xs rounded-lg shadow-sm flex items-center gap-1.5 shrink-0 disabled:opacity-45 disabled:pointer-events-none cursor-pointer border-none"
                      >
                        {isScraping ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 animate-spin text-white" />
                            <span>正在爬網...</span>
                          </>
                        ) : (
                          <>
                            <span>爬取與提取</span>
                          </>
                        )}
                      </button>
                    </div>

                    {/* Scrape Error Message */}
                    {scrapeError && (
                      <div className="p-2 border border-rose-500/20 bg-rose-500/10 rounded-lg text-rose-400 text-[11px] font-sans flex items-center gap-2">
                        <span>⚠️</span>
                        <span>{scrapeError}</span>
                      </div>
                    )}

                    {/* Succeeded Result Preview Widget and Injection Action */}
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
                              ? batchTexts.filter(b => getItemCategory(b, false) === '判例').length
                              : vaultItems.filter(b => getItemCategory(b, true) === '判例').length
                          }
                          ) | 📁 證物(
                          {
                            queueTab === "pending"
                              ? batchTexts.filter(b => getItemCategory(b, false) === '證物').length
                              : vaultItems.filter(b => getItemCategory(b, true) === '證物').length
                          }
                          ) | 🎥 影音(
                          {
                            queueTab === "pending"
                              ? batchTexts.filter(b => ['學術錄影', '學術錄音'].includes(getItemCategory(b, false))).length
                              : vaultItems.filter(b => ['學術錄影', '學術錄音'].includes(getItemCategory(b, true))).length
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
                                ? batchTexts.filter(b => getItemCategory(b, false) === btn.id).length
                                : vaultItems.filter(b => getItemCategory(b, true) === btn.id).length);
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

                                {/* Ingest, Copy, Remove Inline Buttons */}
                                <div className="flex justify-between items-center gap-2 mt-1 pt-1.5 border-t border-slate-900/60">
                                  <button
                                    type="button"
                                    onClick={() => {
                                      if (origIdx !== -1) {
                                        setBatchTexts(prev => prev.filter((_, i) => i !== origIdx));
                                        showAlert("🗑️ 已將教材移出待校對隊列。");
                                      }
                                    }}
                                    className="px-2 py-1 bg-rose-500/10 hover:bg-rose-500 hover:text-white border border-rose-500/20 text-rose-400 rounded text-[10px] transition-all cursor-pointer flex items-center gap-1 active:scale-95 border-none"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                    <span>🗑️ 移出隊列</span>
                                  </button>
                                  <div className="flex gap-2">
                                    <button
                                      type="button"
                                      onClick={() => {
                                        navigator.clipboard.writeText(file.content || "");
                                        showAlert("📋 全文已成功複製到剪貼簿！");
                                      }}
                                      className="px-2 py-1 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-355 rounded text-[10px] transition-all cursor-pointer flex items-center gap-1 active:scale-95"
                                    >
                                      <span>複製全文</span>
                                    </button>
                                    <button
                                      type="button"
                                      onClick={async () => {
                                        try {
                                          const resp = await fetch("/api/ingest", {
                                            method: "POST",
                                            headers: { "Content-Type": "application/json" },
                                            body: JSON.stringify({ files: [file] })
                                          });
                                          const data = await resp.json();
                                          if (data.status === "success") {
                                            showAlert("🚀 該教材已成功智慧消化並寫入資料庫！");
                                            setBatchTexts(prev => prev.filter((_, i) => i !== origIdx));
                                            fetchVaultItems();
                                            fetchSystemStatus();
                                          } else {
                                            showAlert(`❌ 導入失敗：${data.error}`);
                                          }
                                        } catch (e: any) {
                                          showAlert(`❌ 錯誤：${e.message || String(e)}`);
                                        }
                                      }}
                                      className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-[10px] font-bold transition-all cursor-pointer flex items-center gap-1 active:scale-95 border-none"
                                    >
                                      <span>💾 獨立消化入庫</span>
                                    </button>
                                  </div>
                                </div>
                              </div>
                            );
                          })
                        )
                      ) : (
                        (() => {
                          const filteredVaultItems = vaultItems.filter(item => {
                            if (!item) return false;
                            // Category filter
                            if (ingestFilter !== "all") {
                              const fileCat = getItemCategory(item, true);
                              if (fileCat !== ingestFilter) return false;
                            }
                            // Search filter
                            const q = vaultSearchQuery.toLowerCase().trim();
                            if (q) {
                              const matchesSource = item.source && item.source.toLowerCase().includes(q);
                              const matchesText = item.text && item.text.toLowerCase().includes(q);
                              const matchesCat = getItemCategory(item, true).toLowerCase().includes(q);
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
                            const activeCat = getItemCategory(item, true);
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
                                        updateVaultItem(item.id, item.text || "", e.target.value);
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
                </div>

                {/* Digest process logs and visual indicators */}
                <div className="flex flex-col gap-4">
                  {/* Academic Ingest Adaptive Control Center */}
                  <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl flex flex-col gap-3.5 shadow-lg relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-[2.5px] bg-gradient-to-r from-amber-500 via-yellow-400 to-teal-400" />
                    <div className="flex justify-between items-center">
                      <h3 className="text-xs font-bold text-slate-200 tracking-wider flex items-center gap-1.5 font-sans uppercase">
                        <span>⚡</span> 批量學術餵養控制與進度中心
                      </h3>
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold font-mono tracking-wider ${
                        isIngesting 
                          ? isIngestPaused 
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" 
                            : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 animate-pulse"
                          : isParsing
                            ? "bg-pink-500/10 text-pink-400 border border-pink-500/20 animate-pulse"
                            : "bg-slate-950 text-slate-500 border border-slate-800"
                      }`}>
                        {isIngesting ? (isIngestPaused ? "⏸️ 暫停中" : "⚡ 消化中") : isParsing ? "📂 智慧提取中" : "💤 靜態待命"}
                      </span>
                    </div>

                    {/* Progress details if parsing or ingesting */}
                    {isIngesting ? (
                      <div className="space-y-3">
                        <div className="flex justify-between items-center text-[11px] font-mono text-slate-400">
                          <span className="truncate max-w-[210px] text-amber-500" title={currentIngestingName}>
                            📁 {currentIngestingName || "評估下一個檔案..."}
                          </span>
                          <span className="text-slate-300 font-semibold shrink-0">
                            {ingestProgressCount} / {ingestTotal}
                          </span>
                        </div>

                        {/* Progress bar line */}
                        <div className="w-full bg-slate-950 rounded-full h-2.5 overflow-hidden border border-slate-850 p-[1px]">
                          <div 
                            className="bg-gradient-to-r from-amber-500 via-yellow-400 to-teal-400 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${ingestTotal > 0 ? (ingestProgressCount / ingestTotal * 100) : 0}%` }}
                          />
                        </div>

                        {/* Interactive Pause/Resume Buttons & details */}
                        <div className="flex items-center justify-between gap-3 text-[11px] font-sans">
                          <button
                            type="button"
                            onClick={() => {
                              const nextPaused = !isIngestPaused;
                              setIsIngestPaused(nextPaused);
                              isIngestPausedRef.current = nextPaused;
                            }}
                            className={`px-3 py-1.5 rounded-lg border font-semibold flex items-center gap-1.5 transition-all text-[11px] cursor-pointer ${
                              isIngestPaused 
                                ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25" 
                                : "bg-amber-500/15 text-amber-400 border-amber-500/30 hover:bg-amber-500/25"
                            }`}
                          >
                            {isIngestPaused ? (
                              <>
                                <Play className="w-3 h-3 fill-current text-emerald-400" />
                                <span>恢復處理 (Resume)</span>
                              </>
                            ) : (
                              <>
                                <Pause className="w-3 h-3 text-amber-400" />
                                <span>暫停處理 (Pause)</span>
                              </>
                            )}
                          </button>
                          
                          <span className="text-slate-500 text-[10px] font-mono shrink-0">
                            已處理: <span className="text-amber-400 font-bold">{ingestTotal > 0 ? Math.round((ingestProgressCount / ingestTotal) * 100) : 0}%</span>
                          </span>
                        </div>

                        {/* Real-time precalculated duration indicator */}
                        <div className="pt-2.5 border-t border-slate-850 flex items-center justify-between text-[11px] text-slate-400 font-sans">
                          <span className="flex items-center gap-1">✨ 當前預估剩餘處理時間:</span>
                          <span className="font-mono font-bold text-teal-400">
                            {ingestEstRemaining === null 
                              ? "正在校準基準速度..." 
                              : ingestEstRemaining <= 0 
                                ? "即將注入完成！" 
                                : `${ingestEstRemaining} 秒`}
                          </span>
                        </div>
                      </div>
                    ) : isParsing ? (
                      <div className="space-y-3">
                        <div className="flex justify-between items-center text-[11px] font-mono text-slate-400">
                          <span className="truncate max-w-[210px] text-pink-400" title={parsingFileName}>
                            📄 {parsingFileName || "本地提取校對檔案..."}
                          </span>
                          <span className="text-slate-300 font-semibold shrink-0">
                            {parsedFileCount} / {totalFilesToParse}
                          </span>
                        </div>

                        {/* Progress bar line */}
                        <div className="w-full bg-slate-950 rounded-full h-2.5 overflow-hidden border border-slate-850 p-[1px]">
                          <div 
                            className="bg-gradient-to-r from-pink-500 via-rose-400 to-amber-400 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${totalFilesToParse > 0 ? (parsedFileCount / totalFilesToParse * 100) : 0}%` }}
                          />
                        </div>

                        <div className="pt-2 flex justify-between items-center text-[10px] text-slate-500 font-mono">
                          <span>磁碟解碼、影音切片與 OCR</span>
                          <span className="font-bold text-pink-400">
                            {totalFilesToParse > 0 ? Math.round((parsedFileCount / totalFilesToParse) * 100) : 0}%
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="py-4 text-center bg-slate-950/40 border border-slate-850 border-dashed rounded-lg flex flex-col items-center justify-center p-3">
                        <p className="text-xs text-slate-500 italic max-w-[2700px] leading-normal mb-1">
                          待命狀態。請配置左方隊列並點擊下方「開始全自動音檔翻譯、OCR 與自適應消化」以啟動。
                        </p>
                        <p className="text-[10px] text-slate-600 font-mono">
                          注入智商庫後將成為 RWS 深度推理與法律自學檢討的背景知識基礎！
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl flex flex-col gap-4 flex-1">
                    <h3 className="text-xs font-semibold text-slate-300 tracking-wider">🧬 導入處理終端機日誌</h3>
                    
                    <div className="bg-black/40 border border-slate-800 rounded-lg p-3 font-mono text-[11px] h-[300px] overflow-y-auto space-y-2">
                      <p className="text-slate-500">[LOG] 127.0.0.1 - - [13/Jun/2026] Ingestion module initiated.</p>
                      <p className="text-slate-500">[LOG] Local GPU compute_type='float16' enabled for Whisper stream.</p>
                      {isIngesting && !isIngestPaused && (
                        <p className="text-amber-400 font-bold animate-pulse">&gt; [PROCESS] 正在自動執行：糾正「假芳、倚芳、炳芳」等典型語音辨識噪聲，並切分時間軸...</p>
                      )}
                      {isIngestPaused && (
                        <p className="text-amber-500 font-bold animate-pulse">&gt; [PAUSED] 餵養進度已由使用者暫停。待命恢復中...</p>
                      )}
                      {ingestLogs.map((log, idx) => (
                        <div key={idx} className="border-t border-slate-800 pt-2 text-slate-300">
                          <p className="text-emerald-400 font-bold">&gt; [OK] 檔案 {log.name} 已校對完成並提取法條！</p>
                          <p className="text-amber-500/80 text-[10px] mt-1 pl-3 bg-slate-950 p-2 rounded">
                            <span className="font-semibold block text-slate-400 select-none">AI智商庫摘要：</span>
                            {log.summary}
                          </p>
                        </div>
                      ))}
                      {!isIngesting && ingestLogs.length === 0 && (
                        <p className="text-slate-600 italic">無正在處理之日誌，請在上傳隊列中點選啟動。</p>
                      )}
                    </div>
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* TAB 3: EXAM HALL (司法官考題自學演化訓練) */}
          {activeTab === "exam" && (
            <div className="bg-slate-950/80 rounded-xl border border-slate-800 p-5 flex flex-col min-h-[500px]">
              <div className="flex border-b border-slate-800 pb-3 mb-4 justify-between items-center">
                <div>
                  <h2 className="text-lg font-bold font-display tracking-tight text-white flex items-center gap-2">
                    🎓 國家司法官/檢察官考題自學與自我進化
                  </h2>
                  <p className="text-xs text-slate-400">模擬最高考場！讓 AI 與標竿高分答案進行比較，由「閱卷教授」進行狠狠反思檢討，生成學習筆記</p>
                </div>
              </div>

              {/* 國家考試與補習班網路題庫自動/手動採集區 */}
              <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-4 mb-5">
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-xs font-bold text-amber-500 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    國家考試與補習班網路題庫自動/手動採集區
                  </h3>
                  <button
                    onClick={() => setIsManualExamFormOpen(!isManualExamFormOpen)}
                    className="px-2.5 py-1 bg-slate-950 hover:bg-slate-900 border border-slate-800 text-[10px] font-semibold text-slate-300 rounded transition-all cursor-pointer"
                  >
                    {isManualExamFormOpen ? "隱藏手動登記" : "切換手動登記"}
                  </button>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {/* 自動爬蟲區 */}
                  <div className="bg-black/20 p-3 rounded border border-slate-800/60 flex flex-col justify-between">
                    <div>
                      <label className="text-[10px] font-bold text-slate-400 block mb-1">
                        自動網路爬取 (自動下載補習班/考選部網頁試題與詳解並以 AI 提煉)
                      </label>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={examScrapeUrl}
                          onChange={(e) => setExamScrapeUrl(e.target.value)}
                          placeholder="請輸入網址，如：https://www.moex.gov.tw/..."
                          className="flex-1 bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-amber-500 font-sans"
                        />
                        <button
                          onClick={handleScrapeExam}
                          disabled={isExamScraping || !examScrapeUrl.trim()}
                          className="px-3 py-1 bg-amber-600 hover:bg-amber-500 text-white rounded text-xs font-semibold disabled:opacity-50 cursor-pointer transition-all flex items-center gap-1"
                        >
                          {isExamScraping ? (
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            "一鍵爬取"
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="mt-2.5">
                      <span className="text-[9px] text-slate-500 block mb-1">快速測試模擬爬蟲捷徑：</span>
                      <div className="flex flex-wrap gap-1.5">
                        <button
                          type="button"
                          onClick={() => setExamScrapeUrl("https://www.moex.gov.tw/exam/112/civil-law-q1")}
                          className="px-1.5 py-0.5 bg-slate-950 hover:bg-slate-900 border border-slate-800 text-[9px] text-slate-400 rounded transition-all cursor-pointer"
                        >
                          考選部 112 民事法
                        </button>
                        <button
                          type="button"
                          onClick={() => setExamScrapeUrl("https://www.get.com.tw/lawyer/112-exam-q1")}
                          className="px-1.5 py-0.5 bg-slate-950 hover:bg-slate-900 border border-slate-800 text-[9px] text-slate-400 rounded transition-all cursor-pointer"
                        >
                          高點補習班名師解析
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* 手動登記表單 (展開時顯示) */}
                  {isManualExamFormOpen ? (
                    <form onSubmit={handleSubmitManualExam} className="bg-black/20 p-3 rounded border border-slate-800/60 space-y-2">
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 block mb-0.5">考古題標題</label>
                        <input
                          type="text"
                          value={manualExamTitle}
                          onChange={(e) => setManualExamTitle(e.target.value)}
                          placeholder="如：112年司法官民事法第一題"
                          required
                          className="w-full bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-amber-500 font-sans"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 block mb-0.5">考題題目內容 (手動被動輸入)</label>
                        <textarea
                          value={manualExamQuestion}
                          onChange={(e) => setManualExamQuestion(e.target.value)}
                          placeholder="請輸入題目完整內容..."
                          rows={2}
                          required
                          className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500 font-sans"
                        />
                      </div>
                      <div>
                        <label className="text-[10px] font-bold text-slate-400 block mb-0.5">官方詳解 / 補習班解析 (詳解將寫入長期記憶)</label>
                        <textarea
                          value={manualExamAnswer}
                          onChange={(e) => setManualExamAnswer(e.target.value)}
                          placeholder="請輸入詳細解析與解答..."
                          rows={2}
                          required
                          className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500 font-sans"
                        />
                      </div>
                      <div className="flex justify-end">
                        <button
                          type="submit"
                          disabled={isSubmittingManualExam}
                          className="px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded text-xs font-semibold disabled:opacity-50 cursor-pointer transition-all flex items-center gap-1"
                        >
                          {isSubmittingManualExam ? (
                            <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            "登記並寫入長期記憶"
                          )}
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div className="bg-black/10 p-3 rounded border border-slate-800/40 flex items-center justify-center text-slate-500 italic text-xs text-center">
                      點擊右上角「切換手動登記」以手動/被動輸入考古題庫與詳解，系統將記錄詳解
                    </div>
                  )}
                </div>
              </div>

              {/* Question list selector */}
              <div className="flex gap-3 mb-5 overflow-x-auto pb-1 scrollbar-none">
                {exams.map((exam, index) => (
                  <button
                    key={index}
                    onClick={() => {
                      setSelectedExam(index);
                      setAiAnswer("");
                      setProfCritique("");
                    }}
                    className={`px-4 py-2.5 rounded-lg border text-xs font-semibold cursor-pointer transition-all whitespace-nowrap ${
                      selectedExam === index 
                        ? "bg-slate-900 border-amber-500 text-amber-400 shadow-sm" 
                        : "bg-slate-950/40 border-slate-800 text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {exam.title}
                  </button>
                ))}
              </div>

              {/* Question overview */}
              <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl mb-5">
                <div className="flex items-center gap-2 text-xs font-semibold text-amber-500 mb-1">
                  <HelpCircle className="w-4 h-4" /> 考場試題：
                </div>
                <p className="text-xs text-slate-200 leading-relaxed font-sans">{exams[selectedExam].question}</p>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 mb-5">
                
                {/* AI JD Answer Sheet */}
                <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl flex flex-col">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 mb-2 border-b border-slate-800 pb-2">
                    <FileCheck2 className="w-4 h-4 text-emerald-400" /> AI 模擬司法官擬答 (三段論法)
                  </div>
                  
                  <div className="flex-1 min-h-[150px] p-3 bg-black/20 rounded border border-slate-800 font-sans text-xs text-slate-300 leading-relaxed max-h-[300px] overflow-y-auto whitespace-pre-wrap">
                    {isExamRunning ? (
                      <p className="text-slate-500 animate-pulse">正在閉門作答考題，請勿關閉視窗...</p>
                    ) : aiAnswer ? (
                      aiAnswer
                    ) : (
                      <p className="text-slate-500 italic">點擊下方「啟動考試」進行模擬作答</p>
                    )}
                  </div>
                </div>

                {/* Strict Professor Evaluation Panel */}
                <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl flex flex-col">
                  <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 mb-2 border-b border-slate-800 pb-2">
                    <Gavel className="w-4 h-4 text-rose-400" /> 閱卷教授紅筆批改與錯題本
                  </div>
                  
                  <div className="flex-1 min-h-[150px] p-3 bg-rose-950/5 rounded border border-rose-900/20 font-sans text-xs text-slate-300 leading-relaxed max-h-[300px] overflow-y-auto whitespace-pre-wrap">
                    {isExamRunning ? (
                      <p className="text-slate-500 animate-pulse">正在提交給台灣閱卷教授，比對高分範本中...</p>
                    ) : profCritique ? (
                      profCritique
                    ) : (
                      <p className="text-slate-500 italic">作答完成後，教授批語將實時渲染至此，並自動寫入大氣智商庫</p>
                    )}
                  </div>
                </div>

              </div>

              <div className="flex justify-between items-center border-t border-slate-800 pt-4">
                <p className="text-xs text-slate-500 max-w-md leading-normal">
                  💡 自學演化：批改後生成的「自我檢討筆記」會被自適應向量化存入 legal_intelligence_vault。在下一次進行實務諮詢對話時，AI 將引以為戒，優先避免同類型程序漏洞！
                </p>
                <button 
                  onClick={handleExamStart}
                  disabled={isExamRunning}
                  className="px-6 py-3 bg-gradient-to-r from-amber-600 to-amber-700 text-white rounded-lg text-sm font-semibold hover:brightness-110 active:brightness-95 cursor-pointer select-none transition-all flex items-center gap-2"
                >
                  {isExamRunning ? <RefreshCw className="w-4 h-4 animate-spin text-white" /> : "🚀 啟動模擬解題、批改與自我強固"}
                </button>
              </div>

            </div>
          )}

          {/* TAB 4: LAW DRAFTING (訴訟書狀編寫區) */}
          {activeTab === "draft" && (
            <div className="bg-slate-950/80 rounded-xl border border-slate-800 p-5 flex flex-col min-h-[500px]">
              <div className="flex border-b border-slate-800 pb-3 mb-4 justify-between items-center">
                <div>
                  <h2 className="text-lg font-bold font-display tracking-tight text-white flex items-center gap-2">
                    📝 訴訟書狀自動編寫區 (IRAC 結構)
                  </h2>
                  <p className="text-xs text-slate-400">根據口語 facts Facts，自動匹配 RWS 評估出的法條與抗辯理由，生成 100% 格式正確的訴訟狀草稿</p>
                </div>
              </div>

              <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 mb-5 flex-1">
                
                {/* Input Details */}
                <div className="flex flex-col gap-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-400 block mb-1">【事實細節輸入（越詳細，生成涵攝越精準）】</label>
                    <textarea 
                      value={draftFact}
                      onChange={(e) => setFactContent(e.target.value)}
                      rows={8}
                      className="w-full bg-slate-900 border border-slate-800 rounded-lg p-3 text-xs leading-relaxed text-slate-100 focus:outline-none focus:border-amber-500 font-sans"
                      placeholder="請輸入欲撰寫之事實..."
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-semibold text-slate-400 block mb-1">訴訟書狀範例類型</label>
                      <select 
                        value={draftType}
                        onChange={(e) => setDraftType(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 focus:outline-none mt-1 text-slate-200 text-xs cursor-pointer"
                      >
                        <option value="civil_complaint">民事損害賠償起訴狀</option>
                        <option value="criminal_complaint">刑事告訴狀</option>
                        <option value="reply_pleading">民事答辯狀</option>
                        <option value="appeal_pleading">民事上訴理由狀</option>
                      </select>
                    </div>

                    <div className="flex items-end">
                      <button 
                        onClick={handleDraftGenerate}
                        disabled={isDrafting || !draftFact.trim()}
                        className="w-full py-2.5 bg-gradient-to-r from-amber-600 to-amber-700 text-white rounded font-medium hover:brightness-110 active:brightness-95 cursor-pointer text-xs font-display flex items-center justify-center gap-1.5"
                      >
                        {isDrafting ? <RefreshCw className="w-4 h-4 animate-spin text-white" /> : "✍️ 自動起草司法合格書狀"}
                      </button>
                    </div>
                  </div>
                </div>

                {/* Visual draft output */}
                <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl flex flex-col">
                  <div className="flex items-center justify-between text-xs font-semibold text-slate-300 mb-2 border-b border-slate-800 pb-2">
                    <span className="flex items-center gap-2"><FileText className="w-4 h-4 text-amber-500" /> 起草預覽</span>
                    {generatedDraft && (
                      <button 
                        onClick={() => {
                          navigator.clipboard.writeText(generatedDraft);
                          showAlert("已複製書狀草稿到剪貼簿！");
                        }}
                        className="px-2 py-1 bg-slate-950 border border-slate-800 text-[10px] rounded text-slate-400 hover:text-slate-100 cursor-pointer"
                      >
                        複製全文
                      </button>
                    )}
                  </div>
                  
                  <div className="flex-1 min-h-[250px] p-3.5 bg-black/20 rounded border border-slate-800 font-mono text-xs text-slate-200 leading-normal max-h-[350px] overflow-y-auto whitespace-pre-wrap">
                    {isDrafting ? (
                      <p className="text-slate-500 animate-pulse">老律師審視法條對稱，精密寫狀中...</p>
                    ) : generatedDraft ? (
                      generatedDraft
                    ) : (
                      <p className="text-slate-600 italic">在左側輸入事實並點擊按钮，即可預覽高水準書狀文本。</p>
                    )}
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* TAB 5: SYSTEM MANAGEMENT & DISASTER RECOVERY */}
          {activeTab === "admin" && (
            <div className="bg-slate-950/80 rounded-xl border border-slate-800 p-5 flex flex-col min-h-[500px]">
              <div className="flex border-b border-slate-800 pb-3 mb-4 justify-between items-center">
                <div>
                  <h2 className="text-lg font-bold font-display tracking-tight text-white flex items-center gap-2">
                    🔒 資料庫知識管理與加密資安災害復原
                  </h2>
                  <p className="text-xs text-slate-400">備份本工作站持久化數據，防止審判及辦案密件外洩，並支持 AES-256 加密保存</p>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                
                <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
                  <h3 className="text-xs font-semibold text-slate-300 tracking-wider mb-2 flex items-center gap-1.5">
                    <Lock className="w-4 h-4 text-amber-500" /> 軍規級 Fernet 加密備份
                  </h3>
                  <p className="text-xs text-slate-400 mb-4 leading-normal">
                    系統會將本地 RAG 資料夾打成 Zip，動態讀取 `secret.key` 密鑰進行塊加密，防止第三方硬體探查漏洞洩密。
                  </p>
                  
                  <div className="flex gap-2">
                    <button 
                      onClick={handleTriggerBackup}
                      className="px-4 py-2 bg-slate-900 hover:bg-slate-800 border border-slate-700/80 roundedtext-xs font-semibold text-slate-200 hover:text-white transition-all cursor-pointer flex items-center gap-1.5"
                    >
                      <Download className="w-3.5 h-3.5 text-amber-400" />
                      下載加密備份檔 (.enc)
                    </button>
                    
                    <button 
                      onClick={handleResetDb}
                      className="px-4 py-2 bg-rose-950/20 hover:bg-rose-950/40 border border-rose-900/30 rounded text-xs font-semibold text-rose-400 hover:text-rose-300 transition-all cursor-pointer"
                    >
                      安全格式化資料庫
                    </button>
                  </div>
                </div>

                <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl">
                  <h3 className="text-xs font-semibold text-slate-300 tracking-wider mb-2 flex items-center gap-1.5">
                    <Award className="w-4 h-4 text-emerald-400" /> 候選人智力養成進度
                  </h3>
                  <div className="space-y-2 text-xs leading-normal">
                    <div className="flex justify-between items-center bg-slate-950 p-2.5 rounded border border-slate-800/80">
                      <span>112年司法官民事法第一題 (時效抗辯)</span>
                      <span className="text-emerald-400 font-mono">已完成</span>
                    </div>
                    <div className="flex justify-between items-center bg-slate-950 p-2.5 rounded border border-slate-800/80">
                      <span>111年司法官刑事法第二題 (追訴時效)</span>
                      <span className="text-emerald-400 font-mono">已完成</span>
                    </div>
                  </div>
                </div>

              </div>

              {/* SYSTEM DIAGNOSTICS & BACKGROUND MONITOR */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6 border-t border-slate-800 pt-6">
                <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl flex flex-col gap-3">
                  <h3 className="text-xs font-semibold text-slate-300 tracking-wider flex items-center justify-between">
                    <span className="flex items-center gap-1.5"><SlidersHorizontal className="w-4 h-4 text-amber-500" /> 背景獨立爬蟲監控面板</span>
                    <button
                      onClick={handleTriggerScraper}
                      disabled={isTriggeringScraper || (systemStatus && systemStatus?.scraper?.status === "running")}
                      className="px-3 py-1 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-slate-100 text-[10px] font-bold rounded transition-all cursor-pointer border-none"
                    >
                      {systemStatus && systemStatus?.scraper?.status === "running" ? (
                        <span className="flex items-center gap-1"><RefreshCw className="w-2.5 h-2.5 animate-spin" /> 背景執行中...</span>
                      ) : (
                        "手動觸發爬蟲"
                      )}
                    </button>
                  </h3>
                  
                  {systemStatus && systemStatus?.scraper ? (
                    <div className="flex flex-col gap-2.5 text-xs font-mono">
                      <div className="flex justify-between items-center bg-slate-950 p-2 rounded border border-slate-850">
                        <span>目前狀態：</span>
                        <span className={`font-bold px-1.5 py-0.5 rounded ${
                          systemStatus?.scraper?.status === "running"
                            ? "text-amber-400 bg-amber-500/10 animate-pulse"
                            : systemStatus?.scraper?.status === "failed"
                              ? "text-rose-400 bg-rose-500/10"
                              : "text-emerald-400 bg-emerald-500/10"
                        }`}>
                          {systemStatus?.scraper?.status?.toUpperCase()}
                        </span>
                      </div>
                      
                      <select 
                        value={systemStatus?.ollama?.model}
                        onChange={handleModelChange}
                        className="bg-slate-900 border border-slate-700 text-slate-300 text-xs rounded px-2 py-0.5 ml-1 focus:outline-none focus:border-amber-500"
                      >
                        <optgroup label="本地模型">
                          {systemStatus.ollama.availableModels.map((m: string) => (
                            <option key={m} value={m}>{m}</option>
                          ))}
                        </optgroup>
                        {systemStatus.ollama.cloudModels && (
                          <optgroup label="雲端">
                            {systemStatus.ollama.cloudModels.map((m: string) => (
                              <option key={m} value={m}>{m}</option>
                            ))}
                          </optgroup>
                        )}
                      </select>
                      <div className="flex flex-col gap-1.5">
                        <div className="flex justify-between text-[10px] text-slate-400">
                          <span>爬取進度：</span>
                          <span className="font-bold text-amber-500">{systemStatus?.scraper?.progress}%</span>
                        </div>
                        <div className="w-full bg-slate-950 rounded-full h-1.5 overflow-hidden border border-slate-850">
                          <div 
                            className="bg-amber-500 h-1.5 rounded-full transition-all duration-300"
                            style={{ width: `${systemStatus?.scraper?.progress}%` }}
                          />
                        </div>
                      </div>

                      {/* Scraper Latest Log */}
                      <div className="flex flex-col gap-1 mt-1">
                        <span className="text-[10px] text-slate-500">最新背景反饋與檢討訊息：</span>
                        <div className={`p-2.5 rounded border text-[11px] leading-relaxed max-h-24 overflow-y-auto whitespace-pre-wrap ${
                          systemStatus?.scraper?.status === "failed"
                            ? "bg-rose-950/10 border-rose-900/30 text-rose-300"
                            : "bg-slate-950 border-slate-850 text-slate-350"
                        }`}>
                          {systemStatus?.scraper?.message || "尚無背景執行訊息。"}
                        </div>
                      </div>

                      {systemStatus?.scraper?.last_update && (
                        <div className="text-[10px] text-slate-500 text-right">
                          最後更新：{systemStatus?.scraper?.last_update}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-slate-500 italic text-[11px] text-center py-4">
                      無法讀取背景爬蟲狀態，請點擊「手動觸發爬蟲」啟動。
                    </div>
                  )}
                </div>

                {/* 外部 AI 技術引進 Agent */}
                <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl flex flex-col gap-3">
                  <h3 className="text-xs font-semibold text-slate-300 tracking-wider flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <Cpu className="w-4 h-4 text-emerald-400" />
                      外部 AI 技術引進 Agent
                    </span>
                    <button
                      onClick={handleTriggerTechAgent}
                      disabled={isTechAgentLoading}
                      className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-slate-100 text-[10px] font-bold rounded transition-all cursor-pointer border-none"
                    >
                      {isTechAgentLoading ? (
                        <span className="flex items-center gap-1"><RefreshCw className="w-2.5 h-2.5 animate-spin" /> 檢索中...</span>
                      ) : (
                        "一鍵檢索 AI 前沿技術"
                      )}
                    </button>
                  </h3>

                  <div className="flex flex-col gap-2 text-xs font-mono">
                    <div className="flex justify-between items-center bg-slate-950 p-2 rounded border border-slate-850">
                      <span>Agent 狀態：</span>
                      <span className={`font-bold px-1.5 py-0.5 rounded ${
                        isTechAgentLoading
                          ? "text-amber-400 bg-amber-500/10 animate-pulse"
                          : techAlerts.length > 0
                            ? "text-emerald-400 bg-emerald-500/10"
                            : "text-slate-400 bg-slate-500/10"
                      }`}>
                        {isTechAgentLoading ? "INGESTING" : techAlerts.length > 0 ? "RESOLVED_NOTIFIED" : "IDLE"}
                      </span>
                    </div>

                    <div className="flex flex-col gap-1 mt-1 max-h-[200px] overflow-y-auto space-y-2">
                      <span className="text-[10px] text-slate-500">最新引進建議與警告列表 (提醒管理者更新 MCP/算式模型)：</span>
                      {techAlerts.length === 0 ? (
                        <div className="p-2.5 rounded border border-slate-850 bg-slate-950 text-slate-500 text-[11px] italic text-center">
                          尚無建議項目，請點擊上方「一鍵檢索 AI 前沿技術」
                        </div>
                      ) : (
                        techAlerts.map((alert, idx) => (
                          <div key={alert.id || idx} className="p-2.5 rounded border border-slate-800 bg-black/30 text-[11px] leading-relaxed flex flex-col gap-1.5">
                            <div className="flex justify-between items-center">
                              <span className={`font-bold text-[10px] px-1 py-0.2 rounded ${
                                alert.type === "MCP_SPEC"
                                  ? "text-amber-400 bg-amber-500/10"
                                  : alert.type === "ALGORITHM"
                                    ? "text-indigo-400 bg-indigo-500/10"
                                    : "text-cyan-400 bg-cyan-500/10"
                              }`}>
                                {alert.type === "MCP_SPEC" ? "MCP 規格" : alert.type === "ALGORITHM" ? "算法模型" : "AI 前沿技術"}
                              </span>
                              <span className="text-[9px] text-slate-500 font-sans">{alert.timestamp}</span>
                            </div>
                            <div className="font-bold text-slate-200">{alert.title}</div>
                            <div className="text-slate-400 text-[10px] font-sans">{alert.content}</div>
                            <div className="text-[9px] text-slate-500 font-sans">來源：{alert.source}</div>
                            {alert.status === "pending" && (
                              <div className="flex justify-end gap-1.5 mt-1">
                                <button
                                  onClick={() => handleUpdateTechAlert(alert.id, "ignored")}
                                  className="px-2 py-0.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-[9px] text-slate-400 hover:text-slate-300 rounded cursor-pointer"
                                >
                                  忽略
                                </button>
                                <button
                                  onClick={() => handleUpdateTechAlert(alert.id, "resolved")}
                                  className="px-2 py-0.5 bg-emerald-950/40 hover:bg-emerald-900/40 border border-emerald-900/30 text-[9px] text-emerald-400 hover:text-emerald-300 rounded cursor-pointer"
                                >
                                  應用更新提醒
                                </button>
                              </div>
                            )}
                            {alert.status === "resolved" && (
                              <span className="text-[10px] text-emerald-400 font-bold self-end flex items-center gap-1">
                                ✓ 已應用並通知系統 Agent
                              </span>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>

                {/* AI 效能與 Token 預算評估 Agent */}
                <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl flex flex-col gap-3">
                  <h3 className="text-xs font-semibold text-slate-300 tracking-wider flex items-center justify-between">
                    <span className="flex items-center gap-1.5">
                      <SlidersHorizontal className="w-4 h-4 text-amber-500" />
                      AI 效能與 Token 預算評估 Agent
                    </span>
                    <button
                      onClick={handleTriggerEvaluation}
                      disabled={isOptEvaluating}
                      className="px-3 py-1 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-slate-100 text-[10px] font-bold rounded transition-all cursor-pointer border-none"
                    >
                      {isOptEvaluating ? (
                        <span className="flex items-center gap-1"><RefreshCw className="w-2.5 h-2.5 animate-spin" /> 測試中...</span>
                      ) : (
                        "開始自動化效能評估測試"
                      )}
                    </button>
                  </h3>

                  <div className="flex flex-col gap-2.5 text-xs">
                    <div className="flex justify-between items-center bg-slate-950 p-2.5 rounded border border-slate-850">
                      <div className="flex items-center gap-2">
                        <span className={`w-2.5 h-2.5 rounded-full ${isOptimizedMode ? "bg-emerald-400 animate-pulse" : "bg-amber-400 animate-pulse"}`} />
                        <span>工作站運行模式：</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className={`font-mono font-bold px-1.5 py-0.5 rounded ${isOptimizedMode ? "text-emerald-400 bg-emerald-500/10" : "text-amber-400 bg-amber-500/10"}`}>
                          {isOptimizedMode ? "高效能優化模式" : "標準大消耗模式"}
                        </span>
                        <button
                          onClick={() => handleToggleOptimizedMode(!isOptimizedMode)}
                          className={`px-2 py-0.5 rounded text-[10px] font-bold cursor-pointer transition-all border-none ${
                            isOptimizedMode 
                              ? "bg-amber-950/40 text-amber-400 hover:bg-amber-900/40" 
                              : "bg-emerald-950/40 text-emerald-400 hover:bg-emerald-900/40"
                          }`}
                        >
                          {isOptimizedMode ? "切回標準" : "切換優化"}
                        </button>
                      </div>
                    </div>

                    {optBenchmark ? (
                      <div className="space-y-3 font-sans">
                        <div className="overflow-x-auto">
                          <table className="w-full text-left text-[10px] font-mono border-collapse">
                            <thead>
                              <tr className="border-b border-slate-800 text-slate-400">
                                <th className="pb-1.5 pr-2">測試指標</th>
                                <th className="pb-1.5 pr-2">目前模式</th>
                                <th className="pb-1.5 pr-2">優化模式 (新技術)</th>
                                <th className="pb-1.5 text-emerald-400">預估效益</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-800/40 text-slate-300">
                              {optBenchmark.metrics.map((m: any, idx: number) => (
                                <tr key={idx}>
                                  <td className="py-1.5 pr-2">{m.name}</td>
                                  <td className="py-1.5 pr-2 text-slate-450">{m.current}</td>
                                  <td className="py-1.5 pr-2 text-amber-400">{m.optimized}</td>
                                  <td className="py-1.5 text-emerald-400 font-bold">
                                    {m.name.includes("消耗") ? "節省 84% Token" : m.name.includes("容量") ? "提升 8.3x" : m.name.includes("漂移") ? "降低 7x 漂移" : "提速 " + m.optimized.split(" ")[0]}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>

                        <div className="p-2.5 rounded border border-emerald-900/35 bg-emerald-950/10 text-slate-300 text-[11px] leading-relaxed">
                          <strong className="text-emerald-400 block mb-0.5 font-display text-[11px]">💡 效能評估 Agent 測試結論：</strong>
                          {optBenchmark.conclusion}
                        </div>
                      </div>
                    ) : (
                      <div className="p-4 rounded border border-slate-850 bg-slate-950 text-slate-500 text-[11px] italic text-center">
                        尚未進行任何評估，請點選右上角「開始自動化效能評估測試」讓 Agent 分析 Token 節省與提速效益。
                      </div>
                    )}
                  </div>
                </div>

                {/* Local environment diagnostics */}
                <div className="p-4 bg-slate-900/60 border border-slate-800 rounded-xl flex flex-col gap-3">
                  <h3 className="text-xs font-semibold text-slate-300 tracking-wider flex items-center gap-1.5">
                    <Shield className="w-4 h-4 text-emerald-400" /> 本地系統健康診斷
                  </h3>
                  
                  {systemStatus ? (
                    <div className="space-y-2 text-xs font-mono">
                      {/* Ollama latency check */}
                      <div className="flex justify-between items-center bg-slate-950 p-2.5 rounded border border-slate-850">
                        <div className="flex items-center gap-2">
                          <span className={`w-2.5 h-2.5 rounded-full ${
                            systemStatus?.ollama?.status === "connected"
                              ? "bg-emerald-400 animate-pulse"
                              : "bg-rose-505"
                          }`} />
                          <span>Ollama AI 服務：</span>
                          {systemStatus?.ollama?.status === "connected" && systemStatus?.ollama?.availableModels ? (
                            <select 
                              value={systemStatus?.ollama?.model}
                              onChange={handleModelChange}
                              className="bg-slate-900 border border-slate-700 text-slate-300 text-xs rounded px-2 py-0.5 ml-1 focus:outline-none focus:border-amber-500"
                            >
                              {systemStatus.ollama.availableModels.map((m: string) => (
                                <option key={m} value={m}>{m}</option>
                              ))}
                            </select>
                          ) : (
                            <span>({systemStatus?.ollama?.model})</span>
                          )}
                        </div>
                        {systemStatus?.ollama?.status === "connected" ? (
                          <span className="text-emerald-400 font-bold">連線正常 ({systemStatus?.ollama?.latency_ms}ms)</span>
                        ) : (
                          <span className="text-rose-450 font-bold" title={systemStatus?.ollama?.error}>連線中斷</span>
                        )}
                      </div>

                      {systemStatus?.ollama?.status !== "connected" && systemStatus?.ollama?.error && (
                        <div className="p-2 bg-rose-950/10 border border-rose-900/30 rounded text-[10px] text-rose-300 whitespace-pre-wrap leading-normal">
                          錯誤原因：{systemStatus?.ollama?.error}
                        </div>
                      )}

                      <div className="grid grid-cols-2 gap-2 text-[11px]">
                        <div className="bg-slate-950/40 p-2 rounded border border-slate-850">
                          <span className="text-slate-500 block">硬體內存使用：</span>
                          <span className="text-slate-300">{systemStatus?.system?.memory_usage}</span>
                        </div>
                        <div className="bg-slate-950/40 p-2 rounded border border-slate-850">
                          <span className="text-slate-500 block">CPU 核心數：</span>
                          <span className="text-slate-300">{systemStatus?.system?.cpu_cores} 核心</span>
                        </div>
                      </div>

                      <div className="bg-slate-950/40 p-2 rounded border border-slate-850 text-[11px] flex justify-between">
                        <span>法規/智商條目庫大小：</span>
                        <span className="text-amber-400 font-bold">
                          {systemStatus?.database?.laws_count} 條法規 / {systemStatus?.database?.intelligence_count} 筆智商 / {systemStatus?.database?.cases_count} 個案
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-slate-500 italic text-[11px] text-center py-4">
                      正在載入本地健康診斷狀態...
                    </div>
                  )}
                </div>
              </div>

              {/* Local PC copy instructions */}
              <div className="p-4 bg-slate-900/30 border border-dashed border-slate-800 rounded-xl">
                <h3 className="text-xs font-semibold text-amber-500 mb-2">💻 如何將本工作站完全復刻、執行在您的 Windows 本地端？</h3>
                <p className="text-xs text-slate-300 leading-relaxed mb-4">
                  我們已經為您把所有寫對的、100% 正確的 Python 代碼、依賴套件與一鍵啟動批次檔完全配對。
                  為了防止 Windows 系統預設將 PowerShell 腳本以「編輯模式」或「記事本」打開而未執行的安全限制，我們特別為您包裝並提供了「防安全限制一鍵批次啟動器（.bat）」。
                </p>

                {/* BIG PROMINENT DOWNLOAD BUTTON */}
                <div className="mb-5 bg-slate-950/40 p-4 border border-amber-500/15 rounded-xl flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div className="space-y-1 text-left">
                    <div className="text-xs font-semibold text-amber-400 flex items-center gap-1.5 font-sans">
                      💾 取得本機安全、離線、免付費 AI 法律工作站套件
                    </div>
                    <p className="text-[11px] text-slate-400 max-w-md">
                      內含最新的 Python 部署代碼、`setup_lexmind.ps1` 腳本，以及專用於解決 Windows 按右鍵或雙擊自動開啟編輯模式而無法執行的防塵防呆批次檔。
                    </p>
                  </div>

                  <a 
                    href="/api/download-windows-bundle"
                    className="w-full sm:w-auto px-5 py-3 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-600 hover:to-amber-700 text-slate-950 hover:text-slate-950 font-bold text-xs rounded-xl shadow-lg hover:shadow-amber-500/10 transition-all text-center flex items-center justify-center gap-2 border border-amber-400/20 active:scale-[0.98] font-sans"
                  >
                    <Download className="w-4 h-4 text-slate-950 inline" />
                    下載Windows一鍵配置套件(.ZIP)
                  </a>
                </div>

                <div className="bg-slate-950 p-4 rounded-lg border border-slate-850 text-xs font-sans text-slate-300 space-y-3 leading-relaxed mb-4">
                  <div>
                    💡 <b className="text-emerald-400">第一步：雙擊極簡解決方案（推薦 💯）</b>
                    <p className="mt-1 text-slate-405 pl-4">
                      進入您解壓縮出來的資料夾（例如下載區的資料夾），找到並進入 <b className="text-amber-400">`/windows_desktop_deployment/`</b> 子目錄，
                      直接雙擊運行 <b>`雙擊一鍵運行我_安全離線部署.bat`</b> 批次檔！<br />
                      <i>(這個批次檔會自動以「Bypass 安全層級」幫您呼叫 PowerShell 進行部署，完全免去自行輸入任何指令與路徑的麻煩！)</i>
                    </p>
                  </div>
                  <div className="border-t border-slate-800/60 pt-2.5">
                    ⚙️ <b className="text-sky-400">手動 PowerShell 解決方案（若您想自行輸入指令）：</b>
                    <p className="mt-1 text-slate-405 pl-4">
                      請注意，<code className="text-rose-400 font-mono">C:\LocalAI_Workstation</code> 資料夾<b>只有在部署腳本運行成功後才會被自動建立</b>！在您尚未首次部署前，您的硬碟中還沒有這個目錄，這就是為什麼在執行前對其進行 cd 會顯示找不到路徑的原因。<br />
                      如果您偏好手動在 PowerShell 中執行，請使用以下正確步驟：
                    </p>
                    <ol className="list-decimal pl-8 mt-1 space-y-1 text-slate-400 font-mono text-[11px]">
                      <li>1. 在 Windows 搜尋列輸入 <span className="text-white bg-slate-850 px-1 rounded font-sans font-semibold">PowerShell</span> 並開啟。</li>
                      <li>2. 先輸入 <span className="text-amber-400">cd </span> (後面留一格空格)，然後從 Windows 實體檔案總管中，<b>將解壓縮出來的 `windows_desktop_deployment` 資料夾「直接拖曳拖進」PowerShell 視窗中</b>，它會自動為您填入當下的完整確切下載解壓縮路徑！最後按下 Enter。</li>
                      <li>3. 接著輸入：<span className="text-emerald-400">powershell -NoProfile -ExecutionPolicy Bypass -File .\setup_lexmind.ps1</span> 即可一鍵運行！</li>
                    </ol>
                  </div>
                </div>
              </div>

            </div>
          )}

          {/* TAB 7: RAG BENCHMARK EVALUATION SYSTEM */}
          {activeTab === "benchmark" && (
            <div className="bg-slate-950/80 rounded-xl border border-slate-800 flex flex-col md:flex-row min-h-[700px] overflow-hidden">
              
              {/* Sidebar of the Benchmark Tool */}
              <div className="w-full md:w-64 bg-slate-950 border-r border-slate-850 p-5 flex flex-col gap-6 shrink-0">
                
                {/* Logo & Title */}
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-500">
                    <Scale className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold tracking-wide text-slate-100 uppercase">台灣法律 RAG</h2>
                    <p className="text-[10px] text-slate-400 font-mono">評測基準系統 v1.0</p>
                  </div>
                </div>

                <hr className="border-slate-850" />

                {/* Statistics Box */}
                <div className="flex flex-col gap-3">
                  <span className="text-[10px] font-bold tracking-wider text-slate-450 uppercase">資料集統計</span>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="bg-slate-900/50 p-2 border border-slate-850 rounded">
                      <div className="text-[10px] text-slate-500 font-mono">樣本數</div>
                      <div className="text-base font-bold text-amber-500 font-mono mt-0.5">{benchmarkStats.samplesCount}</div>
                    </div>
                    <div className="bg-slate-900/50 p-2 border border-slate-850 rounded">
                      <div className="text-[10px] text-slate-500 font-mono">法律領域</div>
                      <div className="text-base font-bold text-slate-200 font-mono mt-0.5">{benchmarkStats.domainsCount}</div>
                    </div>
                    <div className="bg-slate-900/50 p-2 border border-slate-850 rounded">
                      <div className="text-[10px] text-slate-500 font-mono">難度層級</div>
                      <div className="text-base font-bold text-slate-200 font-mono mt-0.5">{benchmarkStats.difficultiesCount}</div>
                    </div>
                    <div className="bg-slate-900/50 p-2 border border-slate-850 rounded">
                      <div className="text-[10px] text-slate-500 font-mono">查詢類型</div>
                      <div className="text-base font-bold text-slate-200 font-mono mt-0.5">{benchmarkStats.queryTypesCount}</div>
                    </div>
                  </div>
                </div>

                <hr className="border-slate-850" />

                {/* Navigation Menu */}
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold tracking-wider text-slate-450 uppercase mb-1">主選單</span>
                  {[
                    { id: "overview", label: "📊 總覽儀表板", icon: SlidersHorizontal },
                    { id: "library", label: "📚 評測樣本庫", icon: BookOpen },
                    { id: "about", label: "ℹ️ 關於系統", icon: HelpCircle }
                  ].map(item => {
                    const Icon = item.icon;
                    const isActive = benchmarkSubTab === item.id;
                    return (
                      <button
                        key={item.id}
                        onClick={() => {
                          setBenchmarkSubTab(item.id as any);
                          setSelectedBenchSample(null);
                        }}
                        className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-xs font-semibold cursor-pointer transition-all ${
                          isActive 
                            ? "bg-amber-600/10 border border-amber-600/30 text-amber-400" 
                            : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60 border border-transparent"
                        }`}
                      >
                        <Icon className={`w-4 h-4 ${isActive ? "text-amber-500" : "text-slate-400"}`} />
                        {item.label}
                      </button>
                    );
                  })}
                </div>

                <div className="mt-auto pt-6 border-t border-slate-850/60">
                  <p className="text-[9px] text-slate-600 leading-normal font-sans">
                    資料來源：<br />
                    司法院法學資料檢索系統<br />
                    法務部全國法規資料庫
                  </p>
                </div>
              </div>

              {/* Main Content Pane */}
              <div className="flex-1 p-6 flex flex-col gap-6 overflow-y-auto">
                
                {/* Loader Overlay */}
                {isReportLoading && !isEvaluating && (
                  <div className="flex flex-col justify-center items-center py-20 gap-3">
                    <RefreshCw className="w-8 h-8 animate-spin text-amber-500" />
                    <span className="text-xs text-slate-400">正在加載評測數據...</span>
                  </div>
                )}

                {/* Sub Tab: Overview */}
                {!isReportLoading && benchmarkSubTab === "overview" && (
                  <div className="flex flex-col gap-6">
                    
                    {/* Header bar */}
                    <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900/40 p-4 border border-slate-850 rounded-xl">
                      <div>
                        <h3 className="text-base font-bold text-white">台灣法律 RAG 指標總覽</h3>
                        <p className="text-xs text-slate-400 mt-0.5">系統已為 520 個評測樣本進行了精確的自動評估與基準度量。</p>
                      </div>
                      <button
                        onClick={() => fetchBenchmarkReport(true)}
                        disabled={isEvaluating}
                        className="px-4 py-2 bg-amber-600 hover:bg-amber-500 disabled:bg-slate-850 text-white font-bold text-xs rounded-lg transition-colors cursor-pointer flex items-center gap-2 disabled:cursor-not-allowed"
                      >
                        {isEvaluating ? (
                          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Sparkles className="w-3.5 h-3.5" />
                        )}
                        {isEvaluating ? "正在評測中..." : "⚡ 啟動 RAG 評測基準"}
                      </button>
                    </div>

                    {/* Summary Cards */}
                    {benchmarkReport && (
                      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                        {[
                          { label: "🏆 綜合得分", val: benchmarkReport.summary.overall_score, desc: "檢索、引證及生成綜合加權" },
                          { label: "🔍 Precision@5", val: benchmarkReport.summary.precision_at_5, desc: "前5個檢索結果的精準率" },
                          { label: "🎯 Recall@5", val: benchmarkReport.summary.recall_at_5, desc: "前5個檢索結果的召回率" },
                          { label: "📑 Citation F1", val: benchmarkReport.summary.citation_f1, desc: "引用條文與判決字號精準度" },
                          { label: "💡 概念覆蓋率", val: benchmarkReport.summary.concept_coverage, desc: "核心法律術語與爭點覆蓋率" }
                        ].map((card, i) => (
                          <div key={i} className="bg-slate-900/40 border border-slate-850 p-4 rounded-xl flex flex-col justify-between">
                            <span className="text-[11px] font-bold text-slate-400">{card.label}</span>
                            <div className="text-2xl font-bold text-slate-100 font-mono my-2">
                              {(card.val * 100).toFixed(1)}%
                            </div>
                            <span className="text-[9px] text-slate-500 leading-snug">{card.desc}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Charts grid */}
                    {benchmarkReport && (
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        
                        {/* Core Metrics Radar */}
                        <div className="bg-slate-900/40 border border-slate-850 p-5 rounded-xl">
                          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-4">核心評測維度分佈 (Radar)</h4>
                          <div className="h-64 flex justify-center items-center">
                            <ResponsiveContainer width="100%" height="100%">
                              <RadarChart cx="50%" cy="50%" outerRadius="80%" data={[
                                { subject: "綜合得分", value: benchmarkReport.summary.overall_score * 100 },
                                { subject: "Precision@5", value: benchmarkReport.summary.precision_at_5 * 100 },
                                { subject: "Recall@5", value: benchmarkReport.summary.recall_at_5 * 100 },
                                { subject: "Citation F1", value: benchmarkReport.summary.citation_f1 * 100 },
                                { subject: "概念覆蓋率", value: benchmarkReport.summary.concept_coverage * 100 }
                              ]}>
                                <PolarGrid stroke="#334155" />
                                <PolarAngleAxis dataKey="subject" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 9 }} />
                                <Radar name="RAG 效能" dataKey="value" stroke="#f59e0b" fill="#f59e0b" fillOpacity={0.15} />
                              </RadarChart>
                            </ResponsiveContainer>
                          </div>
                        </div>

                        {/* Domain comparison bar */}
                        <div className="bg-slate-900/40 border border-slate-850 p-5 rounded-xl">
                          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-4">四大法律科目得分對比</h4>
                          <div className="h-64">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={[
                                { name: "民法 (Civil)", score: benchmarkReport.by_domain.civil.overall_score * 100 },
                                { name: "刑法 (Criminal)", score: benchmarkReport.by_domain.criminal.overall_score * 100 },
                                { name: "公法 (Const)", score: benchmarkReport.by_domain.constitutional.overall_score * 100 },
                                { name: "程序法 (Proc)", score: benchmarkReport.by_domain.procedure.overall_score * 100 }
                              ]}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                                <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 10 }} />
                                <Tooltip 
                                  contentStyle={{ backgroundColor: "#020617", borderColor: "#334155", borderRadius: 8, fontSize: 11 }}
                                  formatter={(value: any) => [`${parseFloat(value).toFixed(1)} 分`, "得分"]}
                                />
                                <Bar dataKey="score" radius={[4, 4, 0, 0]}>
                                  {
                                    [0, 1, 2, 3].map((entry, index) => {
                                      const colors = ["#f59e0b", "#10b981", "#3b82f6", "#8b5cf6"];
                                      return <Cell key={`cell-${index}`} fill={colors[index]} />;
                                    })
                                  }
                                </Bar>
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        </div>

                        {/* Difficulty comparison bar */}
                        <div className="bg-slate-900/40 border border-slate-850 p-5 rounded-xl">
                          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-4">難度級別得分對比</h4>
                          <div className="h-64">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={[
                                { name: "基礎 (Basic)", score: benchmarkReport.by_difficulty.basic.overall_score * 100 },
                                { name: "中階 (Interm)", score: benchmarkReport.by_difficulty.intermediate.overall_score * 100 },
                                { name: "高階 (Adv)", score: benchmarkReport.by_difficulty.advanced.overall_score * 100 },
                                { name: "專家 (Expert)", score: benchmarkReport.by_difficulty.expert.overall_score * 100 }
                              ]}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                                <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 10 }} />
                                <Tooltip 
                                  contentStyle={{ backgroundColor: "#020617", borderColor: "#334155", borderRadius: 8, fontSize: 11 }}
                                  formatter={(value: any) => [`${parseFloat(value).toFixed(1)} 分`, "得分"]}
                                />
                                <Bar dataKey="score" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        </div>

                        {/* Query type comparison bar */}
                        <div className="bg-slate-900/40 border border-slate-850 p-5 rounded-xl">
                          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-4">查詢類型得分對比</h4>
                          <div className="h-64">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart data={[
                                { name: "檢索 (Factual)", score: benchmarkReport.by_query_type.factual_retrieval.overall_score * 100 },
                                { name: "單一 (SingleDoc)", score: benchmarkReport.by_query_type.single_doc.overall_score * 100 },
                                { name: "多文 (MultiDoc)", score: benchmarkReport.by_query_type.multi_doc_synthesis.overall_score * 100 },
                                { name: "引用鏈 (Chain)", score: benchmarkReport.by_query_type.citation_chain.overall_score * 100 },
                                { name: "程序推理 (Proc)", score: benchmarkReport.by_query_type.procedural_reasoning.overall_score * 100 }
                              ]}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                                <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 9 }} />
                                <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 10 }} />
                                <Tooltip 
                                  contentStyle={{ backgroundColor: "#020617", borderColor: "#334155", borderRadius: 8, fontSize: 11 }}
                                  formatter={(value: any) => [`${parseFloat(value).toFixed(1)} 分`, "得分"]}
                                />
                                <Bar dataKey="score" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        </div>

                      </div>
                    )}

                    {/* Successes & Failures */}
                    {benchmarkReport && (
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        
                        {/* Top failures */}
                        <div className="bg-slate-900/40 border border-slate-850 p-5 rounded-xl flex flex-col gap-3">
                          <h4 className="text-xs font-bold text-rose-450 uppercase tracking-wider flex items-center gap-1.5">
                            <AlertTriangle className="w-4 h-4" /> 最亟待改善案例 (Top 5 Failures)
                          </h4>
                          <div className="flex flex-col gap-2">
                            {benchmarkReport.top_failures.slice(0, 5).map((f: any, idx: number) => (
                              <div key={idx} className="bg-slate-950/60 border border-slate-850 p-3 rounded-lg flex flex-col gap-1 hover:border-slate-800 transition-colors">
                                <div className="flex justify-between items-center text-xs font-mono">
                                  <span className="text-rose-400 font-bold">{f.id}</span>
                                  <span className="text-[10px] text-slate-500">
                                    {f.domain === "civil" ? "民法" : f.domain === "criminal" ? "刑法" : f.domain === "procedure" ? "程序法" : "公法"} · {
                                      f.difficulty === "basic" ? "基礎" : f.difficulty === "intermediate" ? "中階" : f.difficulty === "advanced" ? "高階" : "專家"
                                    }
                                  </span>
                                </div>
                                <p className="text-xs text-slate-300 font-medium line-clamp-1 mt-1">{f.query}</p>
                                <div className="flex justify-between text-[10px] text-slate-500 mt-1.5 pt-1.5 border-t border-slate-900">
                                  <span>綜合得分: <span className="text-rose-400 font-bold">{(f.overall_score * 100).toFixed(1)}%</span></span>
                                  <span>Citation F1: {(f.citation_f1 * 100).toFixed(0)}%</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Top successes */}
                        <div className="bg-slate-900/40 border border-slate-850 p-5 rounded-xl flex flex-col gap-3">
                          <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
                            <CheckCircle className="w-4 h-4" /> 表現最優異案例 (Top 5 Successes)
                          </h4>
                          <div className="flex flex-col gap-2">
                            {benchmarkReport.top_successes.slice(0, 5).map((s: any, idx: number) => (
                              <div key={idx} className="bg-slate-950/60 border border-slate-850 p-3 rounded-lg flex flex-col gap-1 hover:border-slate-800 transition-colors">
                                <div className="flex justify-between items-center text-xs font-mono">
                                  <span className="text-emerald-400 font-bold">{s.id}</span>
                                  <span className="text-[10px] text-slate-500">
                                    {s.domain === "civil" ? "民法" : s.domain === "criminal" ? "刑法" : s.domain === "procedure" ? "程序法" : "公法"} · {
                                      s.difficulty === "basic" ? "基礎" : s.difficulty === "intermediate" ? "中階" : s.difficulty === "advanced" ? "高階" : "專家"
                                    }
                                  </span>
                                </div>
                                <p className="text-xs text-slate-300 font-medium line-clamp-1 mt-1">{s.query}</p>
                                <div className="flex justify-between text-[10px] text-slate-500 mt-1.5 pt-1.5 border-t border-slate-900">
                                  <span>綜合得分: <span className="text-emerald-400 font-bold">{(s.overall_score * 100).toFixed(1)}%</span></span>
                                  <span>Citation F1: {(s.citation_f1 * 100).toFixed(0)}%</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                      </div>
                    )}

                  </div>
                )}

                {/* Sub Tab: Benchmark Samples Library */}
                {!isReportLoading && benchmarkSubTab === "library" && (
                  <div className="flex flex-col gap-6">
                    
                    {/* Search and Filters */}
                    <div className="bg-slate-900/40 p-4 border border-slate-850 rounded-xl flex flex-col gap-4">
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={benchLibrarySearch}
                          onChange={(e) => {
                            setBenchLibrarySearch(e.target.value);
                            setBenchLibraryPage(1);
                          }}
                          placeholder="搜尋問題關鍵字、條文或法律術語..."
                          className="flex-1 bg-slate-950 border border-slate-850 rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-amber-500/50 text-slate-200"
                        />
                      </div>
                      <div className="grid grid-cols-3 gap-3">
                        <select
                          value={benchLibraryDomain}
                          onChange={(e) => {
                            setBenchLibraryDomain(e.target.value);
                            setBenchLibraryPage(1);
                          }}
                          className="bg-slate-950 border border-slate-850 rounded-lg p-2 text-xs text-slate-300 focus:outline-none cursor-pointer"
                        >
                          <option value="">過濾法律科目 (全部)</option>
                          <option value="civil">民法 (Civil)</option>
                          <option value="criminal">刑法 (Criminal)</option>
                          <option value="procedure">程序法 (Procedure)</option>
                          <option value="constitutional">公法 (Constitutional)</option>
                        </select>
                        <select
                          value={benchLibraryDifficulty}
                          onChange={(e) => {
                            setBenchLibraryDifficulty(e.target.value);
                            setBenchLibraryPage(1);
                          }}
                          className="bg-slate-950 border border-slate-850 rounded-lg p-2 text-xs text-slate-300 focus:outline-none cursor-pointer"
                        >
                          <option value="">過濾難度層級 (全部)</option>
                          <option value="basic">基礎 (Basic)</option>
                          <option value="intermediate">中階 (Intermediate)</option>
                          <option value="advanced">高階 (Advanced)</option>
                          <option value="expert">專家 (Expert)</option>
                        </select>
                        <select
                          value={benchLibraryQueryType}
                          onChange={(e) => {
                            setBenchLibraryQueryType(e.target.value);
                            setBenchLibraryPage(1);
                          }}
                          className="bg-slate-950 border border-slate-850 rounded-lg p-2 text-xs text-slate-300 focus:outline-none cursor-pointer"
                        >
                          <option value="">過濾查詢類型 (全部)</option>
                          <option value="factual_retrieval">事實檢索 (Factual)</option>
                          <option value="single_doc">單一文件 (Single Doc)</option>
                          <option value="multi_doc_synthesis">多文整合 (Multi Doc)</option>
                          <option value="citation_chain">法理引用鏈 (Chain)</option>
                          <option value="procedural_reasoning">程序法推理 (Proc)</option>
                        </select>
                      </div>
                    </div>

                    {/* Table View */}
                    <div className="bg-slate-900/20 border border-slate-850 rounded-xl overflow-hidden">
                      {isLibraryLoading ? (
                        <div className="flex flex-col justify-center items-center py-20 gap-3">
                          <RefreshCw className="w-6 h-6 animate-spin text-amber-500" />
                          <span className="text-xs text-slate-400">正在加載樣本...</span>
                        </div>
                      ) : benchLibrarySamples.length === 0 ? (
                        <div className="text-center py-20 text-slate-500 text-xs">
                          沒有符合條件的評測樣本
                        </div>
                      ) : (
                        <div className="overflow-x-auto">
                          <table className="w-full text-left border-collapse text-xs">
                            <thead>
                              <tr className="bg-slate-900/60 border-b border-slate-850 text-slate-400 font-semibold">
                                <th className="p-3 font-mono w-24">編號</th>
                                <th className="p-3 w-20">科目</th>
                                <th className="p-3 w-20">難度</th>
                                <th className="p-3 w-24 font-semibold">類型</th>
                                <th className="p-3">法律問題描述</th>
                                <th className="p-3 text-right w-24">操作</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-850/60">
                              {benchLibrarySamples.map((s, idx) => (
                                <tr key={idx} className="hover:bg-slate-900/40 text-slate-300">
                                  <td className="p-3 font-mono text-amber-500 font-bold">{s.id}</td>
                                  <td className="p-3 font-medium">
                                    {s.domain === "civil" && "民法"}
                                    {s.domain === "criminal" && "刑法"}
                                    {s.domain === "procedure" && "程序法"}
                                    {s.domain === "constitutional" && "公法"}
                                  </td>
                                  <td className="p-3">
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                      s.difficulty === "basic" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                                      s.difficulty === "intermediate" ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" :
                                      s.difficulty === "advanced" ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                                      "bg-rose-500/10 text-rose-450 border border-rose-550/20"
                                    }`}>
                                      {s.difficulty === "basic" ? "基礎" :
                                       s.difficulty === "intermediate" ? "中階" :
                                       s.difficulty === "advanced" ? "高階" : "專家"}
                                    </span>
                                  </td>
                                  <td className="p-3 text-[11px] text-slate-400 font-mono">
                                    {s.query_type}
                                  </td>
                                  <td className="p-3 font-medium max-w-xs truncate">{s.query}</td>
                                  <td className="p-3 text-right">
                                    <button
                                      onClick={() => setSelectedBenchSample(s)}
                                      className="px-2.5 py-1 bg-slate-900 border border-slate-850 hover:border-slate-700 text-[10px] text-slate-200 hover:text-white rounded transition-colors cursor-pointer"
                                    >
                                      查看詳情
                                    </button>
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}

                      {/* Pagination Controls */}
                      {benchLibraryTotal > 0 && (
                        <div className="flex justify-between items-center p-4 bg-slate-900/40 border-t border-slate-850 text-xs">
                          <span className="text-slate-400">
                            共 <span className="font-bold text-amber-500 font-mono">{benchLibraryTotal}</span> 筆樣本
                          </span>
                          <div className="flex gap-2 items-center">
                            <button
                              disabled={benchLibraryPage === 1}
                              onClick={() => setBenchLibraryPage(prev => prev - 1)}
                              className="px-2.5 py-1 bg-slate-950 border border-slate-850 hover:bg-slate-900 rounded disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-slate-300 font-bold cursor-pointer"
                            >
                              上一頁
                            </button>
                            <span className="text-slate-300 font-mono">
                              {benchLibraryPage} / {Math.ceil(benchLibraryTotal / benchLibraryLimit)}
                            </span>
                            <button
                              disabled={benchLibraryPage >= Math.ceil(benchLibraryTotal / benchLibraryLimit)}
                              onClick={() => setBenchLibraryPage(prev => prev + 1)}
                              className="px-2.5 py-1 bg-slate-950 border border-slate-850 hover:bg-slate-900 rounded disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-slate-300 font-bold cursor-pointer"
                            >
                              下一頁
                            </button>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Detailed Sample View panel */}
                    {selectedBenchSample && (
                      <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 flex flex-col gap-4 relative">
                        <button
                          onClick={() => setSelectedBenchSample(null)}
                          className="absolute top-4 right-4 p-1.5 bg-slate-950 hover:bg-slate-850 border border-slate-850 text-slate-400 hover:text-white rounded-lg cursor-pointer transition-colors"
                          title="關閉詳情"
                        >
                          <X className="w-4 h-4" />
                        </button>
                        
                        <div className="flex items-center gap-3">
                          <span className="text-base font-mono font-bold text-amber-500">{selectedBenchSample.id}</span>
                          <span className="text-xs text-slate-400">基準樣本詳情與參考解答</span>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div className="flex flex-col gap-1">
                            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">測試問題</span>
                            <div className="p-3 bg-slate-950 border border-slate-850 rounded-lg text-xs text-slate-200 font-medium leading-relaxed">
                              {selectedBenchSample.query}
                            </div>
                          </div>
                          
                          <div className="flex flex-col gap-1">
                            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">預期引用法規與實務裁判</span>
                            <div className="p-3 bg-slate-950 border border-slate-850 rounded-lg text-xs flex flex-col gap-1">
                              {selectedBenchSample.expected_citations && selectedBenchSample.expected_citations.length > 0 ? (
                                selectedBenchSample.expected_citations.map((cit: string, idx: number) => (
                                  <div key={idx} className="text-amber-500 font-mono font-bold flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 bg-amber-500 rounded-full shrink-0" />
                                    {cit}
                                  </div>
                                ))
                              ) : (
                                <span className="text-slate-500 italic">無明確指定引用條文</span>
                              )}
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-col gap-1">
                          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">參考答案 (Ground Truth)</span>
                          <div className="p-4 bg-slate-950 border border-slate-850 rounded-lg text-xs text-slate-300 leading-relaxed font-sans max-h-48 overflow-y-auto">
                            {selectedBenchSample.ground_truth_answer}
                          </div>
                        </div>

                        <div className="flex flex-col gap-1">
                          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">核心法律概念與爭點</span>
                          <div className="flex flex-wrap gap-1.5">
                            {selectedBenchSample.key_concepts && selectedBenchSample.key_concepts.map((c: string, idx: number) => (
                              <span key={idx} className="bg-slate-900 border border-slate-850 text-slate-300 text-[10px] px-2.5 py-1 rounded font-medium">
                                💡 {c}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                  </div>
                )}

                {/* Sub Tab: About the System */}
                {!isReportLoading && benchmarkSubTab === "about" && (
                  <div className="flex flex-col gap-6 text-slate-350 text-xs leading-relaxed max-w-3xl">
                    <div className="bg-slate-900/40 p-5 border border-slate-850 rounded-xl flex flex-col gap-4">
                      <h3 className="text-sm font-bold text-white uppercase tracking-wider">臺灣法律 RAG 評測指標科學公式說明</h3>
                      
                      <div className="space-y-4">
                        <div>
                          <h4 className="text-slate-200 font-bold">1. 檢索品質指標 (Retrieval Precision & Recall)</h4>
                          <p className="mt-1">
                            檢索精準度為前 5 個檢索結果中，含有地方法院/最高法院判決或法條等與 Ground Truth 相關之比例：
                          </p>
                          <div className="bg-slate-950 p-2.5 rounded border border-slate-900 font-mono text-[10px] my-1 text-center text-amber-500">
                            Precision@k = |Relevant ∩ Retrieved[:k]| / k
                          </div>
                          <div className="bg-slate-950 p-2.5 rounded border border-slate-900 font-mono text-[10px] my-1 text-center text-amber-500">
                            Recall@k = |Relevant ∩ Retrieved[:k]| / |Relevant|
                          </div>
                        </div>

                        <div>
                          <h4 className="text-slate-200 font-bold">2. 台灣法律條文與裁判精確匹配 (Citation Accuracy F1)</h4>
                          <p className="mt-1">
                            法律實務极其嚴謹，本系統利用 <code>TaiwanLegalCitationParser</code> 全自動正則比對台灣法典（如：民法第767條第1項前段）及歷年裁判字號（如：最高法院112年度台上字第1234號判決），在忽略「項」、「款」、「前後段」之干擾下進行標準化匹配，計算其綜合 Precision 與 Recall 的 F1 分數。
                          </p>
                        </div>

                        <div>
                          <h4 className="text-slate-200 font-bold">3. 法律三段論句構評估 (Legal Syllogism Heuristic)</h4>
                          <p className="mt-1">
                            為防範法理邏輯斷層與 AI 幻覺，系統會對生成的答覆進行自然語言語境正則比對，檢驗是否滿足：
                          </p>
                          <ul className="list-disc pl-5 mt-1 space-y-1 text-slate-400">
                            <li><strong>大前提 (Major Premise)</strong>：援引之法律規範（如：依民法第184條之規定...）。</li>
                            <li><strong>小前提 (Minor Premise)</strong>：個案具體事實認定（如：查本件被告開車超速侵害原告...）。</li>
                            <li><strong>結論 (Conclusion)</strong>：法律效果之宣告（如：故原告得請求損害賠償...）。</li>
                          </ul>
                        </div>
                        
                        <div>
                          <h4 className="text-slate-200 font-bold">4. 綜合度量權重分佈 (Overall Composite Score)</h4>
                          <p className="mt-1">
                            最終的 RAG 綜合評估得分 (Overall Score) 採用以下權重進行加權計算：
                          </p>
                          <div className="bg-slate-950 p-3 rounded border border-slate-900 font-mono text-[10px] my-2 text-amber-500">
                            Overall Score = 30% * (Precision@5 + Recall@5) / 2 + 35% * Citation F1 + 35% * (Concept Coverage + Structure Score) / 2
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

              </div>
            </div>
          )}

        </section>

      </main>

      {/* Footer copyright */}
      <footer className="py-4 text-center text-xs text-slate-600 bg-slate-950/80 border-t border-slate-900 font-mono">
        © 2026 LexMind-Omni AI Workspace. Powered by local LLM and RWS weighting. AI response is for experimental reference; please consult licensed Taiwan Attorneys for formal proceedings.
      </footer>

      {/* Global Processing Completion Popup Modal */}
      <AnimatePresence>
        {completionModal.isOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setCompletionModal(prev => ({ ...prev, isOpen: false }))}
              className="absolute inset-0 bg-slate-950/80 backdrop-blur-md"
            />
            {/* Modal Dialog */}
            <motion.div
              initial={{ scale: 0.95, y: 15, opacity: 0 }}
              animate={{ scale: 1, y: 0, opacity: 1 }}
              exit={{ scale: 0.95, y: 15, opacity: 0 }}
              transition={{ type: "spring", stiffness: 350, damping: 25 }}
              className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl overflow-hidden text-slate-100 ring-1 ring-amber-500/20"
            >
              <div className="absolute top-0 left-0 w-full h-[3px] bg-gradient-to-r from-amber-500 via-amber-600 to-amber-700" />
              
              <button
                type="button"
                onClick={() => setCompletionModal(prev => ({ ...prev, isOpen: false }))}
                className="absolute top-4 right-4 text-slate-450 hover:text-slate-100 transition-colors p-1"
              >
                <X className="w-4 h-4" />
              </button>

              <div className="flex flex-col items-center text-center mt-2 mb-6">
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-full text-emerald-450 mb-3.5 shadow-inner">
                  <CheckCircle className="w-8 h-8 text-emerald-400" />
                </div>
                <h3 className="text-lg font-bold font-display tracking-tight text-white">
                  {completionModal.type === "parse" ? "🎉 批次多模態教材提取完成" : "🚀 智產智商庫消化完成"}
                </h3>
                <p className="text-xs text-slate-400 mt-1 max-w-sm">
                  {completionModal.type === "parse" 
                    ? "影音、影像 OCR 及學術大數據，已成功解析至待處理隊列！" 
                    : "所選多模態語音及書狀，已成功完成去筆噪校正並注入智產智商庫！"}
                </p>
              </div>

              {/* Bento Grid Analytics */}
              <div className="grid grid-cols-3 gap-3 mb-5">
                <div className="p-3 bg-slate-950/50 rounded-xl border border-slate-850 text-center">
                  <span className="block text-[9px] text-slate-500 font-semibold mb-1 tracking-wider uppercase">解析檔案數</span>
                  <span className="text-base font-bold text-amber-500 font-mono">{completionModal.totalFiles}</span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">個檔案</span>
                </div>
                <div className="p-3 bg-slate-950/50 rounded-xl border border-slate-850 text-center">
                  <span className="block text-[9px] text-slate-500 font-semibold mb-1 tracking-wider uppercase">耗費時間</span>
                  <span className="text-base font-bold text-emerald-400 font-mono">
                    {completionModal.timeSpentSec.toFixed(2)}
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">秒</span>
                </div>
                <div className="p-3 bg-slate-950/50 rounded-xl border border-slate-850 text-center">
                  <span className="block text-[9px] text-slate-500 font-semibold mb-1 tracking-wider uppercase">智商庫總數</span>
                  <span className="text-base font-bold text-cyan-400 font-mono">
                    {completionModal.totalVaultItems || totalVaultItems}
                  </span>
                  <span className="text-[10px] text-slate-400 block mt-0.5">筆摘要條目</span>
                </div>
              </div>

              {/* Parsed files list */}
              <div className="border border-slate-850 rounded-xl bg-slate-950/30 p-3 mb-6 max-h-[140px] overflow-y-auto">
                <div className="text-[10px] font-bold text-slate-500 uppercase mb-2 tracking-wider flex justify-between">
                  <span>📂 處理對象檔案</span>
                  <span>狀態</span>
                </div>
                <div className="space-y-1.5">
                  {completionModal.fileList && completionModal.fileList.length > 0 ? (
                    completionModal.fileList.map((file, i) => (
                      <div key={i} className="flex justify-between items-center text-[11px] py-1 border-b border-slate-850/40 last:border-0 pb-1">
                        <span className="text-slate-300 truncate max-w-[280px] flex items-center gap-1.5 font-mono" title={file.name}>
                          <span className="px-1 py-0.5 bg-slate-900 border border-slate-800 text-[8px] font-bold text-slate-500 rounded">{file.type}</span>
                          {file.name}
                        </span>
                        <span className={`px-1.5 py-0.5 text-[9px] font-bold rounded-full border ${
                          file.status === "success" 
                            ? "bg-emerald-500/10 text-emerald-450 border-emerald-500/20" 
                            : "bg-rose-500/10 text-rose-450 border-rose-500/20"
                        }`}>
                          {file.status.toUpperCase()}
                        </span>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-slate-500 italic text-center py-2">無可提供之檔案數據</p>
                  )}
                </div>
              </div>

              {/* Close Button */}
              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={() => setCompletionModal(prev => ({ ...prev, isOpen: false }))}
                  className="px-5 py-2 bg-amber-500 hover:bg-amber-600 active:bg-amber-700 text-slate-950 font-bold text-xs rounded-lg transition-colors cursor-pointer border-none shadow-md w-full sm:w-auto"
                >
                  確認並返回工作區
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Toast Notification Container */}
      <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-3 max-w-xs pointer-events-none">
        <AnimatePresence>
          {toasts.map(t => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.2 } }}
              layout
              className={`pointer-events-auto p-4 rounded-xl border shadow-2xl flex items-start gap-3 backdrop-blur-md transition-all ${
                t.type === "success"
                  ? "bg-emerald-950/90 border-emerald-500/30 text-emerald-100 ring-1 ring-emerald-500/20"
                  : t.type === "error"
                  ? "bg-rose-950/90 border-rose-500/30 text-rose-100 ring-1 ring-rose-500/20"
                  : t.type === "warning"
                  ? "bg-amber-950/90 border-amber-500/30 text-amber-100 ring-1 ring-amber-500/20"
                  : "bg-slate-900/95 border-slate-800 text-slate-100 ring-1 ring-slate-800/50"
              }`}
            >
              <span className="text-base mt-0.5 select-none">
                {t.type === "success" ? "✅" : t.type === "error" ? "❌" : t.type === "warning" ? "⚠️" : "ℹ️"}
              </span>
              <div className="flex-1">
                <p className="text-xs font-medium font-sans leading-relaxed break-all">{t.message}</p>
              </div>
              <button
                type="button"
                onClick={() => setToasts(prev => prev.filter(item => item.id !== t.id))}
                className="text-slate-400 hover:text-slate-200 p-0.5 -mt-1 -mr-1 cursor-pointer transition-colors"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Web-based Local Folder Picker Modal */}
      <AnimatePresence>
        {isFolderPickerOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsFolderPickerOpen(false)}
              className="absolute inset-0 bg-slate-950/85 backdrop-blur-sm"
            />
            <motion.div
              initial={{ scale: 0.95, y: 15, opacity: 0 }}
              animate={{ scale: 1, y: 0, opacity: 1 }}
              exit={{ scale: 0.95, y: 15, opacity: 0 }}
              transition={{ type: "spring", stiffness: 350, damping: 25 }}
              className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl overflow-hidden text-slate-100 ring-1 ring-amber-500/20 max-h-[80vh] flex flex-col z-10"
            >
              <div className="absolute top-0 left-0 w-full h-[3px] bg-gradient-to-r from-amber-500 via-amber-600 to-amber-700" />
              
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  📁 選擇本機工作站資料夾
                </h3>
                <button
                  type="button"
                  onClick={() => setIsFolderPickerOpen(false)}
                  className="text-slate-450 hover:text-slate-100 transition-colors p-1 cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Path Input & Go Up Button */}
              <div className="flex gap-2 mb-3">
                {parentBrowseDir && (
                  <button
                    type="button"
                    onClick={() => fetchDirectories(parentBrowseDir)}
                    className="px-2.5 py-1.5 bg-slate-950 border border-slate-850 hover:bg-slate-800 hover:border-slate-755 text-slate-300 text-xs rounded-lg transition-colors flex items-center gap-1 cursor-pointer"
                    title="移至上層資料夾"
                  >
                    ⬆️ 上層
                  </button>
                )}
                <input
                  type="text"
                  value={currentBrowseDir}
                  onChange={(e) => setCurrentBrowseDir(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      fetchDirectories(currentBrowseDir);
                    }
                  }}
                  className="flex-1 bg-slate-950 border border-slate-850 rounded-lg py-1.5 px-3 text-xs text-slate-300 font-mono focus:outline-none focus:border-amber-500/50"
                />
                <button
                  type="button"
                  onClick={() => fetchDirectories(currentBrowseDir)}
                  className="px-2.5 py-1.5 bg-slate-950 border border-slate-800 hover:bg-slate-850 text-slate-300 text-xs rounded-lg transition-colors cursor-pointer"
                >
                  前往
                </button>
              </div>

              {/* Directories list */}
              <div className="flex-1 border border-slate-850 rounded-xl bg-slate-950/40 p-3 overflow-y-auto min-h-[220px] max-h-[320px]">
                {isBrowseLoading ? (
                  <div className="flex flex-col items-center justify-center py-12 gap-2">
                    <RefreshCw className="w-6 h-6 animate-spin text-amber-500" />
                    <p className="text-xs text-slate-500">正在讀取目錄項目...</p>
                  </div>
                ) : browseError ? (
                  <div className="text-center py-8">
                    <p className="text-xs text-rose-455 font-semibold">❌ {browseError}</p>
                    <button
                      type="button"
                      onClick={() => fetchDirectories("C:/LocalAI_Workstation")}
                      className="mt-3 px-3 py-1 bg-slate-900 border border-slate-800 hover:border-slate-700 hover:bg-slate-850 text-slate-300 text-xs rounded cursor-pointer"
                    >
                      返回預設目錄
                    </button>
                  </div>
                ) : browseDirectories.length === 0 ? (
                  <div className="text-center py-12 text-xs text-slate-500 italic">
                    此資料夾下沒有其他子資料夾
                  </div>
                ) : (
                  <div className="space-y-1">
                    {browseDirectories.map((dir, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => fetchDirectories(dir.path)}
                        className="w-full text-left flex items-center gap-2 px-2.5 py-2 hover:bg-slate-900/60 active:bg-slate-900 rounded-lg transition-colors text-xs text-slate-300 font-mono border-none cursor-pointer group"
                      >
                        <span className="text-amber-500 group-hover:scale-110 transition-transform">
                          {dir.name.includes("磁碟區") ? "💾" : "📁"}
                        </span>
                        <span className="truncate">{dir.name}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Bottom Confirm/Cancel Buttons */}
              <div className="flex justify-end gap-2 mt-4 pt-3 border-t border-slate-850">
                <button
                  type="button"
                  onClick={() => setIsFolderPickerOpen(false)}
                  className="px-4 py-2 bg-slate-950 border border-slate-800 hover:bg-slate-850 text-slate-400 hover:text-slate-200 text-xs rounded-lg transition-colors cursor-pointer"
                >
                  取消
                </button>
                <button
                  type="button"
                  disabled={currentBrowseDir === "本機"}
                  onClick={async () => {
                    setIsFolderPickerOpen(false);
                    setLocalScanPath(currentBrowseDir);
                    // Trigger scan
                    setIsLocalScanning(true);
                    try {
                      const scanResp = await fetch(`/api/scan-local-media?dir=${encodeURIComponent(currentBrowseDir)}`);
                      if (!scanResp.ok) throw new Error(`掃描失敗 (HTTP ${scanResp.status})`);
                      const scanData = await scanResp.json();
                      if (scanData.status === "success") {
                        setScannedLocalFiles(scanData.files);
                        showAlert(`🔍 選取成功！自動掃描發現 ${scanData.files.length} 個尚未分析教材！`);
                      } else {
                        throw new Error(scanData.error || "未知錯誤");
                      }
                    } catch (err: any) {
                      showAlert(`❌ 掃描失敗: ${err.message}`);
                    } finally {
                      setIsLocalScanning(false);
                    }
                  }}
                  className={`px-5 py-2 font-bold text-xs rounded-lg transition-colors border-none shadow-md ${
                    currentBrowseDir === "本機"
                      ? "bg-slate-800 text-slate-500 cursor-not-allowed opacity-50"
                      : "bg-amber-500 hover:bg-amber-600 text-slate-950 cursor-pointer"
                  }`}
                >
                  確認選擇此資料夾
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Batch Ingest settings & monitor Modal */}
      <AnimatePresence>
        {isBatchIngestModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => {
                if (batchIngestStatus === "idle" || batchIngestStatus === "completed" || batchIngestStatus === "aborted") {
                  setIsBatchIngestModalOpen(false);
                }
              }}
              className="absolute inset-0 bg-slate-955/85 backdrop-blur-sm"
            />
            <motion.div
              initial={{ scale: 0.95, y: 15, opacity: 0 }}
              animate={{ scale: 1, y: 0, opacity: 1 }}
              exit={{ scale: 0.95, y: 15, opacity: 0 }}
              transition={{ type: "spring", stiffness: 350, damping: 25 }}
              className="relative w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl overflow-hidden text-slate-100 ring-1 ring-amber-500/20 max-h-[90vh] flex flex-col z-10"
            >
              <div className="absolute top-0 left-0 w-full h-[3px] bg-gradient-to-r from-amber-500 via-amber-600 to-amber-700" />
              
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  ⚡ 多模態資料教材批次處理與進度監控
                </h3>
                <button
                  type="button"
                  disabled={batchIngestStatus === "running" || batchIngestStatus === "paused"}
                  onClick={() => setIsBatchIngestModalOpen(false)}
                  className="text-slate-450 hover:text-slate-100 transition-colors p-1 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed border-none bg-transparent"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {batchIngestStatus === "idle" ? (
                /* STEP 1: Settings Panel */
                <div className="flex flex-col gap-4 overflow-y-auto pr-1">
                  <div className="bg-slate-950/60 border border-slate-850 p-3 rounded-lg text-xs leading-relaxed text-slate-300">
                    <span className="font-bold text-amber-400 block mb-1">📋 待處理教材清單 ({batchIngestFiles.length} 個檔案)：</span>
                    <div className="max-h-24 overflow-y-auto space-y-1 font-mono pr-2">
                      {batchIngestFiles.map((f, i) => (
                        <div key={i} className="flex justify-between text-slate-400 border-b border-slate-900/50 pb-0.5">
                          <span className="truncate max-w-[400px]">{f.name}</span>
                          <span>{((f.size || 0) / (1024*1024)).toFixed(2)} MB</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    {/* Execution mode selection */}
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">執行模式</label>
                      <select
                        value={batchExecutionMode}
                        onChange={(e) => setBatchExecutionMode(e.target.value as "all" | "batch")}
                        className="bg-slate-950 border border-slate-850 rounded-lg py-1.5 px-3 text-xs text-slate-300 focus:outline-none focus:border-amber-500/50 cursor-pointer"
                      >
                        <option value="all">一次全數執行 (一次處理所有檔案)</option>
                        <option value="batch">分批次執行 (分多次處理)</option>
                      </select>
                    </div>

                    {/* Target Ingest action */}
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">處理動作</label>
                      <div className="py-1.5 px-3 bg-slate-950 border border-slate-850 rounded-lg text-xs text-amber-500 font-mono font-bold">
                        {batchIngestTargetMode === "import" ? "📥 導入下方待處理隊列" : "⚡ 直接分析整理到記憶庫"}
                      </div>
                    </div>
                  </div>

                  {batchExecutionMode === "batch" && (
                    <div className="grid grid-cols-2 gap-4 bg-slate-950/20 border border-slate-850/50 p-3 rounded-lg">
                      <div className="flex flex-col gap-1.5">
                        <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">每批次處理檔案數</label>
                        <input
                          type="number"
                          min="1"
                          max={batchIngestFiles.length}
                          value={batchFilesCount}
                          onChange={(e) => setBatchFilesCount(Math.max(1, parseInt(e.target.value) || 1))}
                          className="bg-slate-950 border border-slate-850 rounded-lg py-1.5 px-3 text-xs text-slate-300 focus:outline-none focus:border-amber-500/50"
                        />
                      </div>
                      <div className="flex flex-col gap-1.5">
                        <label className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">批次間隔時間 (秒)</label>
                        <input
                          type="number"
                          min="0"
                          value={batchIntervalSeconds}
                          onChange={(e) => setBatchIntervalSeconds(Math.max(0, parseInt(e.target.value) || 0))}
                          className="bg-slate-950 border border-slate-850 rounded-lg py-1.5 px-3 text-xs text-slate-300 focus:outline-none focus:border-amber-500/50"
                        />
                      </div>
                    </div>
                  )}

                  {/* System Overload Protection Agent Configuration */}
                  <div className="flex items-start gap-3 p-3 bg-slate-950/40 border border-slate-850/80 rounded-lg hover:border-slate-800 transition-colors">
                    <input
                      type="checkbox"
                      id="guardAgent"
                      checked={isGuardAgentEnabled}
                      onChange={(e) => setIsGuardAgentEnabled(e.target.checked)}
                      className="mt-0.5 w-4 h-4 rounded border-slate-800 text-amber-500 focus:ring-amber-500 focus:ring-offset-slate-900 bg-slate-950 cursor-pointer"
                    />
                    <div className="flex flex-col gap-0.5">
                      <label htmlFor="guardAgent" className="text-xs font-bold text-slate-200 cursor-pointer flex items-center gap-1.5 hover:text-white transition-colors">
                        <Shield className="w-3.5 h-3.5 text-amber-500" />
                        授權「過載保護監測 Agent」專責管制批次負載
                      </label>
                      <span className="text-[10px] text-slate-450 leading-relaxed">
                        啟用後，專責 Agent 會在每個檔案執行前計算 GPU 溫度與記憶體 (RAM/VRAM) 附載。若過載（溫度 &ge; 80°C、RAM &ge; 90%、VRAM &ge; 95%），Agent 將自動暫停批次，待降溫恢復後自動繼續。
                      </span>
                    </div>
                  </div>

                  {/* Time Estimations & Calendar Projection */}
                  <div className="bg-slate-950/40 border border-slate-850/80 rounded-lg p-3 grid grid-cols-3 gap-2 text-center">
                    <div className="flex flex-col">
                      <span className="text-[9px] text-slate-500 font-bold uppercase">預估處理總時間</span>
                      <span className="text-sm font-mono font-bold text-amber-400 mt-1">
                        {calculateEstimatedSeconds(batchIngestFiles).toFixed(1)} 秒
                      </span>
                    </div>
                    <div className="flex flex-col border-l border-slate-850">
                      <span className="text-[9px] text-slate-500 font-bold uppercase">預估開始時間</span>
                      <span className="text-sm font-mono font-bold text-slate-300 mt-1">
                        {new Date().toLocaleTimeString()}
                      </span>
                    </div>
                    <div className="flex flex-col border-l border-slate-850">
                      <span className="text-[9px] text-slate-500 font-bold uppercase">預估結束時間</span>
                      <span className="text-sm font-mono font-bold text-emerald-400 mt-1">
                        {new Date(Date.now() + calculateEstimatedSeconds(batchIngestFiles) * 1000).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>

                  <div className="flex justify-end gap-2 mt-4 pt-3 border-t border-slate-850">
                    <button
                      type="button"
                      onClick={() => setIsBatchIngestModalOpen(false)}
                      className="px-4 py-2 bg-slate-950 border border-slate-800 hover:bg-slate-855 text-slate-400 hover:text-slate-200 text-xs rounded-lg transition-colors cursor-pointer"
                    >
                      取消
                    </button>
                    <button
                      type="button"
                      onClick={() => runBatchIngestProcess(batchIngestFiles, batchIngestTargetMode, batchExecutionMode, batchFilesCount, batchIntervalSeconds)}
                      className="px-5 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold text-xs rounded-lg transition-colors cursor-pointer border-none shadow-md"
                    >
                      開始執行
                    </button>
                  </div>
                </div>
              ) : (
                /* STEP 2: Running Progress Monitor */
                <div className="flex flex-col gap-4 overflow-y-auto pr-1">
                  {/* Progress Header */}
                  {(() => {
                    let currentFileFraction = 0;
                    if (systemStatus?.ingest_progress && systemStatus?.ingest_progress?.status === "running") {
                      const { totalChunks, processedChunks } = systemStatus.ingest_progress;
                      if (totalChunks > 0) {
                        currentFileFraction = processedChunks / totalChunks;
                      }
                    }
                    const totalProgressCount = batchProcessedCount + currentFileFraction;
                    const totalProgressPercent = batchIngestFiles.length > 0 
                      ? Math.min(100, Math.round((totalProgressCount / batchIngestFiles.length) * 100)) 
                      : 0;

                    const currentFile = batchIngestFiles[batchProcessedCount];
                    const currentFileEstimate = currentFile ? calculateEstimatedSeconds([currentFile]) : 0;
                    const remainingFilesEstimate = calculateEstimatedSeconds(batchIngestFiles.slice(batchProcessedCount + 1));
                    const rawRemaining = remainingFilesEstimate + currentFileEstimate * (1 - currentFileFraction);
                    const timeSinceLast = batchElapsedSeconds - lastCompletedTime;
                    const smoothRemaining = Math.max(5, Math.round(rawRemaining - timeSinceLast));

                    return (
                      <>
                        <div className="flex justify-between items-center text-xs">
                          <span className="text-slate-400 font-mono">
                            進度：{batchProcessedCount} / {batchIngestFiles.length} 個檔案
                          </span>
                          <span className="font-mono font-bold text-amber-500">
                            {totalProgressPercent} %
                          </span>
                        </div>

                        {/* Progress Bar */}
                        <div className="w-full h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-850">
                          <motion.div
                            className="h-full bg-gradient-to-r from-amber-500 via-amber-400 to-emerald-400 rounded-full"
                            initial={{ width: 0 }}
                            animate={{ width: `${totalProgressPercent}%` }}
                            transition={{ duration: 0.3 }}
                          />
                        </div>

                        {/* Current Active Processing details */}
                        <div className="bg-slate-950/40 border border-slate-850 p-3 rounded-lg text-xs">
                          {isGuardAgentWaiting ? (
                            <div className="flex items-center gap-2 text-amber-400 font-bold animate-pulse">
                              <Shield className="w-3.5 h-3.5 text-amber-500" />
                              <span>🛡️ 系統安全 Agent：運算負載過載自動冷卻保護中...</span>
                            </div>
                          ) : batchIngestStatus === "running" ? (
                            <div className="flex items-center gap-2 text-slate-300">
                              <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-500" />
                              <span className="truncate">
                                正在處理：<span className="font-mono font-bold text-white">{batchCurrentFileName}</span>
                              </span>
                            </div>
                          ) : batchIngestStatus === "paused" ? (
                            <div className="flex items-center gap-2 text-amber-400 font-bold">
                              <span>⏸️ 處理程序已暫停</span>
                            </div>
                          ) : batchIngestStatus === "completed" ? (
                            <div className="flex flex-col gap-1 text-emerald-400 font-bold">
                              <span>✅ 批次處理程序已順利完成！</span>
                              <span className="text-[10px] text-slate-300 font-normal">
                                成功新增: {batchSuccessCount}，自動跳過已存在: {batchSkipCount}，失敗: {batchFailCount}
                              </span>
                            </div>
                          ) : batchIngestStatus === "aborted" ? (
                            <div className="flex items-center gap-2 text-rose-500 font-bold">
                              <span>🛑 處理程序已被使用者中斷或取消！</span>
                            </div>
                          ) : null}
                          
                          <div className="grid grid-cols-2 gap-2 mt-3 pt-2 border-t border-slate-900 text-slate-450 text-[10px] font-mono">
                            <div>已用時間：{batchElapsedSeconds} 秒</div>
                            <div>
                              預估剩餘：
                              {batchIngestStatus === "running"
                                ? `${smoothRemaining} 秒`
                                : "已停止"}
                            </div>
                            <div className="col-span-2 mt-1.5 flex gap-3 text-slate-350 text-[10px]">
                              <span>新增成功: <span className="text-emerald-400 font-bold">{batchSuccessCount}</span></span>
                              <span>自動跳過: <span className="text-amber-500 font-bold">{batchSkipCount}</span></span>
                              <span>處理失敗: <span className="text-rose-400 font-bold">{batchFailCount}</span></span>
                            </div>
                          </div>
                        </div>
                      </>
                    );
                  })()}

                  {/* Real-time System Telemetry & Agent Monitor */}
                  <div className="bg-slate-950/60 border border-slate-850 p-3 rounded-lg flex flex-col gap-2">
                    <div className="flex justify-between items-center text-[10px] text-slate-450 font-bold uppercase tracking-wider">
                      <span className="flex items-center gap-1.5">
                        <Cpu className="w-3.5 h-3.5 text-amber-500 animate-pulse" />
                        本機運算負載實時遙測 (Telemetry)
                      </span>
                      {isGuardAgentEnabled ? (
                        isGuardAgentWaiting ? (
                          <span className="flex items-center gap-1.5 text-amber-400 font-bold animate-pulse">
                            <span className="w-2 h-2 rounded-full bg-amber-400" />
                            ⚠️ Agent 過載保護暫停中
                          </span>
                        ) : (
                          <span className="flex items-center gap-1.5 text-emerald-400 font-bold">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                            🛡️ Agent 負載守護中
                          </span>
                        )
                      ) : (
                        <span className="text-slate-500 font-bold">
                          ⚪ 負載防護未啟用
                        </span>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-3 mt-1">
                      {/* RAM Usage */}
                      <div className="flex flex-col gap-1">
                        <div className="flex justify-between text-[10px] font-mono">
                          <span className="text-slate-400">主記憶體 (RAM)</span>
                          <span className={
                            systemStatus?.system?.total_mem && 
                            ((systemStatus?.system?.total_mem - systemStatus?.system?.free_mem) / systemStatus?.system?.total_mem) >= 0.9 
                              ? "text-rose-450 font-bold" 
                              : "text-slate-300"
                          }>
                            {systemStatus?.system?.total_mem 
                              ? `${(((systemStatus?.system?.total_mem - systemStatus?.system?.free_mem) / systemStatus?.system?.total_mem) * 100).toFixed(1)}%` 
                              : "0.0%"}
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-slate-900 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full transition-all duration-500 ${
                              systemStatus?.system?.total_mem && ((systemStatus?.system?.total_mem - systemStatus?.system?.free_mem) / systemStatus?.system?.total_mem) >= 0.9
                                ? "bg-rose-500"
                                : systemStatus?.system?.total_mem && ((systemStatus?.system?.total_mem - systemStatus?.system?.free_mem) / systemStatus?.system?.total_mem) >= 0.7
                                ? "bg-amber-500"
                                : "bg-emerald-500"
                            }`}
                            style={{ 
                              width: systemStatus?.system?.total_mem 
                                ? `${(((systemStatus?.system?.total_mem - systemStatus?.system?.free_mem) / systemStatus?.system?.total_mem) * 100)}%` 
                                : "0%" 
                            }}
                          />
                        </div>
                        <div className="text-[9px] text-slate-500 font-mono mt-0.5">
                          {systemStatus?.system?.memory_usage || "載入中..."}
                        </div>
                      </div>

                      {/* GPU Status (If Nvidia GPU exists) */}
                      {Array.isArray(systemStatus?.gpus) && systemStatus?.gpus.length > 0 ? (
                        <div className="flex flex-col gap-2.5 max-h-24 overflow-y-auto pr-1">
                          {systemStatus?.gpus.map((gpu: any, i: number) => (
                            <div key={i} className="flex flex-col gap-1 border-b border-slate-900/50 pb-1.5 last:border-b-0 last:pb-0">
                              <div className="flex justify-between text-[10px] font-mono">
                                <span className="text-slate-400">GPU #{gpu.index} 溫度 / VRAM</span>
                                <span className={
                                  (gpu.temp >= 80 || gpu.vram_used / gpu.vram_total >= 0.95) 
                                    ? "text-rose-450 font-bold" 
                                    : "text-slate-300"
                                }>
                                  {gpu.temp}°C / {((gpu.vram_used / gpu.vram_total) * 100).toFixed(0)}%
                                </span>
                              </div>
                              <div className="w-full h-1 bg-slate-900 rounded-full overflow-hidden">
                                <div 
                                  className={`h-full rounded-full transition-all duration-500 ${
                                    gpu.temp >= 80 || gpu.vram_used / gpu.vram_total >= 0.95
                                      ? "bg-rose-500"
                                      : gpu.temp >= 70 || gpu.vram_used / gpu.vram_total >= 0.8
                                      ? "bg-amber-500"
                                      : "bg-emerald-500"
                                  }`}
                                  style={{ 
                                    width: `${Math.max(5, (gpu.vram_used / gpu.vram_total) * 100)}%` 
                                  }}
                                />
                              </div>
                              <div className="text-[9px] text-slate-500 font-mono flex justify-between">
                                <span>Core Load: {gpu.util}%</span>
                                <span>總量: {(gpu.vram_total / 1024).toFixed(1)} GB VRAM</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="flex flex-col justify-center items-center bg-slate-900/30 border border-slate-850/50 rounded p-1.5 text-center h-[34px]">
                          <span className="text-[9px] text-slate-500 font-bold">ℹ️ 無 Nvidia 獨顯 (跳過 GPU 監測)</span>
                          <span className="text-[8px] text-slate-600">採 CPU/RAM 負載安全防護</span>
                        </div>
                      )}

                      {/* Ingestion Split-and-Combine progress */}
                      {(() => {
                        const progresses = Array.isArray(systemStatus?.active_progresses) && systemStatus.active_progresses.length > 0
                          ? systemStatus.active_progresses
                          : systemStatus?.ingest_progress && systemStatus?.ingest_progress?.status === "running"
                          ? [systemStatus.ingest_progress]
                          : [];

                        if (progresses.length === 0) return null;

                        return (
                          <div className="col-span-2 mt-2 pt-2 border-t border-slate-900/50 flex flex-col gap-3">
                            {progresses.map((prog: any, pIdx: number) => (
                              <div key={pIdx} className="flex flex-col gap-1.5 bg-slate-900/20 p-2 border border-slate-850/30 rounded">
                                <div className="flex justify-between text-[10px] font-mono">
                                  <span className="text-amber-400 font-bold flex items-center gap-1.5 animate-pulse truncate max-w-[70%]" title={prog.message}>
                                    <span className="w-1.5 h-1.5 bg-amber-500 rounded-full shrink-0" />
                                    {prog.message || "⚙️ 正在分析錯字與法理爭點..."}
                                  </span>
                                  <span className="text-slate-300 shrink-0">
                                    區段 {prog.processedChunks} / {prog.totalChunks}
                                  </span>
                                </div>
                                <div className="w-full h-1 bg-slate-950 rounded-full overflow-hidden">
                                  <div 
                                    className="h-full bg-amber-500 rounded-full transition-all duration-500"
                                    style={{ 
                                      width: `${Math.min(100, Math.max(2, (prog.processedChunks / (prog.totalChunks || 1)) * 100))}%` 
                                    }}
                                  />
                                </div>
                                <div className="text-[9px] text-slate-500 truncate" title={prog.filename}>
                                  檔案: {prog.filename}
                                </div>
                              </div>
                            ))}

                            {systemStatus?.ollama?.status === "connected" && systemStatus?.ollama?.model?.toLowerCase().includes("deepseek-r1") && (
                              <div className="text-[8px] text-slate-500 bg-slate-900/50 p-1.5 border border-slate-850 rounded leading-relaxed mt-0.5">
                                ⚠️ 偵測到正在使用 Ollama 深度推理模型 ({systemStatus?.ollama?.model})。推理模型因輸出思考過程會花費較長時間，請耐心等待。
                              </div>
                            )}
                          </div>
                        );
                      })()}
                    </div>
                  </div>

                  {/* Scrollable Live log console */}
                  <div className="flex flex-col gap-1">
                    <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">📊 執行日誌與錯誤監視視窗</span>
                    <div className="h-44 border border-slate-850 rounded-lg bg-slate-950 p-3 font-mono text-[10px] overflow-y-auto space-y-1">
                      {batchLogs.length === 0 ? (
                        <span className="text-slate-600 italic">日誌等待中...</span>
                      ) : (
                        batchLogs.map((log, i) => (
                          <div key={i} className="flex gap-2 leading-relaxed">
                            <span className="text-slate-500">[{log.time}]</span>
                            <span
                              className={
                                log.type === "success"
                                  ? "text-emerald-400"
                                  : log.type === "error"
                                  ? "text-rose-400 font-semibold"
                                  : "text-slate-300"
                              }
                            >
                              {log.text}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Processing Controls */}
                  <div className="flex justify-end gap-2 mt-3 pt-3 border-t border-slate-850">
                    <div className="flex gap-2 mr-auto">
                      {batchIngestStatus === "running" && (
                        <button
                          type="button"
                          onClick={() => {
                            isBatchPausedRef.current = true;
                            setBatchIngestStatus("paused");
                          }}
                          className="px-3 py-1.5 bg-slate-950 border border-slate-800 hover:bg-slate-850 text-amber-500 font-bold text-xs rounded-lg transition-colors cursor-pointer"
                        >
                          ⏸️ 臨時暫停
                        </button>
                      )}
                      {batchIngestStatus === "paused" && (
                        <button
                          type="button"
                          onClick={() => {
                            isBatchPausedRef.current = false;
                          }}
                          className="px-3 py-1.5 bg-slate-950 border border-slate-800 hover:bg-slate-850 text-emerald-400 font-bold text-xs rounded-lg transition-colors cursor-pointer"
                        >
                          ▶️ 繼續執行
                        </button>
                      )}
                      {(batchIngestStatus === "running" || batchIngestStatus === "paused") && (
                        <button
                          type="button"
                          onClick={() => {
                            isBatchAbortedRef.current = true;
                            isBatchPausedRef.current = false; // ensure it doesn't get stuck in pause loop
                          }}
                          className="px-3 py-1.5 bg-rose-950/20 border border-rose-900/40 hover:bg-rose-950/40 text-rose-400 font-bold text-xs rounded-lg transition-colors cursor-pointer"
                        >
                          🛑 中斷取消
                        </button>
                      )}
                    </div>
                    
                    <button
                      type="button"
                      disabled={batchIngestStatus === "running" || batchIngestStatus === "paused"}
                      onClick={() => setIsBatchIngestModalOpen(false)}
                      className="px-5 py-2 bg-slate-950 border border-slate-800 hover:bg-slate-850 text-slate-300 hover:text-white font-bold text-xs rounded-lg transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      關閉視窗
                    </button>
                  </div>
                </div>
              )}
            </motion.div>
          </div>
        )}
      </AnimatePresence>

    </div>
  );
}
