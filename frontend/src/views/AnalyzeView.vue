<script setup>
import { ref, onMounted } from 'vue'
import { t, m, lang } from '../i18n'
import {
  predict as apiPredict,
  fetchModels,
  fetchDemo,
  createReview,
  updateReview,
  fetchReview,
  predictCsv,
} from '../api'

const text = ref('')
const textRef = ref(null)
const model = ref('tfidf')
const models = ref([])
const loading = ref(false)
const status = ref('')
const statusError = ref(false)
const rating = ref(null)
const aspects = ref([])
const explanation = ref({})
const editingId = ref(null)

const batchFile = ref(null)
const batchProgress = ref(null)
const batchStatus = ref('')
const batchStatusError = ref(false)

function setStatus(msg, isError = false) {
  status.value = msg
  statusError.value = isError
}

function clearText() {
  text.value = ''
  aspects.value = []
  rating.value = null
  explanation.value = {}
  status.value = ''
  statusError.value = false
  if (textRef.value) textRef.value.focus()
}

function onKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    e.preventDefault()
    predict()
  }
}

function starString(star) {
  return '★'.repeat(star) + '☆'.repeat(5 - star)
}

function distributionBars(a) {
  if (!a.distribution || !Object.keys(a.distribution).length) return []
  const order = ['negative', 'neutral', 'positive']
  return order.filter(k => k in a.distribution).map(k => ({
    key: k,
    value: a.distribution[k],
  }))
}

function explainFor(aspect) {
  const e = explanation.value[aspect]
  if (!e) return null
  const pos = (e.positive || []).map(x => x[0]).join(' ')
  const neg = (e.negative || []).map(x => x[0]).join(' ')
  return { pos, neg }
}

async function predict() {
  if (!text.value.trim()) { setStatus(t('empty'), true); return }
  loading.value = true
  setStatus(model.value === 'tfidf' ? t('analyzing') : t('loading'))
  try {
    const data = await apiPredict(text.value, model.value)
    rating.value = data.rating
    aspects.value = data.aspects || []
    const exp = {}
    ;(data.explanation || []).forEach(e => { exp[e.aspect] = e })
    explanation.value = exp
    setStatus('')
  } catch (e) {
    setStatus(e.message, true)
    aspects.value = []
    rating.value = null
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!text.value.trim()) { setStatus(t('empty'), true); return }
  try {
    if (editingId.value) await updateReview(editingId.value, text.value, model.value)
    else await createReview(text.value, model.value)
    editingId.value = null
    setStatus(t('saved'))
  } catch (e) {
    setStatus(e.message, true)
  }
}

async function demo() {
  try {
    const d = await fetchDemo()
    text.value = d.text
    model.value = d.model || model.value
    await predict()
  } catch (e) {
    setStatus(e.message, true)
  }
}

async function batch() {
  if (!batchFile.value) { setStatus(t('noFile'), true); return }
  batchStatus.value = ''
  batchStatusError.value = false
  batchProgress.value = { done: 0, total: 0 }
  try {
    await predictCsv(
      batchFile.value,
      model.value,
      (p) => { batchProgress.value = p },
      (r) => {
        batchStatus.value = t('batchDone')
        batchStatusError.value = false
        // trigger download of the result CSV
        const blob = new Blob(['\ufeff' + r.csv], { type: 'text/csv;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = r.filename
        a.click()
        URL.revokeObjectURL(url)
      },
    )
  } catch (e) {
    batchStatus.value = e.message
    batchStatusError.value = true
  } finally {
    batchProgress.value = null
  }
}

function onFileChange(e) {
  batchFile.value = e.target.files[0] || null
}

async function loadEdit() {
  // support deep-link ?edit=ID from the history page
  const params = new URLSearchParams(window.location.hash.split('?')[1] || '')
  const id = params.get('edit')
  if (id) {
    try {
      const rv = await fetchReview(id)
      text.value = rv.text
      model.value = rv.model
      editingId.value = id
      await predict()
    } catch { /* ignore */ }
  }
}

onMounted(async () => {
  try { models.value = await fetchModels() } catch { /* ignore */ }
  loadEdit()
})
</script>

<template>
  <div>
    <div class="guide">
      <h2 class="guide-title">{{ t('guideTitle') }}</h2>
      <p class="guide-text">{{ t('guide') }}</p>
    </div>

    <section class="panel">
      <h2 class="panel-title">{{ t('navAnalyze') }}</h2>

      <div class="field">
        <label for="text">{{ t('reviewLabel') }}</label>
        <div class="input-wrap">
          <textarea id="text" ref="textRef" v-model="text" :placeholder="t('reviewPlaceholder')" @keydown="onKeydown"></textarea>
          <button v-if="text" class="clear-btn" :title="t('clear')" @click="clearText">×</button>
        </div>
        <div class="input-footer">
          <span class="counter">{{ text.length }} {{ t('chars') }}</span>
        </div>
      </div>

      <div class="field">
        <label for="model">{{ t('modelLabel') }}</label>
        <select id="model" v-model="model">
          <option v-for="mm in models" :key="mm.key" :value="mm.key">{{ mm.name }}</option>
        </select>
        <p class="hint">{{ t('modelHint') }}</p>
      </div>

      <div class="actions">
        <button class="btn primary" :disabled="loading" @click="predict">
          <span v-if="loading" class="spinner"></span>{{ loading ? t('analyzing') : t('predict') }}
        </button>
        <button class="btn" :disabled="loading" @click="save">{{ t('save') }}</button>
        <button class="btn" :disabled="loading" @click="demo">{{ t('demo') }}</button>
      </div>
      <div class="status" :class="{ error: statusError }">{{ status }}</div>
    </section>

    <section class="panel">
      <h2 class="panel-title">{{ t('batchLabel') }}</h2>
      <input type="file" accept=".csv" @change="onFileChange" />
      <p class="hint">{{ t('batchHint') }}</p>
      <div class="actions">
        <a class="btn" href="/api/template">{{ t('template') }}</a>
        <button class="btn" @click="batch">{{ t('batch') }}</button>
      </div>
      <div class="progress" :class="{ show: batchProgress }">
        <div class="progress-fill" :style="{ width: batchProgress ? (batchProgress.done / batchProgress.total * 100) + '%' : '0' }"></div>
      </div>
      <div class="progress-text" v-if="batchProgress">{{ batchProgress.done }} / {{ batchProgress.total }}</div>
      <div class="status" :class="{ error: batchStatusError }">{{ batchStatus }}</div>
    </section>

    <div class="rating" v-if="rating && rating.star">
      <span class="rating-stars">{{ starString(rating.star) }}</span>
      <span class="rating-text">{{ t('ratingLabel') }}: {{ rating.star }} / 5</span>
      <span class="rating-hint">{{ t('ratingHint') }}</span>
    </div>

    <div class="results">
      <article v-for="a in aspects" :key="a.aspect" class="aspect-card">
        <h3>
          {{ m().aspects[a.aspect] }}
          <span class="badge" :class="a.label || 'neutral'">{{ m().labels[a.label] }}</span>
        </h3>
        <div class="conf" v-if="a.confidence !== null">
          {{ t('confidence') }} {{ (a.confidence * 100).toFixed(1) }}%
        </div>
        <div class="dist">
          <template v-for="b in distributionBars(a)" :key="b.key">
            <div class="bar"><span :style="{ width: (b.value * 100) + '%' }"></span></div>
            <div class="dist-label">{{ m().labels[b.key] }} {{ (b.value * 100).toFixed(1) }}%</div>
          </template>
        </div>
        <div class="explain" v-if="explainFor(a.aspect)">
          <span class="explain-hint">{{ t('explainHint') }}</span>
          <span v-if="explainFor(a.aspect).pos" class="explain-pos">+ {{ explainFor(a.aspect).pos }}</span>
          <span v-if="explainFor(a.aspect).neg" class="explain-neg">- {{ explainFor(a.aspect).neg }}</span>
        </div>
      </article>
    </div>
  </div>
</template>
