<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { t, m } from '../i18n'
import { fetchReviews, deleteReview, batchDelete } from '../api'

const router = useRouter()
const reviews = ref([])
const allSelected = ref(false)

async function load() {
  try { reviews.value = await fetchReviews() } catch { reviews.value = [] }
}

function toggleAll() {
  reviews.value.forEach(r => { r._checked = allSelected.value })
}

function selectedIds() {
  return reviews.value.filter(r => r._checked).map(r => r.id)
}

async function remove(id) {
  await deleteReview(id)
  load()
}

async function removeSelected() {
  const ids = selectedIds()
  if (!ids.length) { alert(t('noneSelected')); return }
  await batchDelete(ids, false)
  load()
}

async function removeAll() {
  if (!confirm(t('confirmDeleteAll'))) return
  await batchDelete([], true)
  load()
}

function edit(r) {
  router.push({ path: '/', query: { edit: r.id } })
}

function exportCsv() {
  window.location.href = '/api/reviews/export'
}

onMounted(load)
</script>

<template>
  <div>
    <h2 style="margin: .5em 0 .2em">{{ t('historyTitle') }}</h2>
    <p class="hint" style="margin: 0 0 1em">{{ t('historySub') }}</p>

    <div class="toolbar">
      <label class="btn" style="margin:0">
        <input type="checkbox" v-model="allSelected" @change="toggleAll" style="margin-right:6px" />
        {{ t('selectAll') }}
      </label>
      <button class="btn" @click="exportCsv">{{ t('exportCsv') }}</button>
      <button class="btn danger" @click="removeSelected">{{ t('deleteSelected') }}</button>
      <button class="btn danger" @click="removeAll">{{ t('deleteAll') }}</button>
    </div>

    <p class="empty-hint" v-if="!reviews.length">{{ t('emptyHistory') }}</p>

    <div class="history-item" v-for="r in reviews" :key="r.id">
      <input type="checkbox" v-model="r._checked" />
      <div class="history-body">
        <div class="history-text">{{ r.text }}</div>
        <div class="history-tags">
          <span v-for="a in ['food','service','price','ambience']" :key="a" class="badge" :class="r[a + '_label'] || 'neutral'">
            {{ m().aspects[a] }} {{ m().labels[r[a + '_label']] }}
          </span>
        </div>
        <div class="history-meta">
          {{ r.model }} · {{ ['food','service','price','ambience'].map(a => m().aspects[a] + ' ' + ((r[a + '_confidence'] || 0) * 100).toFixed(0) + '%').join(' / ') }}
        </div>
        <div class="history-actions">
          <a href="#" @click.prevent="edit(r)">{{ t('edit') }}</a>
          <button class="danger" @click="remove(r.id)">{{ t('delete') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>
