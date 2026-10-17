import { ref } from 'vue'

const messages = {
  zh: {
    title: '方面级情感分析',
    subtitle: '输入一条餐厅评论，分析其在口味、服务、价格、环境四个方面的情感。',
    guideTitle: '使用说明',
    guide: '① 粘贴评论 → ② 选模型并点击「分析」→ ③ 查看四个方面的情感、整体星级评分与关键词解释。',
    navAnalyze: '分析',
    navHistory: '历史记录',
    reviewLabel: '评论',
    modelLabel: '模型',
    modelHint: 'TF-IDF + 逻辑回归：快（默认）。BERT / RoBERTa：更准但较慢，首次加载需下载模型。',
    reviewPlaceholder: '食物很棒，但服务太慢了。',
    predict: '分析',
    analyzing: '分析中…',
    save: '保存结果',
    demo: '随机演示样本',
    batchLabel: '批量导入（CSV）',
    template: '下载模板',
    batch: '批量分析',
    batchHint: 'CSV 需包含 review 列；结果会同时保存到历史记录。',
    historyTitle: '历史记录',
    historySub: '管理已保存的分析：查看、编辑、删除、导出。',
    selectAll: '全选',
    exportCsv: '导出 CSV',
    deleteSelected: '删除选中',
    deleteAll: '删除全部',
    confidence: '置信度',
    ratingLabel: '整体评分',
    ratingHint: '整体星级评分（1-5），由微调的语言模型预测。',
    explainHint: '关键词：+ 表示推向正面，- 表示推向负面（SHAP）。',
    empty: '请输入评论。',
    noDemo: '暂无演示样本。',
    loading: '正在加载模型（首次运行可能需要几秒）…',
    noFile: '请先选择 CSV 文件。',
    batchDone: '处理完成，已保存并下载 results.csv',
    edit: '编辑',
    delete: '删除',
    saved: '已保存。',
    emptyHistory: '暂无保存的记录。',
    confirmDeleteAll: '确定删除全部记录？',
    noneSelected: '请至少选择一条记录。',
    footnote: '模型：TF-IDF + 逻辑回归（默认）、BERT、RoBERTa。「中性」表示置信度低于阈值。',
    langToggle: 'English',
    clear: '清空',
    chars: '字',
    aspects: { food: '口味', service: '服务', price: '价格', ambience: '环境' },
    labels: { negative: '负面', neutral: '中性', positive: '正面' },
  },
  en: {
    title: 'Aspect-Based Sentiment Analysis',
    subtitle: 'Enter a restaurant review to analyze its sentiment across four aspects.',
    guideTitle: 'How it works',
    guide: '1. Paste a review · 2. Pick a model and click Analyze · 3. Read the four aspects, the overall star rating, and the keyword explanations.',
    navAnalyze: 'Analyze',
    navHistory: 'History',
    reviewLabel: 'Review',
    modelLabel: 'Model',
    modelHint: 'TF-IDF + LR is fast (default). BERT / RoBERTa are more accurate but slower; the first load downloads the model.',
    reviewPlaceholder: 'The food was fantastic but the service was slow.',
    predict: 'Analyze',
    analyzing: 'Analyzing...',
    save: 'Save result',
    demo: 'Random demo sample',
    batchLabel: 'Batch import (CSV)',
    template: 'Download template',
    batch: 'Batch analyze',
    batchHint: "CSV needs a 'review' column. Results are saved to history.",
    historyTitle: 'Saved records',
    historySub: 'Manage saved analyses: view, edit, delete, export.',
    selectAll: 'Select all',
    exportCsv: 'Export CSV',
    deleteSelected: 'Delete selected',
    deleteAll: 'Delete all',
    confidence: 'confidence',
    ratingLabel: 'Overall rating',
    ratingHint: 'Overall star rating (1-5), predicted by a fine-tuned language model.',
    explainHint: 'Key words: + push toward positive, - toward negative (SHAP).',
    empty: 'Please enter a review.',
    noDemo: 'No demo samples available.',
    loading: 'Loading model (first run may take a few seconds)...',
    noFile: 'Please choose a CSV file first.',
    batchDone: 'Done, saved and downloaded results.csv',
    edit: 'Edit',
    delete: 'Delete',
    saved: 'Saved.',
    emptyHistory: 'No saved records yet.',
    confirmDeleteAll: 'Delete all records?',
    noneSelected: 'Select at least one record.',
    footnote: "Models: TF-IDF + LR (default), BERT, RoBERTa. 'Neutral' means confidence below threshold.",
    langToggle: '中文',
    clear: 'Clear',
    chars: 'chars',
    aspects: { food: 'Taste', service: 'Service', price: 'Price', ambience: 'Ambience' },
    labels: { negative: 'Negative', neutral: 'Neutral', positive: 'Positive' },
  },
}

const stored = typeof localStorage !== 'undefined' ? localStorage.getItem('lang') : null
export const lang = ref(stored === 'en' ? 'en' : 'zh')

export function t(key) {
  return messages[lang.value][key] ?? key
}

export function m() {
  return messages[lang.value]
}

export function toggleLang() {
  lang.value = lang.value === 'zh' ? 'en' : 'zh'
  if (typeof localStorage !== 'undefined') localStorage.setItem('lang', lang.value)
}
