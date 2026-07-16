// Client-side rule engine for Taiwanese Legal Terminology and Spelling Proofreading (LanguageTool-inspired)

export interface ProofMatch {
  id: string;
  suspect: string;
  correct: string;
  reason: string;
  index: number;
}

export interface LegalRule {
  pattern: RegExp | string;
  correct: string;
  reason: string;
}

// Comprehensive rules for Taiwanese ASR legal mistranscriptions
export const LEGAL_PROOF_RULES: LegalRule[] = [
  { pattern: /假芳/g, correct: "甲方", reason: "語音轉記錯別字，應為契約或訴訟當事人「甲方」" },
  { pattern: /倚芳/g, correct: "乙方", reason: "語音轉記錯別字，應為契約或訴訟當事人「乙方」" },
  { pattern: /丙芳/g, correct: "丙方", reason: "語音轉記錯別字，應為契約或訴訟當事人「丙方」" },
  { pattern: /丁芳/g, correct: "丁方", reason: "語音轉記錯別字，應為當事人「丁方」" },
  { pattern: /侵權形為/g, correct: "侵權行為", reason: "法律專有名詞錯誤，應為民法第184條之「侵權行為」" },
  { pattern: /侵權行民/g, correct: "侵權行為", reason: "法律專有名詞拼寫錯誤，應為「侵權行為」" },
  { pattern: /損害合償/g, correct: "損害賠償", reason: "常見語音辨識錯誤，應為「損害賠償」" },
  { pattern: /損害補償/g, correct: "損害賠償", reason: "請確認本案係依民事侵權請求「損害賠償」，亦或行政合法損失之「損害補償」" },
  { pattern: /告訴乃輪/g, correct: "告訴乃論", reason: "刑事程序專有名詞辨識錯誤，應為「告訴乃論」之罪" },
  { pattern: /型事訴訟/g, correct: "刑事訴訟", reason: "法律專業名詞錯別字，應為「刑事訴訟」" },
  { pattern: /型訴/g, correct: "刑訴", reason: "刑事訴訟法簡配字詞辨識錯誤，應為「刑訴」" },
  { pattern: /行事訴訟/g, correct: "刑事訴訟", reason: "同音字辨識錯誤，應為「刑事訴訟」" },
  { pattern: /包庇罪犯/g, correct: "庇護罪犯", reason: "刑法專有名詞建議，法條精確用語為「藏匿或使之隱避」" },
  { pattern: /不當得裏/g, correct: "不當得利", reason: "民法第179條專有字，應為「不當得利」" },
  { pattern: /不當德利/g, correct: "不當得利", reason: "同音字辨識錯誤，應為「不當得利」" },
  { pattern: /因果觀係/g, correct: "因果關係", reason: "法律與邏輯要件錯別字，應為「因果關係」" },
  { pattern: /因果關西/g, correct: "因果關係", reason: "同音錯字，應為「因果關係」" },
  { pattern: /油漆徒刑/g, correct: "有期徒刑", reason: "極常見語音搞笑錯字，應為刑罰之種類「有期徒刑」" },
  { pattern: /無期徒行/g, correct: "無期徒刑", reason: "應為刑罰之主刑種類「無期徒刑」" },
  { pattern: /由期徒刑/g, correct: "有期徒刑", reason: "語音同音錯別字，應為「有期徒刑」" },
  { pattern: /和解和議/g, correct: "和解協議", reason: "應為當事人之「和解協議」或「和解契約」" },
  { pattern: /最高法源/g, correct: "最高法院", reason: "台灣最高司法機關名稱辨識錯誤，應為「最高法院」" },
  { pattern: /高等法源/g, correct: "高等法院", reason: "應為「高等法院」" },
  { pattern: /地方法源/g, correct: "地方法院", reason: "應為「地方法院」" },
  { pattern: /訴訟袋裡人/g, correct: "訴訟代理人", reason: "重大代理用語辨識錯誤，應為「訴訟代理人」" },
  { pattern: /訴代理人/g, correct: "訴訟代理人", reason: "拼寫或辨識缺漏，建議修正為「訴訟代理人」" },
  { pattern: /無權戰有/g, correct: "無權占有", reason: "物權法核心專有名詞辨識錯誤，應為「無權占有」" },
  { pattern: /無權佔有/g, correct: "無權占有", reason: "法律精確用語為「無權占有」（占字無人字旁）" },
  { pattern: /失效消滅/g, correct: "時效消滅", reason: "請求權消滅時效之專有名詞辨識錯誤，應為「時效消滅」" },
  { pattern: /時效銷滅/g, correct: "時效消滅", reason: "消滅時效錯別字，應為「時效消滅」" },
  { pattern: /非送事件/g, correct: "非訟事件", reason: "非訟事件法名詞同音錯字，應為「非訟事件」" },
  { pattern: /政當防衛/g, correct: "正當防衛", reason: "阻卻違法事由專有名詞辨識錯誤，應為「正當防衛」" },
  { pattern: /正當防委/g, correct: "正當防衛", reason: "語音辨識錯誤，應為「正當防衛」" },
  { pattern: /緊及避難/g, correct: "緊急避難", reason: "阻卻違法事由同音混淆，應為「緊急避難」" },
  { pattern: /最行法定/g, correct: "罪刑法定", reason: "刑法基本原則之錯別字，應為「罪刑法定」原則" },
  { pattern: /罪行法定/g, correct: "罪刑法定", reason: "法律精確術語應指處罰必須有成文「刑」法明文，故為「罪刑法定」" },
  { pattern: /自由心正/g, correct: "自由心證", reason: "訴訟法證據評價原則，正確用語為「自由心證」" },
  { pattern: /甲扣押/g, correct: "假扣押", reason: "保全程序之專有名詞辨識錯誤，法律之「假」意指暫時，應為「假扣押」" },
  { pattern: /假扣鴨/g, correct: "假扣押", reason: "語音諧音搞笑錯誤，正確為保全程序「假扣押」" },
  { pattern: /甲處分/g, correct: "假處分", reason: "定暫時狀態保全程序，應為「假處分」" },
  { pattern: /假處份/g, correct: "假處分", reason: "法律正確用字為「分」，應為「假處分」" },
  { pattern: /偵查停/g, correct: "偵查庭", reason: "檢察官開庭場所字詞辨識錯誤，應為「偵查庭」" },
  { pattern: /不起訴處份/g, correct: "不起訴處分", reason: "處分之分字不可加人字旁，應為「不起訴處分」" },
  { pattern: /起訴處份/g, correct: "起訴處分", reason: "正確用字為「起訴處分」" },
  { pattern: /緩起訴處份/g, correct: "緩起訴處分", reason: "正確用字為「緩起訴處分」" },
  { pattern: /明事訴訟/g, correct: "民事訴訟", reason: "同音字辨識錯誤，應為「民事訴訟」" },
  { pattern: /聲請書狀/g, correct: "聲請書狀", reason: "若向法院請求裁定，應用「聲請」；如果是起訴，則為「起訴」" },
  { pattern: /聯帶賠償/g, correct: "連帶賠償", reason: "共同侵權連帶責任，應為「連帶賠償」" },
  { pattern: /連袋賠償/g, correct: "連帶賠償", reason: "諧音辨識錯誤，應為「連帶賠償」" }
];

/**
 * Scan text to find all mismatched legal terminology based on spell checking rules.
 * Keeps track of matching word indexes accurately.
 */
export function proofreadText(text: string): ProofMatch[] {
  if (!text) return [];
  const matches: ProofMatch[] = [];
  
  // Use sequential find to record unique IDs and locations
  LEGAL_PROOF_RULES.forEach((rule, ruleIdx) => {
    const rx = typeof rule.pattern === "string" ? new RegExp(rule.pattern, "g") : rule.pattern;
    rx.lastIndex = 0; // reset
    let m;
    while ((m = rx.exec(text)) !== null) {
      matches.push({
        id: `rule-${ruleIdx}-${m.index}`,
        suspect: m[0],
        correct: rule.correct,
        reason: rule.reason,
        index: m.index
      });
      // Safety break to prevent infinite loops in regex
      if (rx.lastIndex === m.index) {
        rx.lastIndex++;
      }
    }
  });

  // Sort by index so the order matches reading flow
  return matches.sort((a, b) => a.index - b.index);
}

/**
 * Perform automatic corrections of all known misrecognized terms.
 */
export function autoCorrectText(text: string): string {
  if (!text) return "";
  let result = text;
  
  // Sort rules in length-descending order to avoid replacing parts of larger replacements first
  const sortedRules = [...LEGAL_PROOF_RULES].sort((a, b) => {
    const aLen = typeof a.pattern === "string" ? a.pattern.length : a.pattern.source.length;
    const bLen = typeof b.pattern === "string" ? b.pattern.length : b.pattern.source.length;
    return bLen - aLen;
  });

  sortedRules.forEach((rule) => {
    if (typeof rule.pattern === "string") {
      result = result.replace(new RegExp(rule.pattern, "g"), rule.correct);
    } else {
      result = result.replace(rule.pattern, rule.correct);
    }
  });

  return result;
}
